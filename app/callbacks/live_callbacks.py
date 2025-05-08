# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import datetime
from io import StringIO

import pandas as pd
import requests
from dash import Input, Output, State, callback_context, ctx, exceptions, html, no_update
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from utils.display import build_vision_polygon
from utils.live_stream import fetch_cameras, find_closest_camera_pose  # replace with actual import


# API Communication
def send_api_request(FASTAPI_URL, endpoint: str):
    try:
        response = requests.post(f"{FASTAPI_URL}{endpoint}")
        return response.json().get("message", "Unknown response")
    except requests.exceptions.RequestException:
        return "Error: Could not reach API server."


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
    print("[control_camera] Triggered with args:", locals())
    ctx = callback_context
    if not ctx.triggered or not selected_camera:
        raise PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if selected_camera["camera"] != camera_id:
        raise PreventUpdate

    # Use the Pi IP instead of the camera IP
    pi_ip = selected_camera.get("pi_ip")
    if not pi_ip:
        raise PreventUpdate

    direction_map = {
        "move-up": "Up",
        "move-down": "Down",
        "move-left": "Left",
        "move-right": "Right",
        "stop-move": "Stop",
    }

    if button_id == "start-stream":
        send_api_request(f"http://{pi_ip}:8081", f"/start_stream/{camera_id}")

    elif button_id == "stop-stream":
        send_api_request(f"http://{pi_ip}:8081", "/stop_stream")

    elif button_id in direction_map:
        direction = direction_map[button_id]
        if direction != "Stop":
            true_speed = int(move_speed / 10) + 1
            print("mooooove to ", f"http://{pi_ip}:8081", f"/move/{camera_id}?direction={direction}&speed={true_speed}")
            send_api_request(f"http://{pi_ip}:8081", f"/move/{camera_id}?direction={direction}&speed={true_speed}")
        else:
            send_api_request(f"http://{pi_ip}:8081", f"/stop/{camera_id}")

    elif button_id == "zoom-input":
        if zoom_level is not None:
            true_zoom = int(zoom_level * 64 / 100)  # because backend expects 0-64
            send_api_request(f"http://{pi_ip}:8081", f"/zoom/{camera_id}/{true_zoom}")

    return no_update


start_time = None


@app.callback(
    Output("stream-timer", "disabled"),
    Output("detection-status", "data"),
    Input("start-stream", "n_clicks"),
    Input("stop-stream", "n_clicks"),
    prevent_initial_call=True,
)
def control_detection(start_clicks, stop_clicks):
    print("[control_detection] Triggered with args:", locals())

    triggered = ctx.triggered_id
    global start_time

    if triggered == "start-stream":
        start_time = datetime.datetime.now()
        return False, "running"  # Enable timer
    elif triggered == "stop-stream":
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
    if detection_status == "running" and start_time:
        elapsed = datetime.datetime.now() - start_time
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        timer_text = f"{minutes:02d}:{seconds:02d}"
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
                html.Span(f"Levée de doute en cours, la détection n'est plus active depuis {timer_text}"),
            ]
        )
    else:
        return ""


