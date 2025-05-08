# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import datetime
from io import StringIO

import logging_config
import pandas as pd
import requests
from dash import Input, Output, State, ctx, exceptions, html, no_update
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from utils.display import build_vision_polygon
from utils.live_stream import fetch_cameras, find_closest_camera_pose, send_api_request

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


start_time = None


@app.callback(
    Output("dummy-output", "children"),
    Input("start-stream", "n_clicks"),
    Input("stop-stream", "n_clicks"),
    Input("move-up", "n_clicks"),
    Input("move-down", "n_clicks"),
    Input("move-left", "n_clicks"),
    Input("move-right", "n_clicks"),
    Input("stop-move", "n_clicks"),
    Input("zoom-input", "value"),
    State("camera-select", "value"),
    State("speed-input", "value"),
    State("selected-camera-pose", "data"),
    prevent_initial_call=True,
)
def control_camera(
    start_stream,
    stop_stream,
    up,
    down,
    left,
    right,
    stop,
    zoom_level,
    camera_id,
    move_speed,
    selected_camera,
):
    """
    Callback to control camera actions (stream, movement, zoom) based on UI input.

    Parameters
    ----------
    start_stream : int
        Click count for start-stream button.
    stop_stream : int
        Click count for stop-stream button.
    up, down, left, right, stop : int
        Click counts for movement control buttons.
    zoom_level : float
        Current zoom level (0-100%).
    camera_id : str
        Currently selected camera ID.
    move_speed : int
        Speed slider value.
    selected_camera : dict
        Selected camera metadata (contains 'camera', 'ip', 'pi_ip', etc.)

    Returns
    -------
    no_update
        Placeholder to satisfy Dash Output without altering the layout.
    """
    logger.debug(
        "[control_camera] Triggered with args: %s",
        {
            "start": start_stream,
            "stop": stop_stream,
            "zoom": zoom_level,
            "camera_id": camera_id,
            "selected_camera": selected_camera,
        },
    )

    if not ctx.triggered or not selected_camera:
        raise PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if selected_camera.get("camera") != camera_id:
        raise PreventUpdate

    pi_ip = selected_camera.get("pi_ip")
    camera_ip = selected_camera.get("ip")
    if not pi_ip or not camera_ip:
        raise PreventUpdate

    direction_map = {
        "move-up": "Up",
        "move-down": "Down",
        "move-left": "Left",
        "move-right": "Right",
        "stop-move": "Stop",
    }

    try:
        if button_id == "start-stream":
            send_api_request(f"http://{pi_ip}:8081", f"/start_stream/{camera_ip}")

        elif button_id == "stop-stream":
            send_api_request(f"http://{pi_ip}:8081", f"/stop_stream/{camera_ip}")

        elif button_id in direction_map:
            direction = direction_map[button_id]
            if direction != "Stop":
                true_speed = int(move_speed / 10) + 1
                logger.info("Moving camera %s -> %s at speed %d", camera_ip, direction, true_speed)
                send_api_request(f"http://{pi_ip}:8081", f"/move/{camera_ip}?direction={direction}&speed={true_speed}")
            else:
                logger.info("Stopping movement for camera %s", camera_ip)
                send_api_request(f"http://{pi_ip}:8081", f"/stop/{camera_ip}")

        elif button_id == "zoom-input":
            if zoom_level is not None:
                true_zoom = int(zoom_level * 64 / 100)
                logger.info("Zooming camera %s to level %d", camera_ip, true_zoom)
                send_api_request(f"http://{pi_ip}:8081", f"/zoom/{camera_ip}/{true_zoom}")

    except Exception as e:
        logger.warning("Failed to send command to camera %s via Pi %s: %s", camera_ip, pi_ip, e)

    return no_update


@app.callback(
    Output("stream-timer", "disabled"),
    Output("detection-status", "data"),
    Input("start-stream", "n_clicks"),
    Input("stop-stream", "n_clicks"),
    prevent_initial_call=True,
)
def control_detection(start_clicks, stop_clicks):
    """
    Callback to control the stream timer and detection status.

    Triggered by clicks on the start or stop stream buttons.
    Sets a global start time when streaming begins and disables the timer when stopped.

    Returns
    -------
    Tuple[bool, str] or Tuple[no_update, no_update]
        - Whether the timer should be disabled.
        - The current detection status ("running", "stopped", or no_update).
    """
    global start_time
    triggered = ctx.triggered_id

    logger.debug("[control_detection] Triggered by: %s", triggered)

    if triggered == "start-stream":
        start_time = datetime.datetime.now()
        logger.info("Stream started at %s", start_time)
        return False, "running"  # Enable timer

    elif triggered == "stop-stream":
        logger.info("Stream stopped")
        start_time = None
        return True, "stopped"  # Disable timer

    return no_update, no_update


