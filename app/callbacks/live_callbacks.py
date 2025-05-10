# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import base64
import datetime
import io
import time
from io import StringIO

import logging_config
import pandas as pd
import requests
from dash import ALL, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from utils.display import build_vision_polygon
from utils.live_stream import fetch_cameras, find_closest_camera_pose, send_api_request

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


start_time = None
last_command_time = time.time()  # Track the last command time


@app.callback(
    Output("available-stream-sites-dropdown", "value"),
    Input({"type": "site-marker", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def update_dropdown_on_marker_click(n_clicks_list):
    triggered = ctx.triggered_id
    if triggered and isinstance(triggered, dict):
        return triggered["index"]
    return no_update


# Set Camera
@app.callback(
    Output("pi_api_url", "data"),
    Output("pi_cameras", "data"),
    Input("available-stream-sites-dropdown", "value"),
    State("available-stream-sites", "data"),
)
def fetch_cameras_from_pi(site_name, available_stream):
    if not site_name or not available_stream:
        raise PreventUpdate

    logger.debug(f"[fetch_cameras_from_pi] site_name={site_name}, available_stream={available_stream}")

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

    return pi_api_url, pi_cameras


@app.callback(
    Output("stream-current-azimuth", "value"),
    Output("trigered_from_alert", "data"),
    Input("pi_cameras", "data"),
    State("trigered_from_alert", "data"),
    State("selected-camera-info", "data"),
)
def set_azimuth(pi_cameras, trigered_from_alert, selected_camera_info):
    if trigered_from_alert:
        print(selected_camera_info[1], False)
        return selected_camera_info[1], False

    else:
        raise PreventUpdate


@app.callback(
    Output("current_camera", "data"),
    Output("stream-camera-name", "children"),
    Output("stream-preset-azimuths", "children"),
    Input("stream-current-azimuth", "value"),
    State("pi_cameras", "data"),
    prevent_initial_call=True,
)
def set_current_camera(target_azimuth, pi_cameras):
    if target_azimuth is None or not pi_cameras:
        raise PreventUpdate

    camera, signed_shift = find_closest_camera_pose(target_azimuth, pi_cameras)

    cam_name = camera.get("name")
    azimuths = pi_cameras.get(cam_name, {}).get("azimuths")
    az_string = str(azimuths)

    current_camera = {
        "camera": camera,
        "pose_shift": signed_shift,
    }

    return current_camera, cam_name, az_string


@app.callback(
    Output("zoom-input", "value"),
    Output("speed-input", "value"),
    Input("current_camera", "data"),
    prevent_initial_call=True,
)
def reset_zoom_and_speed_on_camera_change(current_camera):
    if not current_camera:
        raise PreventUpdate

    logger.info(
        f"[reset_zoom_and_speed] Resetting zoom & speed due to camera change: {current_camera['camera'].get('name')}"
    )

    return 0, 0  # or any default you prefer, like 10, 50 etc.


@app.callback(
    Output("stream-start-time", "data"),
    Output("stream-timer", "disabled"),
    Output("inactivity-modal", "is_open"),
    Output("hide-stream-flag", "data"),
    Output("stream-status", "children"),
    Input("current_camera", "data"),
    Input("stream-timer", "n_intervals"),
    State("pi_api_url", "data"),
    State("stream-start-time", "data"),
    State("detection-status", "data"),
    prevent_initial_call=True,
)
def manage_stream_ui(current_camera, n_intervals, pi_api_url, stream_start_iso, detection_status):
    triggered = ctx.triggered_id

    # 🚀 Triggered by selecting a new camera
    if triggered == "current_camera":
        if not current_camera or not pi_api_url:
            raise PreventUpdate

        camera_ip = current_camera.get("camera", {}).get("ip")
        if not camera_ip:
            raise PreventUpdate

        logger.info(f"[start_stream] Starting stream for {camera_ip}")
        send_api_request(pi_api_url, f"/start_stream/{camera_ip}")

        now_iso = datetime.datetime.now().isoformat()
        return now_iso, False, False, False, ""  # start time, timer enabled, modal closed, flag false, no banner

    # ⏱️ Triggered by timer tick
    if triggered == "stream-timer":
        if detection_status != "running" or not stream_start_iso:
            return no_update, no_update, False, False, ""

        try:
            start_time = datetime.datetime.fromisoformat(stream_start_iso)
            elapsed = datetime.datetime.now() - start_time
            seconds_elapsed = int(elapsed.total_seconds())

            # ⛔ After 120s, hide warning + open modal + disable timer
            if seconds_elapsed > 120:
                logger.info("[stream monitor] Inactivity threshold reached.")
                return no_update, True, True, True, ""

            # ✅ Still under threshold, display status
            minutes, seconds = divmod(seconds_elapsed, 60)
            timer_text = f"{minutes:02d}:{seconds:02d}"

            status_banner = html.Div(
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

            return no_update, no_update, False, False, status_banner

        except Exception as e:
            logger.warning(f"[stream monitor] Failed to parse time or generate banner: {e}")
            return no_update, no_update, False, False, ""

    return no_update, no_update, False, False, ""


@app.callback(
    Output("dummy-output", "children"),
    Input("current_camera", "data"),
    Input("move-up", "n_clicks"),
    Input("move-down", "n_clicks"),
    Input("move-left", "n_clicks"),
    Input("move-right", "n_clicks"),
    Input("stop-move", "n_clicks"),
    Input("zoom-input", "value"),
    State("speed-input", "value"),
    State("pi_api_url", "data"),
    prevent_initial_call=True,
)
def control_camera(current_camera, up, down, left, right, stop, zoom_level, move_speed, pi_api_url):
    if not ctx.triggered or not current_camera:
        raise PreventUpdate

    logger.debug(f"[control_camera] Triggered by: {ctx.triggered_id}")
    logger.debug(f"[control_camera] Current camera data: {current_camera}")

    global last_command_time
    last_command_time = time.time()

    trigger = ctx.triggered_id
    camera = current_camera.get("camera", {})
    pose_shift = current_camera.get("pose_shift", 0)

    camera_ip = camera.get("ip")
    pose_id = camera.get("pose_id")

    if not pi_api_url or not camera_ip:
        raise PreventUpdate

    direction_map = {
        "move-up": "Up",
        "move-down": "Down",
        "move-left": "Left",
        "move-right": "Right",
        "stop-move": "Stop",
    }

    try:
        # 🔁 Case 1: Triggered by current_camera
        if trigger == "current_camera":
            logger.info(f"[AUTO] Triggered by camera pose change for {camera_ip}")

            # Move to preset pose if defined
            if pose_id is not None:
                logger.info(f"[AUTO] Moving {camera_ip} to preset pose {pose_id}")
                send_api_request(pi_api_url, f"/move/{camera_ip}?pose_id={pose_id}&speed=50")
                time.sleep(1.5)  # Allow some delay before fine adjustment

            # Apply signed shift
            if abs(pose_shift) >= 1:
                direction = "Right" if pose_shift > 0 else "Left"
                degrees = abs(pose_shift)
                logger.info(f"[AUTO] Applying fine shift of {degrees:.2f}° to the {direction} for {camera_ip}")
                send_api_request(pi_api_url, f"/move/{camera_ip}?direction={direction}&degrees={degrees:.2f}&speed=4")

        # 🧑‍💻 Case 2: Manual PTZ controls
        elif trigger in direction_map:
            direction = direction_map[trigger]
            true_speed = int(move_speed / 10) + 1
            if direction != "Stop":
                logger.info(f"[MANUAL] Moving {camera_ip} -> {direction} at speed {true_speed}")
                send_api_request(pi_api_url, f"/move/{camera_ip}?direction={direction}&speed={true_speed}")
            else:
                logger.info(f"[MANUAL] Stopping movement for {camera_ip}")
                send_api_request(pi_api_url, f"/stop/{camera_ip}")

        # 🔍 Case 3: Zoom input change
        elif trigger == "zoom-input":
            if zoom_level is not None:
                true_zoom = int(zoom_level * 41 / 100)
                logger.info(f"[MANUAL] Zooming {camera_ip} to level {true_zoom}")
                send_api_request(pi_api_url, f"/zoom/{camera_ip}/{true_zoom}")

    except Exception as e:
        logger.warning(f"[ERROR] Failed to control camera {camera_ip} via Pi {pi_api_url}: {e}")

    return no_update


@app.callback(
    Output("vision_polygons-stream", "children"),
    Output("map-stream", "center"),
    Input("current_camera", "data"),
    Input("zoom-input", "value"),
    State("api_cameras", "data"),
    prevent_initial_call=True,
)
def update_cone_and_center_from_current_camera(current_camera, zoom_level, api_cameras_data):
    logger.debug("[update_cone_and_center_from_current_camera] Triggered")

    if not current_camera or not api_cameras_data:
        raise PreventUpdate

    camera = current_camera.get("camera", {})
    pose_shift = current_camera.get("pose_shift", 0)
    cam_name = camera.get("name")
    pose_id = camera.get("pose_id")
    azimuths = camera.get("azimuths", [])
    poses = camera.get("poses", [])

    if cam_name is None or pose_id is None or not azimuths or not poses:
        logger.warning(f"[update_cone_and_center_from_current_camera] Incomplete camera data: {camera}")
        raise PreventUpdate

    try:
        df_cams = pd.read_json(StringIO(api_cameras_data), orient="split")
        row = df_cams[df_cams["name"] == cam_name]
    except Exception as e:
        logger.error(f"[update_cone_and_center_from_current_camera] Failed to parse API camera data: {e}")
        raise PreventUpdate

    if row.empty:
        logger.warning(f"[update_cone_and_center_from_current_camera] Camera '{cam_name}' not found in API data")
        raise PreventUpdate

    try:
        site_lat = float(row["lat"].values[0])
        site_lon = float(row["lon"].values[0])

        # FOV based on zoom input
        def fov_zoom(z):
            return 55.59044 - 2.00815 * z + 0.01886 * z**2

        zoom_level_converted = int(zoom_level * 41 / 100)
        opening_angle = int(fov_zoom(zoom_level_converted))

        pose_index = poses.index(pose_id)
        base_azimuth = azimuths[pose_index]
        adjusted_azimuth = base_azimuth + pose_shift

        logger.info(
            f"[update_cone_and_center] Drawing cone for '{cam_name}' at azimuth={adjusted_azimuth:.2f}° (FOV={opening_angle:.2f}°)"
        )

        cone, _ = build_vision_polygon(
            site_lat=site_lat,
            site_lon=site_lon,
            azimuth=adjusted_azimuth,
            opening_angle=opening_angle,
            dist_km=cfg.CAM_RANGE_KM,
        )

        return [cone], [site_lat, site_lon]

    except Exception as e:
        logger.error(f"[update_cone_and_center_from_current_camera] Error computing vision cone: {e}")
        return no_update, no_update


@app.callback(
    Output("video-stream", "src"),
    Input("available-stream-sites-dropdown", "value"),
    Input("hide-stream-flag", "data"),
)
def update_stream_url(site_name, hide_flag):
    if hide_flag:
        logger.info("[update_stream_url] Stream hidden due to inactivity.")
        return None

    if not site_name:
        raise PreventUpdate

    return f"{cfg.MEDIAMTX_SERVER_IP}:8889/{site_name}"


@app.callback(
    Output("capture-modal", "is_open"),
    Output("captured-image", "src"),
    Output("download-captured-image", "href"),
    Input("capture-image-button", "n_clicks"),
    State("current_camera", "data"),
    State("pi_api_url", "data"),
    prevent_initial_call=True,
)
def open_capture_modal(n_clicks, current_camera, api_url):
    if not current_camera or not api_url:
        print("Missing camera or API URL")
        return False, "", ""

    global last_command_time
    last_command_time = time.time()

    camera_id = current_camera["camera"].get("ip")
    if not camera_id:
        print("No IP in current_camera data")
        return False, "", ""

    try:
        resp = requests.get(f"{api_url}/capture/{camera_id}", timeout=5)
        if resp.status_code != 200:
            print(f"Non-200 response: {resp.status_code}")
            return False, "", ""

        if not resp.content or len(resp.content) < 100:
            print(f"Image too small or empty: {len(resp.content)} bytes")
            return False, "", ""

        # Convert image to base64 for display
        image_bytes = io.BytesIO(resp.content).getvalue()
        base64_img = base64.b64encode(image_bytes).decode("utf-8")
        img_src = f"data:image/jpeg;base64,{base64_img}"

        print("✅ Image capture successful, displaying modal.")
        return True, img_src, img_src

    except Exception as e:
        print(f"❌ Exception during image capture: {e}")
        return False, "", ""
