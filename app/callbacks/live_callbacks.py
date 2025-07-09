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
from dash import ALL, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
from main import app
from reolink_api_client import ReolinkAPIClient

import config as cfg
from utils.display import build_vision_polygon
from utils.live_stream import find_closest_camera_pose, fov_zoom

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)

INACTIVITY_TIMEOUT = 120
start_time = None
last_command_time = time.time()


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
        logger.warning(f"No Pi IP found for site '{site_name}'")
        raise PreventUpdate

    pi_api_url = f"http://{pi_ip}:8081"
    logger.info(f"Querying Pi at: {pi_api_url}")

    try:
        # Use the ReolinkAPIClient instead of the old fetch_cameras
        client = ReolinkAPIClient(pi_api_url)
        data = client.get_camera_infos()  # this calls /info/camera_infos

        pi_cameras = {}
        for cam in data.get("cameras", []):
            name = cam.get("name", f"Camera {cam.get('id')}")
            if name:
                pi_cameras[name] = {
                    "ip": cam.get("ip"),
                    "poses": cam.get("poses", []),
                    "azimuths": cam.get("azimuths", []),
                }

    except Exception as e:
        logger.error(f"[fetch_cameras_from_pi] Error fetching cameras from {pi_api_url}: {e}")
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
    if trigered_from_alert and selected_camera_info:
        logger.debug(f"[set_azimuth] Setting from alert: azimuth={selected_camera_info[1]}")
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

        # Create a new client instance safely
        client = ReolinkAPIClient(pi_api_url)

        try:
            logger.info(f"[start_stream] Stoping patrol for {camera_ip}")
            client.stop_patrol(camera_ip)
            logger.info(f"[start_stream] Starting stream for {camera_ip}")
            client.start_stream(camera_ip)
        except Exception as e:
            logger.error(f"[start_stream] Failed to start stream for {camera_ip}: {e}")
            raise PreventUpdate

        now_iso = datetime.datetime.now().isoformat()
        return now_iso, False, False, False, ""  # start time, timer enabled, modal closed, flag false, no banner

    # ⏱️ Triggered by timer tick
    if triggered == "stream-timer":
        if detection_status != "running" or not stream_start_iso:
            return no_update, no_update, False, False, ""

        try:
            now = time.time()
            seconds_since_command = int(now - last_command_time)

            # Format time since last command
            minutes, seconds = divmod(seconds_since_command, 60)
            timer_text = f"{minutes:02d}:{seconds:02d}"

            # Total stream time
            stream_start = datetime.datetime.fromisoformat(stream_start_iso)
            total_elapsed = datetime.datetime.now() - stream_start
            total_minutes, total_seconds = divmod(int(total_elapsed.total_seconds()), 60)
            total_timer_text = f"{total_minutes:02d}:{total_seconds:02d}"

            if seconds_since_command > INACTIVITY_TIMEOUT:
                logger.info("[stream monitor] Inactivity threshold reached.")
                return no_update, True, True, True, ""

            status_banner = html.Div([
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
                    f"⚠️ Levée de doute en cours, détection inactive depuis {total_timer_text} - dernière action il y a {timer_text}",
                    style={"color": "orange", "fontWeight": "bold"},
                ),
            ])

            return no_update, no_update, False, False, status_banner

        except Exception as e:
            logger.warning(f"[stream monitor] Failed to track last command time: {e}")
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

    # Instantiate the API client
    client = ReolinkAPIClient(pi_api_url)

    direction_map = {
        "move-up": "Up",
        "move-down": "Down",
        "move-left": "Left",
        "move-right": "Right",
        "stop-move": "Stop",
    }

    try:
        # Case 1: Triggered by camera data change (automatic pose adjustment)
        if trigger == "current_camera":
            logger.info(f"[AUTO] Triggered by camera pose change for {camera_ip}")
            time.sleep(1)  # Let stream start

            # Move to preset pose if available
            if pose_id is not None:
                logger.info(f"[AUTO] Moving {camera_ip} to preset pose {pose_id}")
                client.move_camera(camera_ip, pose_id=pose_id, speed=50)
                time.sleep(1.5)  # Give time to settle

            # Apply fine adjustment
            if abs(pose_shift) >= 1:
                direction = "Right" if pose_shift > 0 else "Left"
                degrees = abs(pose_shift)
                logger.info(f"[AUTO] Applying fine shift of {degrees:.2f}° {direction} for {camera_ip}")
                client.move_camera(camera_ip, direction=direction, degrees=degrees, speed=4)

        # Case 2: Manual movement
        elif trigger in direction_map:
            direction = direction_map[trigger]
            true_speed = int(move_speed / 10) + 1
            if direction != "Stop":
                logger.info(f"[MANUAL] Moving {camera_ip} -> {direction} at speed {true_speed}")
                client.move_camera(camera_ip, direction=direction, speed=true_speed)
            else:
                logger.info(f"[MANUAL] Stopping movement for {camera_ip}")
                client.stop_camera(camera_ip)

        # Case 3: Zoom change
        elif trigger == "zoom-input":
            if zoom_level is not None:
                true_zoom = int(zoom_level * 41 / 100)
                logger.info(f"[MANUAL] Zooming {camera_ip} to level {true_zoom}")
                client.zoom(camera_ip, true_zoom)

    except Exception as e:
        logger.warning(f"[ERROR] Failed to control camera {camera_ip} via Pi {pi_api_url}: {e}")

    return no_update