@app.callback(
    Output("stream-status", "children"),
    Input("stream-timer", "n_intervals"),
    State("detection-status", "data"),
    prevent_initial_call=True,
)
def update_status(n, detection_status):
    """
    Callback to update the stream status banner with elapsed time since stream start.

    Triggered periodically by the stream timer. Displays a warning banner if detection is inactive.

    Parameters
    ----------
    n : int
        Number of timer intervals elapsed.
    detection_status : str
        Current status of detection ("running", "stopped", etc.).

    Returns
    -------
    html.Div or str
        HTML elements displaying stream status, or empty string if not applicable.
    """
    if detection_status == "running" and start_time:
        elapsed = datetime.datetime.now() - start_time
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        timer_text = f"{minutes:02d}:{seconds:02d}"

        logger.debug("[update_status] Detection inactive since %s", timer_text)

        return html.Div(
            [
                html.Span(
                    "🔴 Live stream",
                    style={
                        "backgroundColor": "#f99",
                        "color": "black",
                        "borderRadius": "6px",
                        "padding": "4px 8px",
                        "marginRight": "8px",
                        "fontWeight": "bold",
                    },
                ),
                html.Span(
                    f"⚠️ Levée de doute en cours, la détection n'est plus active depuis {timer_text}",
                    style={"color": "orange", "fontWeight": "bold"},
                ),
            ]
        )
    else:
        logger.debug("[update_status] No active stream or start_time missing")
        return ""


@app.callback(
    Output("pose-buttons", "children"),
    Input("camera-select", "value"),
    State("pi-cameras", "data"),
    prevent_initial_call=True,
)
def update_pose_buttons(camera_name, pi_cameras):
    """
    Callback to generate pose buttons based on the selected camera.

    Parameters
    ----------
    camera_name : str
        Name of the selected camera.
    pi_cameras : dict
        Dictionary of camera configurations retrieved from the Pi.

    Returns
    -------
    List[html.Button] or str
        A list of pose buttons with azimuth labels, or an empty string if camera is not found.
    """
    if not camera_name or not pi_cameras:
        logger.debug("[update_pose_buttons] Missing camera name or pi_cameras")
        return ""

    camera_info = pi_cameras.get(camera_name)
    if not camera_info:
        logger.warning("[update_pose_buttons] Camera '%s' not found in pi_cameras", camera_name)
        return ""

    poses = camera_info.get("poses", [])
    azimuths = camera_info.get("azimuths", [])

    if len(poses) != len(azimuths):
        logger.warning("[update_pose_buttons] Mismatched poses and azimuths for camera '%s'", camera_name)
        return ""

    logger.debug("[update_pose_buttons] Generating %d pose buttons for camera '%s'", len(poses), camera_name)

    buttons = [
        html.Button(
            f"{az}°",
            id={"type": "pose-button", "camera": camera_name, "index": pose_id},
            n_clicks=0,
            style={
                "background": "none",
                "border": "2px solid #098386",
                "borderRadius": "8px",
                "fontSize": "16px",
                "cursor": "pointer",
                "padding": "6px 12px",
                "color": "#098386",
            },
        )
        for pose_id, az in zip(poses, azimuths, strict=True)
    ]

    return buttons


