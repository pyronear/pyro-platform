# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json
import os
from datetime import date, datetime, timedelta, timezone
from io import BytesIO, StringIO

import boto3
import dash
import logging_config
import pandas as pd
from botocore.exceptions import ClientError
from dash import Input, Output, State, ctx
from dash.dependencies import ALL
from dash.exceptions import PreventUpdate
from dateutil.relativedelta import relativedelta  # type: ignore
from main import app
from translations import translate

import config as cfg
from services import api_client
from utils.display import (
    build_vision_polygon,
    convert_dt_to_local_tz,
    create_sequence_list,
    filter_bboxes_dict,
    prepare_archive,
)
from utils.telemetry import telemetry_client

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(Output("camera_status_button_text", "children"), Input("language", "data"))
def update_camera_status_button(lang):
    return [translate("camera_status", lang)]


@app.callback(Output("blinking_alarm_button_text", "children"), Input("language", "data"))
def update_blinking_alarm_button(lang):
    return [translate("blinking_alarm", lang)]


@app.callback(Output("home_button_text", "children"), Input("language", "data"))
def update_home_button(lang):
    return [translate("home", lang)]


@app.callback(Output("live_stream_button_text", "children"), Input("language", "data"))
def update_live_stream_button(lang):
    return [translate("live_stream", lang)]


@app.callback(
    Output("start-live-stream", "children"),
    Input("language", "data"),
)
def update_start_live_stream_button(lang):
    return translate("start_live_stream_button", lang)


@app.callback(
    Output("create-occlusion-mask", "children"),
    Input("language", "data"),
)
def update_create_occlusion_mask_button(lang):
    return translate("create_occlusion_mask", lang)


@app.callback(
    Output("language", "data"),
    Input("language-selector", "value"),
    prevent_initial_call="initial_duplicate",  # ne déclenche pas à l'initialisation si même valeur
)
def update_language_store(selected_lang):
    return selected_lang


# Create event list
@app.callback(
    Output("sequence-list-container", "children"),
    [
        Input("api_sequences", "data"),
    ],
    State("api_cameras", "data"),
    State("my-date-picker-single", "date"),
)
def update_event_list(api_sequences, cameras, selected_date):
    """
    Updates the event list based on changes in the events data

    Parameters:
    - api_detections (json): JSON formatted data containing current alerts information.

    Returns:
    - html.Div: A Div containing the updated list of alerts.
    """
    logger.info("update_event_list")

    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    cameras = pd.read_json(StringIO(cameras), orient="split")

    return create_sequence_list(api_sequences, cameras)


# Select the event id
@app.callback(
    [
        Output({"type": "event-button", "index": ALL}, "style"),
        Output("sequence_id_on_display", "data"),
        Output("auto-move-button", "n_clicks"),
        Output("custom_js_trigger", "title"),
    ],
    [
        Input({"type": "event-button", "index": ALL}, "n_clicks"),
    ],
    [
        State({"type": "event-button", "index": ALL}, "id"),
        State("api_sequences", "data"),
        State("sequence_id_on_display", "data"),
    ],
    prevent_initial_call=True,
)
def select_event_with_button(n_clicks, button_ids, api_sequences, sequence_id_on_display):
    """
    Handles event selection through button clicks.

    Parameters:
    - n_clicks (list): List of click counts for each event button.
    - button_ids (list): List of button IDs corresponding to events.
    - local_alerts (json): JSON formatted data containing current alert information.
    - sequence_id_on_display (int): Currently displayed event ID.

    Returns:
    - list: List of styles for event buttons.
    - int: ID of the event to display.
    - int: Number of clicks for the auto-move button reset.
    """
    logger.info("select_event_with_button")
    ctx = dash.callback_context
    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    if api_sequences.empty:
        return [[], 0, 1, "reset_zoom"]

    # Extracting the index of the clicked button
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id:
        button_index = json.loads(button_id)["index"]
    else:
        if len(button_ids):
            button_index = button_ids[0]["index"]
        else:
            button_index = 0

    user_name = ctx.states.get("user_name.data")

    if user_name:
        sequence_data = api_sequences[api_sequences["id"] == button_index].iloc[0]
        telemetry_client.capture(
            event="alert_selected",
            distinct_id=user_name,
            properties={
                "sequence_id": button_index,
                "camera_id": sequence_data["camera_id"],
                "is_wildfire": sequence_data.get("is_wildfire", None),
                "started_at": sequence_data["started_at"],
                "selection_method": "button_click",
                "total_sequences": len(api_sequences),
            },
        )

    # Highlight the button
    styles = []
    for button in button_ids:
        if button["index"] == button_index:
            styles.append(
                {
                    "backgroundColor": "#feba6a",
                },
            )  # Highlight style
        else:
            styles.append(
                {},
            )  # Default style

    return [styles, button_index, 1, "reset_zoom"]


