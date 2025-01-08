# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json

import dash
import logging_config
import numpy as np
import pandas as pd
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from services import api_client
from utils.data import read_stored_DataFrame
from utils.display import build_vision_polygon, create_event_list_from_alerts

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


# Create event list
@app.callback(
    Output("alert-list-container", "children"),
    [
        Input("api_detections", "data"),
        Input("to_acknowledge", "data"),
    ],
    State("api_cameras", "data"),
)
def update_event_list(api_detections, to_acknowledge, cameras):
    """
    Updates the event list based on changes in the events data or acknowledgement actions.

    Parameters:
    - api_detections (json): JSON formatted data containing current alerts information.
    - to_acknowledge (int): Event ID that is being acknowledged.

    Returns:
    - html.Div: A Div containing the updated list of alerts.
    """
    logger.info("update_event_list")

    api_detections, event_data_loaded = read_stored_DataFrame(api_detections)
    cameras, _ = read_stored_DataFrame(cameras)

    print("api")
    if not event_data_loaded:
        raise PreventUpdate

    if len(api_detections):
        # Drop acknowledge event for faster update
        api_detections = api_detections[~api_detections["event_id"].isin([to_acknowledge])]

        # Drop event with less than 5 alerts or less then 2 bbox
        drop_event = []
        for event_id in np.unique(api_detections["event_id"].values):
            event_alerts = api_detections[api_detections["event_id"] == event_id]
            if np.sum([len(box) > 2 for box in event_alerts["bboxes"]]) < 2 or len(event_alerts) < 5:
                drop_event.append(event_id)

        api_detections = api_detections[~api_detections["event_id"].isin([drop_event])]

    return create_event_list_from_alerts(api_detections, cameras)


# Select the event id
@app.callback(
    [
        Output({"type": "event-button", "index": ALL}, "style"),
        Output("event_id_on_display", "data"),
        Output("auto-move-button", "n_clicks"),
        Output("custom_js_trigger", "title"),
    ],
    [
        Input({"type": "event-button", "index": ALL}, "n_clicks"),
    ],
    [
        State({"type": "event-button", "index": ALL}, "id"),
        State("api_detections", "data"),
        State("event_id_on_display", "data"),
    ],
    prevent_initial_call=True,
)
def select_event_with_button(n_clicks, button_ids, local_alerts, event_id_on_display):
    """
    Handles event selection through button clicks.

    Parameters:
    - n_clicks (list): List of click counts for each event button.
    - button_ids (list): List of button IDs corresponding to events.
    - local_alerts (json): JSON formatted data containing current alert information.
    - event_id_on_display (int): Currently displayed event ID.

    Returns:
    - list: List of styles for event buttons.
    - int: ID of the event to display.
    - int: Number of clicks for the auto-move button reset.
    """
    logger.info("select_event_with_button")
    ctx = dash.callback_context

    local_alerts, alerts_data_loaded = read_stored_DataFrame(local_alerts)
    if len(local_alerts) == 0:
        return [[], 0, 1, "reset_zoom"]

    if not alerts_data_loaded:
        raise PreventUpdate

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
                    "backgroundColor": "#2C796E",
                    "margin": "10px",
                    "padding": "10px",
                    "borderRadius": "20px",
                    "color": "white",
                    "width": "100%",
                },
            )  # Highlight style
        else:
            styles.append(
                {
                    "backgroundColor": "#FC816B",
                    "margin": "10px",
                    "padding": "10px",
                    "borderRadius": "20px",
                    "width": "100%",
                },
            )  # Default style

    return [styles, button_index, 1, "reset_zoom"]