@app.callback(
    Input({"type": "pose-button", "camera": ALL, "index": ALL}, "n_clicks"),
    State("camera-select", "value"),
    State("pi-cameras", "data"),
    State("available-stream-dropdown", "value"),
    State("available-stream", "data"),
    prevent_initial_call=True,
)
def move_to_pose(n_clicks_list, camera_name, pi_cameras, site_name, available_stream):
    """
    Callback to move a camera to a specific pose when a pose button is clicked.

    Parameters
    ----------
    n_clicks_list : List[int]
        List of click counts for each pose button.
    camera_name : str
        Name of the selected camera.
    pi_cameras : dict
        Camera data including IP and pose info.
    site_name : str
        Selected site for streaming.
    available_stream : dict
        Mapping from site names to their associated Pi IPs.

    Returns
    -------
    None
        This callback has no output; it sends a request to move the camera.
    """
    triggered = ctx.triggered_id

    if not triggered or not pi_cameras or not camera_name:
        logger.debug("[move_to_pose] No valid trigger or data missing")
        raise PreventUpdate

    triggered_camera = triggered.get("camera")
    pose_id = triggered.get("index")

    if triggered_camera != camera_name:
        logger.debug("[move_to_pose] Triggered camera '%s' != selected camera '%s'", triggered_camera, camera_name)
        raise PreventUpdate

    camera_info = pi_cameras.get(camera_name)
    if not camera_info:
        logger.warning("[move_to_pose] Camera info not found for '%s'", camera_name)
        raise PreventUpdate

    camera_ip = camera_info.get("ip")
    pi_ip = available_stream.get(site_name)
    if not pi_ip or not camera_ip:
        logger.warning("[move_to_pose] Missing IP for site '%s' or camera '%s'", site_name, camera_name)
        raise PreventUpdate

    pi_api_url = f"http://{pi_ip}:8081"

    try:
        response = requests.post(f"{pi_api_url}/move/{camera_ip}?pose_id={pose_id}&speed=50")
        logger.info("[move_to_pose] Moved camera '%s' to pose '%s': %s", camera_name, pose_id, response.json())
    except Exception as e:
        logger.error("[move_to_pose] Error moving camera '%s' to pose '%s': %s", camera_name, pose_id, e)
        raise PreventUpdate


@app.callback(
    Output("vision-layer", "children"),
    Input("camera-select", "value"),
    Input({"type": "pose-button", "camera": ALL, "index": ALL}, "n_clicks"),
    State("pi-cameras", "data"),
    State("api_cameras", "data"),
    prevent_initial_call=True,
)
def update_cone(camera_name, n_clicks_list, pi_cameras, api_cameras_data):
    """
    Callback to update the camera vision cone overlay when the camera or pose changes.

    Parameters
    ----------
    camera_name : str
        Selected camera name.
    n_clicks_list : List[int]
        List of click counts from pose buttons.
    pi_cameras : dict
        Local camera configuration data (IP, azimuths, poses, etc.).
    api_cameras_data : str
        JSON string of camera metadata from the API (e.g. location, opening angle).

    Returns
    -------
    List[Component] or no_update
        The vision cone polygon overlay, or no update if conditions are invalid.
    """
    logger.debug("[update_cone] Triggered with camera_name='%s'", camera_name)

    triggered = ctx.triggered_id

    if not triggered or not camera_name or not pi_cameras or not api_cameras_data:
        logger.debug("[update_cone] Missing required data")
        raise PreventUpdate

    camera_info = pi_cameras.get(camera_name)
    if not camera_info:
        logger.warning("[update_cone] Camera '%s' not found in pi_cameras", camera_name)
        raise PreventUpdate

    try:
        df_cams = pd.read_json(StringIO(api_cameras_data), orient="split")
        row = df_cams[df_cams["name"] == camera_name]
    except Exception as e:
        logger.error("[update_cone] Failed to parse API camera data: %s", e)
        raise PreventUpdate

    if row.empty:
        logger.warning("[update_cone] Camera '%s' not found in API metadata", camera_name)
        raise PreventUpdate

    site_lat = float(row["lat"].values[0])
    site_lon = float(row["lon"].values[0])
    opening_angle = int(row["angle_of_view"].values[0])

    poses = camera_info.get("poses", [])
    azimuths = camera_info.get("azimuths", [])

    try:
        # Case 1: camera just selected
        if triggered == "camera-select":
            pose_index = 0
        else:
            pose_id = int(triggered["index"])
            pose_index = poses.index(pose_id)

        new_azimuth = azimuths[pose_index]
        logger.info("[update_cone] Building cone for camera='%s' at azimuth=%d°", camera_name, new_azimuth)

        cone, _ = build_vision_polygon(
            site_lat=site_lat,
            site_lon=site_lon,
            azimuth=new_azimuth,
            opening_angle=opening_angle,
            dist_km=cfg.CAM_RANGE_KM,
        )
        return [cone]

    except Exception as e:
        logger.error("[update_cone] Error building vision cone: %s", e)
        return no_update