@app.callback(
    [
        Output("main-image", "src"),
        Output("bbox-0", "style"),
        Output("bbox-1", "style"),
        Output("bbox-2", "style"),
        Output("image-slider", "max"),
        Output("image-slider", "marks"),
        Output("image-slider", "min"),
        Output("slider-container", "style"),
    ],
    [Input("image-slider", "value"), Input("sequence_on_display", "data")],
    [
        State("sequence-list-container", "children"),
        State("language", "data"),
        State("alert-end-date-value", "children"),
    ],
    prevent_initial_call=True,
)
def update_image_and_bbox(slider_value, sequence_on_display, sequence_list, lang, alert_end_value):
    no_alert_image_src = "./assets/images/no-alert-default.png"
    if lang == "es":
        no_alert_image_src = "./assets/images/no-alert-default-es.png"

    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")

    if sequence_on_display.empty or not len(sequence_list):
        return no_alert_image_src, *[{"display": "none"}] * 3, 0, {}, 0, {"display": "none"}

    images, boxes = zip(
        *((alert["url"], alert["processed_bboxes"]) for _, alert in sequence_on_display.iterrows() if alert["url"]),
        strict=False,
    )

    if not images:
        return no_alert_image_src, *[{"display": "none"}] * 3, 0, {}, 0, {"display": "none"}

    n_images = len(images)
    slider_value = slider_value % n_images
    img_src = images[slider_value]
    images_bbox_list = boxes[slider_value]

    bbox_styles = [{"display": "none"} for _ in range(3)]
    for i, (x0, y0, width, height) in enumerate(images_bbox_list[:3]):
        bbox_styles[i] = {
            "position": "absolute",
            "left": f"{x0}%",
            "top": f"{y0}%",
            "width": f"{width}%",
            "height": f"{height}%",
            "border": "2px solid red",
            "box-sizing": "border-box",
            "zIndex": "10",
            "display": "block",
        }

    try:
        if isinstance(alert_end_value, str) and alert_end_value.strip():
            last_time = datetime.strptime(alert_end_value.strip(), "%H:%M")
        else:
            raise ValueError("Empty or invalid date string")
    except Exception:
        last_time = datetime.now()

    marks = {i: (last_time - timedelta(seconds=30 * (n_images - 1 - i))).strftime("%H:%M:%S") for i in range(n_images)}

    return [img_src, *bbox_styles, n_images - 1, marks, 0, {"display": "block"}]


@app.callback(
    [
        Output("bbox-container", "style"),  # Update the style of the bounding box
        Output("hide-bbox-button", "style"),  # Update the style of the button
    ],
    [Input("hide-bbox-button", "n_clicks")],
    [State("hide-bbox-button", "style")],  # Get the current style of the button
    prevent_initial_call=True,
)
def toggle_bbox_visibility(n_clicks, button_style):
    """
    Toggles the visibility of the bounding box and updates the button style accordingly.

    Parameters:
    - n_clicks (int): Number of clicks on the hide/show button.
    - button_style (dict): Current style of the hide/show button.

    Returns:
    - dict: Updated style for the bounding box.
    - dict: Updated style for the hide/show button.
    """
    logger.info("toggle_bbox_visibility")
    if n_clicks % 2 == 0:
        bbox_style = {"display": "block"}  # Show the bounding box
        button_style["background-color"] = "#054546"  # Original button color
    else:
        bbox_style = {"display": "none"}  # Hide the bounding box
        button_style["background-color"] = "#098386"  # Darker color for the button

    return bbox_style, button_style