# Get event_id data
@app.callback(
    Output("alert_on_display", "data"),
    Input("event_id_on_display", "data"),
    State("api_detections", "data"),
    prevent_initial_call=True,
)
def update_display_data(event_id_on_display, local_alerts):
    """
    Updates the display data based on the currently selected event ID.

    Parameters:
    - event_id_on_display (int): Currently displayed event ID.
    - local_alerts (json): JSON formatted data containing current alert information.

    Returns:
    - json: JSON formatted data for the selected event.
    """
    logger.info("update_display_data")
    local_alerts, data_loaded = read_stored_DataFrame(local_alerts)

    if not data_loaded:
        raise PreventUpdate

    if event_id_on_display == 0:
        return json.dumps(
            {
                "data": pd.DataFrame().to_json(orient="split"),
                "data_loaded": True,
            }
        )
    else:
        if event_id_on_display == 0:
            event_id_on_display = local_alerts["event_id"].values[0]

        alert_on_display = local_alerts[local_alerts["event_id"] == event_id_on_display]

        return json.dumps({"data": alert_on_display.to_json(orient="split"), "data_loaded": True})


@app.callback(
    [
        Output("main-image", "src"),  # Output for the image
        Output("bbox-positioning", "style"),
        Output("image-slider", "max"),
    ],
    [Input("image-slider", "value"), Input("alert_on_display", "data")],
    [
        State("alert-list-container", "children"),
        State("language", "data"),
    ],
    prevent_initial_call=True,
)
def update_image_and_bbox(slider_value, alert_data, alert_list, lang):
    """
    Updates the image and bounding box display based on the slider value.

    Parameters:
    - slider_value (int): Current value of the image slider.
    - alert_data (json): JSON formatted data for the selected event.
    - alert_list (list): List of ongoing alerts.

    Returns:
    - html.Img: An image element displaying the selected alert image.
    - list: A list of html.Div elements representing bounding boxes.
    - int: Maximum value for the image slider.
    """
    img_src = ""
    no_alert_image_src = "./assets/images/no-alert-default.png"
    if lang == "es":
        no_alert_image_src = "./assets/images/no-alert-default-es.png"

    bbox_style = {"display": "none"}  # Default style for the bounding box
    alert_data, data_loaded = read_stored_DataFrame(alert_data)

    if not data_loaded:
        raise PreventUpdate

    if len(alert_list) == 0:
        return no_alert_image_src, bbox_style, 0

    # Filter images with non-empty URLs
    images, boxes = zip(
        *(
            (alert["url"], alert["processed_bboxes"])
            for _, alert in alert_data.iterrows()
            if alert["url"]  # Only include if url is not empty
        )
    )

    if not images:
        return no_alert_image_src, bbox_style, 0

    # Ensure slider_value is within the range of available images
    slider_value = slider_value % len(images)
    img_src = images[slider_value]
    images_bbox_list = boxes[slider_value]

    img_src = images[slider_value]
    images_bbox_list = boxes[slider_value]

    if len(images_bbox_list):
        # Calculate the position and size of the bounding box
        x0, y0, width, height = images_bbox_list[0]  # first box for now

        # Create the bounding box style
        bbox_style = {
            "position": "absolute",
            "left": f"{x0}%",  # Left position based on image width
            "top": f"{y0}%",  # Top position based on image height
            "width": f"{width}%",  # Width based on image width
            "height": f"{height}%",  # Height based on image height
            "display": "block",
        }

    return img_src, bbox_style, len(images) - 1


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
        button_style["backgroundColor"] = "#FEBA6A"  # Original button color
    else:
        bbox_style = {"display": "none"}  # Hide the bounding box
        button_style["backgroundColor"] = "#C96A00"  # Darker color for the button

    return bbox_style, button_style


@app.callback(
    Output("auto-move-state", "data"),
    Input("auto-move-button", "n_clicks"),
    State("auto-move-state", "data"),
    prevent_initial_call=True,
)
def toggle_auto_move(n_clicks, data):
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
    else:
        data["active"] = True
    return data