@app.callback(
    Output("available-stream-dropdown", "value"),
    Input("selected-camera-info", "data"),
    State("available-stream", "data"),
    prevent_initial_call=True,
)
def sync_dropdown_from_camera_info(camera_info, available_stream):
    """
    Callback to synchronize the stream dropdown value based on the selected camera info.

    Extracts the site name from the selected camera and updates the dropdown if valid.

    Parameters
    ----------
    camera_info : Tuple[str, int]
        Selected camera name and azimuth from the UI.
    available_stream : dict
        Mapping of site names to their associated Pi IPs.

    Returns
    -------
    str or PreventUpdate
        The site name to set in the dropdown, or prevent update if not found.
    """
    logger.debug("[sync_dropdown_from_camera_info] Triggered with: %s", camera_info)

    if not camera_info or not available_stream:
        raise exceptions.PreventUpdate

    cam_name, _ = camera_info
    site_name = cam_name[:-3].strip().lower()

    logger.debug("[sync_dropdown_from_camera_info] Extracted site_name='%s'", site_name)

    if site_name not in available_stream:
        logger.warning("[sync_dropdown_from_camera_info] Site '%s' not in available_stream", site_name)
        raise exceptions.PreventUpdate

    logger.info("[sync_dropdown_from_camera_info] Setting stream dropdown to '%s'", site_name)
    return site_name


@app.callback(
    Output("selected-camera-pose", "data"),
    Output("pi-cameras", "data"),
    Output("camera-select", "options"),
    Output("camera-select", "value"),
    Input("available-stream-dropdown", "value"),
    State("available-stream", "data"),
    State("selected-camera-info", "data"),
    prevent_initial_call=True,
)
def get_pi_camera_from_dropdown(site_name, available_stream, camera_info):
    """
    Callback to retrieve Pi camera info and set the default pose and camera selection.

    Parameters
    ----------
    site_name : str
        Selected site from the dropdown.
    available_stream : dict
        Mapping from site name to Pi IP.
    camera_info : Tuple[str, int] or None
        Previously selected camera and azimuth (optional).

    Returns
    -------
    Tuple[dict, dict, List[dict], str]
        - Pose data with pi_ip,
        - All cameras retrieved from the Pi,
        - Options for camera dropdown,
        - Default selected camera name.
    """
    logger.debug("[get_pi_camera_from_dropdown] Triggered with site: %s", site_name)

    if not site_name or not available_stream:
        raise PreventUpdate

    pi_ip = available_stream.get(site_name)
    if not pi_ip:
        logger.warning("No Pi IP found for site '%s'", site_name)
        raise PreventUpdate

    pi_api_url = f"http://{pi_ip}:8081"
    logger.info("Querying Pi at: %s", pi_api_url)

    try:
        pi_cameras = fetch_cameras(pi_api_url)
    except Exception as e:
        logger.error("Error fetching cameras from %s: %s", pi_api_url, e)
        raise PreventUpdate

    if not pi_cameras:
        logger.warning("No cameras found on Pi at site '%s'", site_name)
        raise PreventUpdate

    first_cam_name = next(iter(pi_cameras.keys()))
    cam_info = pi_cameras[first_cam_name]
    azimuths = cam_info.get("azimuths", [])
    poses = cam_info.get("poses", [])

    if not azimuths or not poses:
        logger.warning("Camera '%s' has no pose or azimuth info", first_cam_name)
        raise PreventUpdate

    target_azimuth = camera_info[1] if camera_info else azimuths[0]

    try:
        pose = find_closest_camera_pose(target_azimuth, pi_cameras)
    except Exception as e:
        logger.error("Error finding closest camera pose: %s", e)
        raise PreventUpdate

    pose_with_pi_ip = {**pose, "pi_ip": pi_ip}
    cam_options = [{"label": name, "value": name} for name in pi_cameras]

    return pose_with_pi_ip, pi_cameras, cam_options, first_cam_name


@app.callback(
    Output("video-stream", "src"),
    Input("available-stream-dropdown", "value"),
)
def update_stream_url(site_name):
    """
    Callback to update the video stream URL based on selected site.

    Parameters
    ----------
    site_name : str
        Selected site from dropdown.

    Returns
    -------
    str
        URL to the WEBRTC stream
    """
    if not site_name:
        raise PreventUpdate

    stream_url = f"{cfg.MEDIAMTX_SERVER_IP}:8889/{site_name}"
    logger.debug("Stream URL set to: %s", stream_url)
    return stream_url