@app.callback(
    [
        Output("auto-move-state", "data"),
        Output("auto-move-button", "style"),  # Update the style of the button
    ],
    Input("auto-move-button", "n_clicks"),
    State("auto-move-state", "data"),
    State("auto-move-button", "style"),  # Get the current style of the button
    prevent_initial_call=True,
)
def toggle_auto_move(n_clicks, data, button_style):
    """
    Toggles the automatic movement of the image slider based on button clicks.

    Parameters:
    - n_clicks (int): Number of clicks on the auto-move button.
    - data (dict): Data about the current auto-move state.

    Returns:
    - dict: Updated auto-move state data.
    """
    if n_clicks % 2 == 0:  # Toggle between on and off states
        data["active"] = False
        button_style["background-color"] = "#098386"  # Darker color for the button

    else:
        data["active"] = True
        button_style["background-color"] = "#054546"  # Original button color
    return data, button_style


@app.callback(
    Output("image-slider", "value"),
    [Input("auto-slider-update", "n_intervals")],
    [
        State("image-slider", "value"),
        State("image-slider", "max"),
        State("auto-move-button", "n_clicks"),
        State("sequence-list-container", "children"),
    ],
    prevent_initial_call=True,
)
def auto_move_slider(n_intervals, current_value, max_value, auto_move_clicks, sequence_list):
    """
    Automatically moves the image slider based on a regular interval and the current auto-move state.

    Parameters:
    - n_intervals (int): Number of intervals passed since the start of the auto-move.
    - current_value (int): Current value of the image slider.
    - max_value (int): Maximum value of the image slider.
    - auto_move_clicks (int): Number of clicks on the auto-move button.
    - sequence_list (list): List of ongoing alerts.

    Returns:
    - int: Updated value for the image slider.
    """
    if auto_move_clicks % 2 != 0 and len(sequence_list):  # Auto-move is active and there is ongoing alerts
        return (current_value + 1) % (max_value + 1)
    else:
        raise PreventUpdate