@app.callback(
    Output("image-slider", "value"),
    [Input("auto-slider-update", "n_intervals")],
    [
        State("image-slider", "value"),
        State("image-slider", "max"),
        State("auto-move-button", "n_clicks"),
        State("alert-list-container", "children"),
    ],
    prevent_initial_call=True,
)
def auto_move_slider(n_intervals, current_value, max_value, auto_move_clicks, alert_list):
    """
    Automatically moves the image slider based on a regular interval and the current auto-move state.

    Parameters:
    - n_intervals (int): Number of intervals passed since the start of the auto-move.
    - current_value (int): Current value of the image slider.
    - max_value (int): Maximum value of the image slider.
    - auto_move_clicks (int): Number of clicks on the auto-move button.
    - alert_list (list): List of ongoing alerts.

    Returns:
    - int: Updated value for the image slider.
    """
    if auto_move_clicks % 2 != 0 and len(alert_list):  # Auto-move is active and there is ongoing alerts
        return (current_value + 1) % (max_value + 1)
    else:
        raise PreventUpdate


@app.callback(
    Output("download-link", "href"),
    [Input("image-slider", "value")],
    [State("alert_on_display", "data")],
    prevent_initial_call=True,
)
def update_download_link(slider_value, alert_data):
    """
    Updates the download link for the currently displayed image.

    Parameters:
    - slider_value (int): Current value of the image slider.
    - alert_data (json): JSON formatted data for the selected event.

    Returns:
    - str: URL for downloading the current image.
    """
    alert_data, data_loaded = read_stored_DataFrame(alert_data)
    if data_loaded and len(alert_data):
        try:
            return alert_data["url"].values[slider_value]
        except Exception as e:
            logger.info(e)
            logger.info(f"Size of the alert_data dataframe: {alert_data.size}")

    return ""  # Return empty string if no image URL is available


# Map
@app.callback(
    [
        Output("vision_polygons", "children"),
        Output("map", "center"),
        Output("vision_polygons-md", "children"),
        Output("map-md", "center"),
        Output("alert-camera-value", "children"),
        Output("alert-location-value", "children"),
        Output("alert-azimuth-value", "children"),
        Output("alert-date-value", "children"),
        Output("alert-information", "style"),
        Output("slider-container", "style"),
    ],
    Input("alert_on_display", "data"),
    State("api_cameras", "data"),
    prevent_initial_call=True,
)
def update_map_and_alert_info(alert_data, cameras):
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
    - str: Location information for the alert.
    - str: Detection angle for the alert.
    - str: Date of the alert.
    - dict: Style settings for alert information.
    - dict: Style settings for the slider container.
    """
    logger.info("update_map_and_alert_info")
    alert_data, data_loaded = read_stored_DataFrame(alert_data)
    cameras, _ = read_stored_DataFrame(cameras)

    if not data_loaded:
        raise PreventUpdate

    if not alert_data.empty:
        # Convert the 'bboxes' column to a list (empty lists if the original value was '[]').
        alert_data["bboxes"] = alert_data["bboxes"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() != "[]" else []
        )

        # Filter out rows where 'bboxes' is not empty and get the last one.
        # If all are empty, then simply get the last row of the DataFrame.
        row_with_bboxes = (
            alert_data[alert_data["bboxes"].astype(bool)].iloc[-1]
            if not alert_data[alert_data["bboxes"].astype(bool)].empty
            else alert_data.iloc[-1]
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
    Output("to_acknowledge", "data"),
    [Input("acknowledge-button", "n_clicks")],
    [
        State("event_id_on_display", "data"),
        State("user_token", "data"),
    ],
    prevent_initial_call=True,
)
def acknowledge_event(n_clicks, event_id_on_display, user_token):
    """
    Acknowledges the selected event and updates the state to reflect this.

    Parameters:
    - n_clicks (int): Number of clicks on the acknowledge button.
    - event_id_on_display (int): Currently displayed event ID.
    - user_token (dict): User authorization headers for API requests.

    Returns:
    - int: The ID of the event that has been acknowledged.
    """
    if event_id_on_display == 0 or n_clicks == 0:
        raise PreventUpdate

    if cfg.SAFE_DEV_MODE == "True":
        raise PreventUpdate

    api_client.token = user_token
    # call_api(api_client.acknowledge_event, user_credentials)(event_id=int(event_id_on_display))

    return event_id_on_display


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
