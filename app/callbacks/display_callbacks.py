# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json
from io import StringIO

import dash
import logging_config
import pandas as pd
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from services import api_client
from utils.display import build_vision_polygon, create_event_list_from_alerts

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


# Create event list
@app.callback(
    Output("sequence-list-container", "children"),
    [
        Input("api_sequences", "data"),
        Input("to_acknowledge", "data"),
    ],
    State("api_cameras", "data"),
)
def update_event_list(api_sequences, to_acknowledge, cameras):
    """
    Updates the event list based on changes in the events data or acknowledgement actions.

    Parameters:
    - api_detections (json): JSON formatted data containing current alerts information.
    - to_acknowledge (int): Event ID that is being acknowledged.

    Returns:
    - html.Div: A Div containing the updated list of alerts.
    """
    logger.info("update_event_list")

    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    cameras = pd.read_json(StringIO(cameras), orient="split")

    if len(api_sequences):
        # Drop acknowledge event for faster update
        api_sequences = api_sequences[~api_sequences["id"].isin([to_acknowledge])]

    return create_event_list_from_alerts(api_sequences, cameras)


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
    ],
    [Input("image-slider", "value"), Input("sequence_on_display", "data")],
    [
        State("sequence-list-container", "children"),
        State("language", "data"),
    ],
    prevent_initial_call=True,
)
def update_image_and_bbox(slider_value, sequence_on_display, sequence_list, lang):
    """
    Updates the image and bounding box display based on the slider value.
    """
    img_src = ""
    no_alert_image_src = "./assets/images/no-alert-default.png"
    if lang == "es":
        no_alert_image_src = "./assets/images/no-alert-default-es.png"

    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")

    if sequence_on_display.empty:
        raise PreventUpdate

    if len(sequence_list) == 0:
        return no_alert_image_src, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, 0

    # Filter images with non-empty URLs
    images, boxes = zip(
        *((alert["url"], alert["processed_bboxes"]) for _, alert in sequence_on_display.iterrows() if alert["url"])
    )

    if not images:
        return no_alert_image_src, {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}, 0

    # Ensure slider_value is within the range of available images
    slider_value = slider_value % len(images)
    img_src = images[slider_value]
    images_bbox_list = boxes[slider_value]

    # Create styles for each bbox (default hidden)
    bbox_styles = [{"display": "none"} for _ in range(4)]

    # Update styles for available bounding boxes
    for i, (x0, y0, width, height) in enumerate(images_bbox_list[:3]):  # Limit to 3 bboxes
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

    return [img_src, *bbox_styles, len(images) - 1]


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
            logger.info(e)
            logger.info(f"Size of the alert_data dataframe: {sequence_on_display.size}")

    return ""  # Return empty string if no image URL is available


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
        Output("alert-date-value", "children"),
        Output("alert-information", "style"),
        Output("slider-container", "style"),
    ],
    Input("sequence_on_display", "data"),
    State("api_cameras", "data"),
    prevent_initial_call=True,
)
def update_map_and_alert_info(sequence_on_display, cameras):
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
    cameras = pd.read_json(StringIO(cameras), orient="split")

    if not sequence_on_display.empty:
        # Convert the 'bboxes' column to a list (empty lists if the original value was '[]').
        sequence_on_display["bboxes"] = sequence_on_display["bboxes"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() != "[]" else []
        )

        # Filter out rows where 'bboxes' is not empty and get the last one.
        # If all are empty, then simply get the last row of the DataFrame.
        row_with_bboxes = (
            sequence_on_display[sequence_on_display["bboxes"].astype(bool)].iloc[-1]
            if not sequence_on_display[sequence_on_display["bboxes"].astype(bool)].empty
            else sequence_on_display.iloc[-1]
        )

        row_cam = cameras[cameras["id"] == row_with_bboxes["camera_id"]]
        lat, lon = row_cam[["lat"]].values.item(), row_cam[["lon"]].values.item()

        polygon, detection_azimuth = build_vision_polygon(
            site_lat=lat,
            site_lon=lon,
            azimuth=row_with_bboxes["azimuth"],
            opening_angle=cfg.CAM_OPENING_ANGLE,
            dist_km=cfg.CAM_RANGE_KM,
            bboxes=row_with_bboxes["processed_bboxes"],
        )

        date_val = row_with_bboxes["created_at"].strftime("%Y-%m-%d %H:%M")
        cam_name = f"{row_cam['name'].values.item()[:-3].replace('_', ' ')} : {int(row_with_bboxes['azimuth'])}°"

        camera_info = f"{cam_name}"
        location_info = f"{lat:.4f}, {lon:.4f}"
        angle_info = f"{detection_azimuth}°"
        date_info = f"{date_val}"

        return (
            polygon,
            [lat, lon],
            polygon,
            [lat, lon],
            camera_info,
            location_info,
            angle_info,
            date_info,
            {"display": "block"},
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
        {"display": "none"},
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

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

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
            return modal_visible_style, dash.no_update

    elif triggered_id == "confirm-wildfire":
        # Send wildfire confirmation to the API
        api_client.token = user_token
        api_client.label_sequence(sequence_id_on_display, True)
        return modal_hidden_style, sequence_id_on_display

    elif triggered_id == "confirm-non-wildfire":
        # Send non-wildfire confirmation to the API
        api_client.token = user_token
        api_client.label_sequence(sequence_id_on_display, False)
        return modal_hidden_style, sequence_id_on_display

    elif triggered_id == "cancel-confirmation":
        # Cancel action
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