# Map
@app.callback(
    [
        Output("vision_polygons", "children"),
        Output("map", "center"),
        Output("vision_polygons-md", "children"),
        Output("map-md", "center"),
        Output("alert-camera-value", "children"),
        Output("camera-location-value", "children"),
        Output("alert-azimuth-value", "children"),
        Output("alert-start-date-value", "children"),
        Output("alert-end-date-value", "children"),
        Output("alert-information", "style"),
    ],
    Input("sequence_on_display", "data"),
    [State("api_cameras", "data"), State("sequence_id_on_display", "data"), State("api_sequences", "data")],
    prevent_initial_call=True,
)
def update_map_and_alert_info(sequence_on_display, cameras, sequence_id_on_display, api_sequences):
    """
    Updates the map's vision polygons, center, and alert information based on the current alert data.

    Parameters:
    - alert_data (json): JSON formatted data for the selected event.

    Returns:
    - list: List of vision polygon elements to be displayed on the map.
    - list: New center coordinates for the map.
    - list: List of vision polygon elements to be displayed on the modal map.
    - list: New center coordinates for the modal map.
    - str: Camera information for the alert.
    - str: Camera location for the alert.
    - str: Detection angle for the alert.
    - str: Date of the alert.
    - dict: Style settings for alert information.
    - dict: Style settings for the slider container.
    """
    logger.info("update_map_and_alert_info")
    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")
    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    cameras = pd.read_json(StringIO(cameras), orient="split")

    if not sequence_on_display.empty:
        # Convert the 'bboxes' column to a list (empty lists if the original value was '[]').
        sequence_on_display["bboxes"] = sequence_on_display["bboxes"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() != "[]" else []
        )

        # Filter out rows where 'bboxes' is not empty and get the last one.
        # If all are empty, then simply get the last row of the DataFrame.
        def get_confidence(bboxes):
            if not bboxes:
                return -1  # or np.nan if you prefer
            return max(bbox[-1] for bbox in bboxes)

        # Compute confidence for each row
        sequence_on_display["max_conf"] = sequence_on_display["bboxes"].apply(get_confidence)

        # Filter out rows where bboxes is not empty
        non_empty = sequence_on_display[sequence_on_display["bboxes"].astype(bool)]

        # Get row with highest confidence or fallback to last row
        if not non_empty.empty:
            row_with_bboxes = non_empty.loc[non_empty["max_conf"].idxmax()]
        else:
            row_with_bboxes = sequence_on_display.iloc[-1]

        row_cam = cameras[cameras["id"] == row_with_bboxes["camera_id"]]
        lat, lon, angle_of_view = (
            row_cam[["lat"]].values.item(),
            row_cam[["lon"]].values.item(),
            row_cam[["angle_of_view"]].values.item(),
        )

        polygon, detection_azimuth = build_vision_polygon(
            site_lat=lat,
            site_lon=lon,
            azimuth=row_with_bboxes["azimuth"],
            opening_angle=angle_of_view,
            dist_km=cfg.CAM_RANGE_KM,
            bboxes=row_with_bboxes["bboxes"],
        )

        current_sequence = api_sequences[api_sequences["id"] == sequence_id_on_display].iloc[0]
        start_date_info = convert_dt_to_local_tz(lat, lon, current_sequence["started_at"]).split(" ")[-1]
        end_date_info = convert_dt_to_local_tz(lat, lon, current_sequence["last_seen_at"]).split(" ")[-1]
        cam_name = f"{row_cam['name'].values.item()[:-3].replace('_', ' ')} : {int(row_with_bboxes['azimuth'])}°"

        camera_info = f"{cam_name}"
        location_info = f"{lat:.4f}, {lon:.4f}"
        azimuth = int(current_sequence["cone_azimuth"])
        angle_info = f"{azimuth}°"

        return (
            polygon,
            [lat, lon],
            polygon,
            [lat, lon],
            camera_info,
            location_info,
            angle_info,
            start_date_info,
            end_date_info,
            {"display": "block"},
        )

    return (
        [],
        dash.no_update,
        [],
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        {"display": "none"},
    )


@app.callback(
    [Output("confirmation-modal", "style"), Output("to_acknowledge", "data")],
    [
        Input("acknowledge-button", "n_clicks"),
        Input("confirm-wildfire", "n_clicks"),
        Input("confirm-non-wildfire", "n_clicks"),
        Input("cancel-confirmation", "n_clicks"),
    ],
    [State("sequence_id_on_display", "data"), State("user_token", "data")],
    prevent_initial_call=True,
)
def acknowledge_event(
    acknowledge_clicks, confirm_wildfire, confirm_non_wildfire, cancel, sequence_id_on_display, user_token
):
    ctx = dash.callback_context

    logger.info("acknowledge_event")

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    user_name = ctx.states.get("user_name.data")

    # Modal styles
    modal_visible_style = {
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%, -50%)",
        "z-index": "1000",
        "background-color": "rgba(0, 0, 0, 0.5)",
    }
    modal_hidden_style = {"display": "none"}

    if triggered_id == "acknowledge-button":
        # Show the modal
        if acknowledge_clicks > 0:
            if user_name:
                telemetry_client.capture(
                    event="acknowledgment_modal_opened",
                    distinct_id=user_name,
                    properties={"sequence_id": sequence_id_on_display},
                )
            return modal_visible_style, dash.no_update

    elif triggered_id == "confirm-wildfire":
        # Send wildfire confirmation to the API
        api_client.token = user_token
        api_client.label_sequence(sequence_id_on_display, True)
        if user_name:
            telemetry_client.capture(
                event="alert_acknowledged",
                distinct_id=user_name,
                properties={"sequence_id": sequence_id_on_display, "classification": "wildfire", "action": "confirmed"},
            )
        return modal_hidden_style, sequence_id_on_display

    elif triggered_id == "confirm-non-wildfire":
        # Send non-wildfire confirmation to the API
        api_client.token = user_token
        api_client.label_sequence(sequence_id_on_display, False)
        if user_name:
            telemetry_client.capture(
                event="alert_acknowledged",
                distinct_id=user_name,
                properties={
                    "sequence_id": sequence_id_on_display,
                    "classification": "false_positive",
                    "action": "confirmed",
                },
            )
        return modal_hidden_style, sequence_id_on_display

    elif triggered_id == "cancel-confirmation":
        # Cancel action
        if user_name:
            telemetry_client.capture(
                event="acknowledgment_cancelled",
                distinct_id=user_name,
                properties={"sequence_id": sequence_id_on_display},
            )
        return modal_hidden_style, dash.no_update

    raise dash.exceptions.PreventUpdate