@app.callback(
    Output("pose-buttons", "children"),
    Input("camera-select", "value"),
    State("pi-cameras", "data"),
    prevent_initial_call=True,
)
def update_pose_buttons(camera_name, pi_cameras):
    print("[update_pose_buttons] Triggered with args:", locals())

    if not camera_name or not pi_cameras:
        return ""

    camera_info = pi_cameras.get(camera_name)
    if not camera_info:
        return ""

    buttons = []
    poses = camera_info.get("poses", [])
    azimuths = camera_info.get("azimuths", [])

    for pose_id, az in zip(poses, azimuths, strict=True):
        buttons.append(
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
        )

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
    print("[move_to_pose] Triggered with args:", locals())

    triggered = ctx.triggered_id

    if not triggered or not pi_cameras or not camera_name:
        raise PreventUpdate

    triggered_camera = triggered["camera"]
    pose_id = triggered["index"]

    if triggered_camera != camera_name:
        raise PreventUpdate

    camera_info = pi_cameras.get(camera_name)
    if not camera_info:
        raise PreventUpdate

    camera_ip = camera_info["ip"]
    pi_ip = available_stream.get(site_name)
    if not pi_ip:
        print(f"No Pi IP found for {site_name}")
        raise PreventUpdate

    pi_api_url = f"http://{pi_ip}:8081"

    try:
        response = requests.post(f"{pi_api_url}/move/{camera_ip}?pose_id={pose_id}&speed=50")
        print("Move to pose response:", response.json())
    except Exception as e:
        print(f"Move to pose error: {e}")
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
    print("[update_cone] Triggered with args:", locals())

    triggered = ctx.triggered_id

    if not triggered or not camera_name or not pi_cameras or not api_cameras_data:
        raise PreventUpdate

    camera_info = pi_cameras.get(camera_name)
    if not camera_info:
        raise PreventUpdate

    # Load full camera metadata
    df_cams = pd.read_json(StringIO(api_cameras_data), orient="split")
    row = df_cams[df_cams["name"] == camera_name]

    if row.empty:
        print(f"[update_cone] Camera {camera_name} not found in metadata.")
        raise PreventUpdate

    site_lat = float(row["lat"].values[0])
    site_lon = float(row["lon"].values[0])
    opening_angle = int(row["angle_of_view"].values[0])
    dist_km = 10  # If you want to replace this, extract it from elsewhere or make it a constant

    poses = camera_info.get("poses", [])
    azimuths = camera_info.get("azimuths", [])

    try:
        # Case 1: Camera selection
        if triggered == "camera-select":
            pose_index = 0

        # Case 2: Pose button click
        else:
            pose_id = int(triggered["index"])
            pose_index = poses.index(pose_id)

        new_azimuth = azimuths[pose_index]
        cone, _ = build_vision_polygon(
            site_lat=site_lat,
            site_lon=site_lon,
            azimuth=new_azimuth,
            opening_angle=opening_angle,
            dist_km=dist_km,
        )
        return [cone]

    except Exception as e:
        print(f"Error building vision cone: {e}")
        return no_update


@app.callback(
    Output("available-stream-dropdown", "value"),
    Input("selected-camera-info", "data"),
    State("available-stream", "data"),
    prevent_initial_call=True,
)
def sync_dropdown_from_camera_info(camera_info, available_stream):
    print("[sync_dropdown_from_camera_info] Triggered with:", camera_info)

    if not camera_info or not available_stream:
        raise exceptions.PreventUpdate

    cam_name, _ = camera_info
    site_name = cam_name[:-3].strip().lower()

    print("!!!!!! sync_dropdown_from_camera_info", site_name, available_stream)

    if site_name not in available_stream:
        print(f"[sync_dropdown_from_camera_info] '{site_name}' not in available_stream")
        raise exceptions.PreventUpdate

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
    print("[get_pi_camera_from_dropdown] Triggered with:", site_name)

    if not site_name or not available_stream:
        raise PreventUpdate

    pi_ip = available_stream.get(site_name)
    if not pi_ip:
        print(f"No Pi IP found for {site_name}")
        raise PreventUpdate

    pi_api_url = f"http://{pi_ip}:8081"
    print(f"Querying Pi at: {pi_api_url}")

    try:
        pi_cameras = fetch_cameras(pi_api_url)
    except Exception as e:
        print(f"Error fetching cameras from {pi_api_url}: {e}")
        raise PreventUpdate

    if not pi_cameras:
        print("No cameras found")
        raise PreventUpdate

    first_cam_name = next(iter(pi_cameras.keys()))
    cam_info = pi_cameras[first_cam_name]
    azimuths = cam_info.get("azimuths", [])
    poses = cam_info.get("poses", [])

    if not azimuths or not poses:
        print("Camera has no pose or azimuth info")
        raise PreventUpdate

    # Use azimuth from selected-camera-info, fallback to azimuth[0]
    target_azimuth = camera_info[1] if camera_info else azimuths[0]

    try:
        pose = find_closest_camera_pose(target_azimuth, pi_cameras)
    except Exception as e:
        print(f"Error finding closest camera pose: {e}")
        raise PreventUpdate

    pose_with_pi_ip = {**pose, "pi_ip": pi_ip}
    cam_options = [{"label": k, "value": k} for k in pi_cameras.keys()]

    return pose_with_pi_ip, pi_cameras, cam_options, first_cam_name


@app.callback(
    Output("video-stream", "src"),
    Input("available-stream-dropdown", "value"),
)
def update_stream_url(site_name):
    if not site_name:
        raise PreventUpdate
    stream_url = f"{cfg.MEDIAMTX_SERVER_IP}:8889/{site_name}"
    return stream_url