@app.callback(
    Output("dummy-output2", "children"),
    Input("click-coords", "data"),
    State("current_camera", "data"),
    State("zoom-input", "value"),
    State("pi_api_url", "data"),
    prevent_initial_call=True,
)
def move_by_click(click_data, current_camera, zoom_value, pi_api_url):
    if not click_data or not current_camera:
        raise PreventUpdate

    camera = current_camera.get("camera", {})
    camera_ip = camera.get("ip")
    if not camera_ip or not pi_api_url:
        raise PreventUpdate

    global last_command_time
    last_command_time = time.time()

    # Instantiate the API client
    client = ReolinkAPIClient(pi_api_url)

    # --- 1. Extract click position ---
    x_percent = round((click_data["offsetX"] / click_data["width"]) * 100, 2)
    y_percent = round((click_data["offsetY"] / click_data["height"]) * 100, 2)

    # --- 2. Compute deviation from center ---
    dx = x_percent - 50  # positive = right
    dy = y_percent - 50  # positive = down

    # --- 3. Convert to degrees ---
    true_zoom = int(zoom_value * 41 / 100) if zoom_value is not None else 0
    fov_horizontal = fov_zoom(true_zoom)  # Assumes your function exists elsewhere
    fov_vertical = fov_horizontal * 41.7 / 54.2

    delta_azimuth = dx / 100 * fov_horizontal
    delta_tilt = dy / 100 * fov_vertical

    try:
        # --- 4. Horizontal movement ---
        if abs(delta_azimuth) >= 0.5:
            direction = "Right" if delta_azimuth > 0 else "Left"
            logger.info(f"[CLICK] Moving {direction} by {abs(delta_azimuth):.2f}° for {camera_ip}")
            client.move_camera(camera_ip, direction=direction, degrees=abs(delta_azimuth), speed=3)

        # --- 5. Vertical movement ---
        if abs(delta_tilt) >= 0.5:
            direction = "Down" if delta_tilt > 0 else "Up"
            logger.info(f"[CLICK] Moving {direction} by {abs(delta_tilt):.2f}° for {camera_ip}")
            client.move_camera(camera_ip, direction=direction, degrees=abs(delta_tilt), speed=2)

    except Exception as e:
        logger.warning(f"[ERROR] Click-to-move failed for {camera_ip}: {e}")

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

        zoom_level_converted = int(zoom_level * 41 / 100)
        opening_angle = int(fov_zoom(zoom_level_converted))

        pose_index = poses.index(pose_id)
        base_azimuth = azimuths[pose_index]
        adjusted_azimuth = base_azimuth + pose_shift

        logger.info(
            f"[update_cone_and_center] Drawing cone for '{cam_name}' at azimuth={adjusted_azimuth:.2f}° (FOV={opening_angle:.2f}°)"
        )

        cone = build_vision_polygon(
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

    print(f"{cfg.MEDIAMTX_SERVER_URL}/{site_name}")

    return f"{cfg.MEDIAMTX_SERVER_URL}/{site_name}"


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
        logger.error("Missing camera or API URL")
        return False, "", ""

    global last_command_time
    last_command_time = time.time()

    camera_ip = current_camera["camera"].get("ip")
    if not camera_ip:
        logger.error("No IP in current_camera data")
        return False, "", ""

    try:
        # Instantiate the API client
        client = ReolinkAPIClient(api_url)

        # Capture the image using the client
        img = client.capture_image(camera_ip)

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        if len(image_bytes) < 100:
            logger.error(f"Image too small or empty: {len(image_bytes)} bytes")
            return False, "", ""

        # Encode to base64
        base64_img = base64.b64encode(image_bytes).decode("utf-8")
        img_src = f"data:image/jpeg;base64,{base64_img}"

        logger.info("✅ Image capture successful, displaying modal.")
        return True, img_src, img_src

    except Exception as e:
        logger.error(f"❌ Exception during image capture: {e}")
        return False, "", ""


app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;
        return window.lastClick || null;
    }
    """,
    Output("click-coords", "data"),
    Input("click-overlay", "n_clicks"),
)

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Clickable Stream</title>
        {%favicon%}
        {%css%}
        <script>
            document.addEventListener("DOMContentLoaded", function () {
                document.body.addEventListener("click", function (e) {
                    const rect = e.target.getBoundingClientRect();
                    window.lastClick = {
                        offsetX: Math.round(e.clientX - rect.left),
                        offsetY: Math.round(e.clientY - rect.top),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    };
                });
            });
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""