# Modal issue let's add this later
@app.callback(
    Output("map-modal", "is_open"),  # Toggle the modal
    Input("map-button", "n_clicks"),
    State("map-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_fullscreen_map(n_clicks_open, is_open):
    """
    Toggles the fullscreen map modal based on button clicks.

    Parameters:
    - n_clicks_open (int): Number of clicks on the map button to toggle modal.
    - is_open (bool): Current state of the map modal.

    Returns:
    - bool: New state of the map modal (open/close).
    """
    logger.info("toggle_fullscreen_map")
    if n_clicks_open:
        return not is_open  # Toggle the modal
    return is_open  # Keep the current state


# Define the callback to reset the zoom level
@app.callback(
    Output("map", "zoom"),
    [
        Input({"type": "event-button", "index": ALL}, "n_clicks"),
    ],
)
def reset_zoom(n_clicks):
    """
    Resets the zoom level of the map when an event button is clicked.

    Parameters:
    - n_clicks (list): List of click counts for each event button.

    Returns:
    - int: Reset zoom level for the map.
    """
    if n_clicks:
        return 10  # Reset zoom level to 10
    return dash.no_update


@app.callback(
    [Output("blinking-image", "src"), Output("blinking-image-container", "style")],
    Input("blinking-alarm-interval", "n_intervals"),
    Input("api_sequences", "data"),
)
def blink_image(n_intervals, api_sequences):
    container_style = {
        "display": "flex",
        "justify-content": "center",  # Center horizontaly
        "align-items": "center",  # Center verticaly
        "height": "100vh",
        "width": "100vw",
    }

    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    if api_sequences.empty:
        image_path = "https://pyronear.org/img/logo_letters_orange.png"
        container_style["background-color"] = "#044448"

    else:
        api_sequences["last_seen_at"] = pd.to_datetime(api_sequences["last_seen_at"], utc=True)

        # Get current UTC time
        now_utc = datetime.now(timezone.utc)

        # Find sequences where last_seen_at is within the last 15 minutes
        recent_sequences = api_sequences[api_sequences["last_seen_at"] > now_utc - timedelta(minutes=30)]

        if recent_sequences.empty:
            image_path = "https://pyronear.org/img/logo_letters_orange.png"
            container_style["background-color"] = "#044448"
        else:
            image_path = "https://pyronear.org/img/logo_letters_orange.png"
            container_style["background-color"] = "red" if n_intervals % 2 == 0 else "#044448"

    return [image_path, container_style]


@app.callback(
    Output("datepicker-modal", "is_open"),
    [Input("open-datepicker-modal", "n_clicks"), Input("close-datepicker-modal", "n_clicks")],
    [State("datepicker-modal", "is_open")],
)
def toggle_datepicker_modal(open_click, close_click, is_open):
    if open_click or close_click:
        return not is_open
    return is_open


@app.callback(
    Output("my-date-picker-single", "min_date_allowed"),
    Output("my-date-picker-single", "max_date_allowed"),
    Output("my-date-picker-single", "initial_visible_month"),
    Output("datepicker_button_text", "children"),
    Input("open-datepicker-modal", "n_clicks"),
    Input("my-date-picker-single", "date"),
    prevent_initial_call=True,
)
def update_datepicker(open_clicks, selected_date):
    ctx = dash.callback_context
    triggered_id = ctx.triggered_id
    today = date.today()
    min_date = today - relativedelta(months=3)

    if triggered_id == "open-datepicker-modal":
        return min_date, today, today, dash.no_update

    if triggered_id == "my-date-picker-single":
        if selected_date:
            return dash.no_update, dash.no_update, dash.no_update, f"{selected_date}"
        else:
            return dash.no_update, dash.no_update, dash.no_update, ""

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update


@app.callback(
    Output("selected-camera-info", "data"),
    Input("start-live-stream", "n_clicks"),
    State("alert-camera-value", "children"),
    State("alert-azimuth-value", "children"),
    prevent_initial_call=True,
)
def pick_live_stream_camera(n_clicks, camera_label, azimuth_label):
    logger.info("pick_live_stream_camera")

    if not camera_label or not azimuth_label:
        raise PreventUpdate
    try:
        cam_name, _, azimuth_camera = camera_label.split(" ")
        azimuth_camera = int(azimuth_camera.replace("°", ""))
        # detection_azimuth = int(azimuth_label.replace("°", "").strip()) Need azimuth refine first
    except Exception as e:
        logger.warning(f"[pick_live_stream_camera] Failed to parse camera info: {e}")
        raise PreventUpdate

    logger.info(f"Selected camera={cam_name}, azimuth={azimuth_camera}")
    return (cam_name, azimuth_camera)


@app.callback(
    Output("bbox-modal", "is_open"),
    Output("bbox-store", "data"),
    Input("create-occlusion-mask", "n_clicks"),
    Input("confirm-bbox-button", "n_clicks"),
    Input("delete-bbox-button", "n_clicks"),
    State("alert-camera-value", "children"),
    State("sequence_on_display", "data"),
    State("bbox-store", "data"),
    prevent_initial_call=True,
)
def handle_modal(create_clicks, confirm_clicks, delete_clicks, camera_info, sequence_on_display, bbox_store):
    triggered = ctx.triggered_id
    user_name = ctx.states.get("user_name.data")

    # Shared S3 client setup
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION"),
        )
        bucket_name = "occlusion-masks-json"
    except Exception as e:
        logger.error(f"Error initializing S3 client: {e}")
        if user_name:
            # Get camera_id from sequence data if available
            camera_id = None
            if sequence_on_display:
                try:
                    df = pd.read_json(StringIO(sequence_on_display), orient="split")
                    if not df.empty:
                        camera_id = df.iloc[0]["camera_id"]
                except Exception:
                    pass

            telemetry_client.capture(
                event="occlusion_mask_error",
                distinct_id=user_name,
                properties={
                    "error_type": "s3_client_init",
                    "error_message": str(e),
                    "camera_name": camera_info.split(" ")[0] if camera_info else None,
                    "camera_id": camera_id,
                    "azimuth": int(camera_info.split(" ")[-1].replace("°", "")) if camera_info else None,
                    "action": "create",
                },
            )
        raise PreventUpdate

    if triggered == "create-occlusion-mask":
        if not camera_info or not sequence_on_display:
            raise PreventUpdate

        cam_name, _, azimuth_camera = camera_info.split(" ")
        azimuth_camera = int(azimuth_camera.replace("°", ""))
        object_key = f"{cam_name}_{azimuth_camera}.json"

        df = pd.read_json(StringIO(sequence_on_display), orient="split")
        camera_id = df.iloc[0]["camera_id"]
        df["bboxes"] = df["bboxes"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() != "[]" else []
        )
        best_bbox = None
        best_score = -1
        for bboxes in df["bboxes"]:
            for bbox in bboxes:
                if bbox[-1] > best_score:
                    best_score = bbox[-1]
                    best_bbox = bbox
        if best_bbox is None:
            if user_name:
                telemetry_client.capture(
                    event="occlusion_mask_error",
                    distinct_id=user_name,
                    properties={
                        "error_type": "no_bbox_found",
                        "error_message": "No bounding box found in sequence",
                        "camera_name": cam_name,
                        "camera_id": camera_id,
                        "azimuth": azimuth_camera,
                        "action": "create",
                    },
                )
            raise PreventUpdate

        # Expand bbox by 10%
        x_min, y_min, x_max, y_max, score = best_bbox
        width = x_max - x_min
        height = y_max - y_min
        expand_x = width * 0.05
        expand_y = height * 0.05
        x_min = max(0, x_min - expand_x)
        y_min = max(0, y_min - expand_y)
        x_max = min(1, x_max + expand_x)
        y_max = min(1, y_max + expand_y)
        best_bbox = [x_min, y_min, x_max, y_max, score]

        # Fetch existing masks from S3
        existing_data = {}
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            existing_data = json.loads(response["Body"].read())
            existing_data = filter_bboxes_dict(existing_data)
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                logger.error(f"head_object error: {e}")
                if user_name:
                    telemetry_client.capture(
                        event="occlusion_mask_error",
                        distinct_id=user_name,
                        properties={
                            "error_type": "s3_fetch",
                            "error_message": str(e),
                            "camera_name": cam_name,
                            "camera_id": camera_id,
                            "azimuth": azimuth_camera,
                            "action": "create",
                        },
                    )
                raise PreventUpdate
        except Exception as e:
            logger.error(f"Error loading S3 object: {e}")
            if user_name:
                telemetry_client.capture(
                    event="occlusion_mask_error",
                    distinct_id=user_name,
                    properties={
                        "error_type": "s3_load",
                        "error_message": str(e),
                        "camera_name": cam_name,
                        "camera_id": camera_id,
                        "azimuth": azimuth_camera,
                        "action": "create",
                    },
                )
            raise PreventUpdate

        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing_data[date_now] = best_bbox

        if user_name:
            telemetry_client.capture(
                event="occlusion_mask_created",
                distinct_id=user_name,
                properties={
                    "camera_name": cam_name,
                    "camera_id": camera_id,
                    "azimuth": azimuth_camera,
                    "action": "create",
                },
            )

        data = {"cam_name": cam_name, "azimuth": azimuth_camera, "bboxes_dict": existing_data}
        return True, data

    elif triggered in {"confirm-bbox-button", "delete-bbox-button"}:
        if not bbox_store:
            raise PreventUpdate

        cam_name = bbox_store["cam_name"]
        azimuth = bbox_store["azimuth"]
        object_key = f"{cam_name}_{azimuth}.json"

        # Get camera_id from sequence data
        camera_id = None
        if sequence_on_display:
            try:
                df = pd.read_json(StringIO(sequence_on_display), orient="split")
                if not df.empty:
                    camera_id = df.iloc[0]["camera_id"]
            except Exception:
                pass

        if triggered == "confirm-bbox-button":
            bboxes_dict = bbox_store.get("bboxes_dict", {})
            action = "saved"
        else:
            # delete-bbox-button
            bboxes_dict = {}
            action = "deleted"

        try:
            json_bytes = json.dumps(bboxes_dict, indent=2).encode("utf-8")
            byte_buffer = BytesIO(json_bytes)
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=byte_buffer,
                ContentType="application/json",
                ContentLength=len(json_bytes),
                ACL="public-read",
            )
            logger.info(f"BBoxes {action} on S3: {object_key}")

            if user_name:
                telemetry_client.capture(
                    event=f"occlusion_mask_{action}",
                    distinct_id=user_name,
                    properties={"camera_name": cam_name, "camera_id": camera_id, "azimuth": azimuth},
                )

            updated_store = {
                "cam_name": cam_name,
                "azimuth": azimuth,
                "bboxes_dict": bboxes_dict,
            }
            return False, updated_store

        except Exception as e:
            logger.error(f"Error writing to S3: {e}")
            if user_name:
                telemetry_client.capture(
                    event="occlusion_mask_error",
                    distinct_id=user_name,
                    properties={
                        "error_type": "s3_write",
                        "error_message": str(e),
                        "camera_name": cam_name,
                        "camera_id": camera_id,
                        "azimuth": azimuth,
                        "action": action,
                    },
                )
            raise PreventUpdate

    raise PreventUpdate


@app.callback(
    Output("bbox-image-container", "children"),
    Input("bbox-store", "data"),
    State("sequence_on_display", "data"),
    prevent_initial_call=True,
)
def display_bbox_on_image(bbox_data, sequence_data):
    if not bbox_data:
        raise PreventUpdate

    try:
        bboxes_dict = bbox_data.get("bboxes_dict")
        if not bboxes_dict:
            raise PreventUpdate

        df = pd.read_json(StringIO(sequence_data), orient="split")
        if df.empty:
            raise PreventUpdate

        img_url = df.iloc[0]["url"]

        # Identifier la bbox la plus récente
        latest_date = max(bboxes_dict.keys())

        rectangles = []
        for creation_date, bbox in bboxes_dict.items():
            x1, y1, x2, y2, _ = bbox
            w = x2 - x1
            h = y2 - y1

            is_latest = creation_date == latest_date
            border_color = "green" if is_latest else "red"
            bg_color = "rgba(0, 255, 0, 0.3)" if is_latest else "rgba(255, 0, 0, 0.3)"

            rectangles.append(
                dash.html.Div(
                    title=creation_date,
                    style={
                        "position": "absolute",
                        "top": f"{y1 * 100}%",
                        "left": f"{x1 * 100}%",
                        "width": f"{w * 100}%",
                        "height": f"{h * 100}%",
                        "border": f"2px solid {border_color}",
                        "background-color": bg_color,
                        "box-sizing": "border-box",
                    },
                )
            )

        return dash.html.Div(
            [
                dash.html.Img(src=img_url, style={"width": "100%", "height": "auto", "display": "block"}),
                *rectangles,
            ],
            style={
                "position": "relative",
                "width": "100%",
                "max-width": "100%",
                "height": "auto",
                "display": "inline-block",
            },
        )

    except Exception as e:
        logger.error(f"[display_bbox_on_image] Error: {e}")
        raise PreventUpdate


@app.callback(
    Output("download-link", "href"),
    [Input("image-slider", "value")],
    [State("sequence_on_display", "data")],
    prevent_initial_call=True,
)
def update_download_link(slider_value, sequence_on_display):
    """
    Updates the download link for the currently displayed image.
    Parameters:
    - slider_value (int): Current value of the image slider.
    - alert_data (json): JSON formatted data for the selected event.
    Returns:
    - str: URL for downloading the current image.
    """
    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")
    if len(sequence_on_display):
        try:
            return sequence_on_display["url"].values[slider_value]
        except Exception as e:
            logger.error(e)
            logger.error(f"Size of the alert_data dataframe: {sequence_on_display.size}")

    return ""  # Return empty string if no image URL is available


@app.callback(
    Output("zip-modal", "is_open"),
    Output("zip-dl-link", "href"),
    Output("zip-dl-link", "download"),
    Input("dl-button", "n_clicks"),
    Input("confirm-dl-button", "n_clicks"),
    State("sequence_on_display", "data"),
    State("api_sequences", "data"),
    State("alert-camera-value", "children"),
    State("alert-start-date-value", "children"),
    prevent_initial_call=True,
)
def prepare_archive_callback(open_clicks, close_clicks, sequence_data, api_sequences, camera_value, date_value):
    triggered_id = ctx.triggered_id

    if triggered_id == "dl-button":
        if not camera_value or not date_value or not sequence_data:
            return dash.no_update

        api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
        sequence_data = pd.read_json(StringIO(sequence_data), orient="split")

        # Format zip base and file name
        folder_name = f"{camera_value}-{date_value}".replace(" ", "_").replace(":", "-").replace("°", "")
        zip_filename = f"{folder_name}.zip"
        prepare_archive(sequence_data, api_sequences, folder_name, camera_value)

        # Track archive download request
        user_name = ctx.states.get("user_name.data")
        if user_name:
            telemetry_client.capture(
                event="archive_download_requested",
                distinct_id=user_name,
                properties={
                    "camera": camera_value,
                    "date": date_value,
                    "archive_name": zip_filename,
                },
            )

        return True, f"/download/{zip_filename}", zip_filename

    elif triggered_id == "confirm-dl-button":
        return False, "", ""

    return dash.no_update
