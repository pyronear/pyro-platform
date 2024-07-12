# Copyright (C) 2023-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json
from typing import List

import dash
import logging_config
import pandas as pd
from dash import html
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate
from main import app
from pyroclient import Client

import config as cfg
from utils.data import read_stored_DataFrame
from utils.display import build_vision_polygon, create_wildfire_list_from_df

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    Output("modal-loading", "is_open"),
    [Input("media_url", "data"), Input("client_token", "data"), Input("trigger_no_wildfires", "data")],
    State("store_detections_data", "data"),
    prevent_initial_call=True,
)
def toggle_modal(media_url, client_token, trigger_no_wildfires, local_detections):
    """
    Toggles the visibility of the loading modal based on the presence of media URLs and the state of detections data.

    This function is triggered by changes in the media URLs, user headers, or a trigger indicating no wildfires.
    It checks the current state of detections data and decides whether to display the loading modal.

    Parameters:
    - media_url (dict): Dictionary containing media URLs for detections.
    - client_token (str): Token used for API requests
    - trigger_no_wildfires (bool): Trigger indicating whether there are no wildfires to process.
    - local_detections (json): JSON formatted data containing current detections information.

    Returns:
    - bool: True to show the modal, False to hide it. The modal is shown if detections data is not loaded and there are no media URLs; hidden otherwise.
    """
    if trigger_no_wildfires:
        return False
    if client_token is None:
        raise PreventUpdate
    local_detections, detections_data_loaded = read_stored_DataFrame(local_detections)
    return True if not detections_data_loaded and len(media_url.keys()) == 0 else False


# Createwildfire list
@app.callback(
    Output("wildfire-list-container", "children"),
    [
        Input("store_wildfires_data", "data"),
        Input("to_acknowledge", "data"),
    ],
    State("media_url", "data"),
    prevent_initial_call=True,
)
def update_wildfire_list(local_wildfires, to_acknowledge, media_url):
    """
    Updates the wildfire list based on changes in the wildfires data or acknowledgement actions.

    Parameters:
    - local_wildfires (json): JSON formatted data containing current wildfire information.
    - to_acknowledge (int): wildfire ID that is being acknowledged.
    - media_url (dict): Dictionary containing media URLs for detections.

    Returns:
    - html.Div: A Div containing the updated list of detections.
    """
    trigger_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "to_acknowledge" and str(to_acknowledge) not in media_url.keys():
        raise PreventUpdate

    local_wildfires, wildfire_data_loaded = read_stored_DataFrame(local_wildfires)
    if not wildfire_data_loaded:
        raise PreventUpdate

    if len(local_wildfires):
        local_wildfires = local_wildfires[~local_wildfires["id"].isin([to_acknowledge])]

    return create_wildfire_list_from_df(local_wildfires)


# Select the wildfire id
@app.callback(
    [
        Output({"type": "wildfire-button", "index": ALL}, "style"),
        Output("wildfire_id_on_display", "data"),
        Output("auto-move-button", "n_clicks"),
    ],
    [
        Input({"type": "wildfire-button", "index": ALL}, "n_clicks"),
        Input("to_acknowledge", "data"),
    ],
    [
        State("media_url", "data"),
        State({"type": "wildfire-button", "index": ALL}, "id"),
        State("store_detections_data", "data"),
        State("wildfire_id_on_display", "data"),
    ],
    prevent_initial_call=True,
)
def select_wildfire_with_button(
    n_clicks, to_acknowledge, media_url, button_ids, local_detections, wildfire_id_on_display
):
    """
    Handles wildfire selection through button clicks.

    Parameters:
    - n_clicks (list): List of click counts for eachwildfire button.
    - to_acknowledge (int): Wildfire ID that is being acknowledged.
    - media_url (dict): Dictionary containing media URLs for detections.
    - button_ids (list): List of button IDs corresponding to wildfires.
    - local_detections (json): JSON formatted data containing current detection information.
    - wildfire_id_on_display (int): Currently displayed wildfire ID.

    Returns:
    - list: List of styles for wildfire buttons.
    - int: ID of the wildfire to display.
    """
    ctx = dash.callback_context

    local_detections, detections_data_loaded = read_stored_DataFrame(local_detections)
    if len(local_detections) == 0:
        return [[], 0, 1]

    if not detections_data_loaded:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "to_acknowledge":
        idx = local_detections[~local_detections["wildfire_id"].isin([to_acknowledge])]["wildfire_id"].values
        if len(idx) == 0:
            button_index = 0  # No more images available
        else:
            button_index = idx[0]

    else:
        # Extracting the index of the clicked button
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id:
            button_index = json.loads(button_id)["index"]
        else:
            button_index = 0

        nb_clicks = ctx.triggered[0]["value"]  # check if the button was clicked or just initialized (=0)

        if (
            nb_clicks == 0
            and wildfire_id_on_display > 0
            and wildfire_id_on_display in local_detections["wildfire_id"].values
        ):
            button_index = wildfire_id_on_display

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

    return [styles, button_index, 1]


# Get wildfire_id data
@app.callback(
    Output("detection_on_display", "data"),
    Input("wildfire_id_on_display", "data"),
    State("store_detections_data", "data"),
    State("store_wildfires_data", "data"),
    prevent_initial_call=True,
)
def update_display_data(wildfire_id_on_display, local_detections, local_wildfires):
    """
    Updates the display data based on the currently selected wildfire ID.

    Parameters:
    - wildfire_id_on_display (int): Currently displayed wildfire ID.
    - local_detections (json): JSON formatted data containing current detection information.

    Returns:
    - json: JSON formatted data for the selected wildfire.
    """
    local_detections, data_detections_loaded = read_stored_DataFrame(local_detections)
    local_wildfires, data_wildfires_loaded = read_stored_DataFrame(local_wildfires)

    if not data_detections_loaded or not data_wildfires_loaded:
        raise PreventUpdate

    if wildfire_id_on_display == 0:
        return json.dumps(
            {
                "data": pd.DataFrame().to_json(orient="split"),
                "data_loaded": False,
            }
        )
    else:

        detection_ids = local_wildfires[local_wildfires["id"] == wildfire_id_on_display]["detection_ids"].values[0]
        detection_on_display = local_detections[local_detections["id"].isin(detection_ids)]
        return json.dumps({"data": detection_on_display.to_json(orient="split"), "data_loaded": True})


@app.callback(
    [
        Output("image-container", "children"),  # Output for the image
        Output("bbox-container", "children"),  # Output for the bounding box
        Output("image-slider", "max"),
    ],
    [Input("image-slider", "value"), Input("detection_on_display", "data")],
    [
        State("media_url", "data"),
        State("wildfire-list-container", "children"),
    ],
    prevent_initial_call=True,
)
def update_image_and_bbox(slider_value, detection_data, media_url, wildfire_list):
    """
    Updates the image and bounding box display based on the slider value.

    Parameters:
    - slider_value (int): Current value of the image slider.
    - detection_data (json): JSON formatted data for the selected wildfire.
    - media_url (dict): Dictionary containing media URLs for detections.

    Returns:
    - html.Img: An image element displaying the selected detection image.
    - list: A list of html.Div elements representing bounding boxes.
    """
    img_src = ""
    bbox_style = {}
    bbox_divs: List[html.Div] = []  # This will contain the bounding box as an html.Div
    detection_data, data_loaded = read_stored_DataFrame(detection_data)
    if not data_loaded:
        raise PreventUpdate

    if len(wildfire_list) == 0:
        img_html = html.Img(
            src="./assets/images/no-alert-default.png",
            className="common-style",
            style={"width": "100%", "height": "auto"},
        )
        return img_html, bbox_divs, 0

    # Filter images with non-empty URLs
    images = []
    if str(detection_data["id"].values[0]) not in media_url.keys():
        raise PreventUpdate

    for _, detection in detection_data.iterrows():
        images.append(media_url[str(detection["id"])])
    boxes = detection_data["processed_loc"].tolist()

    if slider_value < len(images):
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
                "border": "2px solid red",
                "zIndex": "10",
            }

    # Create a div that represents the bounding box
    bbox_div = html.Div(style=bbox_style)
    bbox_divs.append(bbox_div)

    img_html = html.Img(src=img_src, className="common-style", style={"width": "100%", "height": "auto"})
    return img_html, bbox_divs, len(images) - 1


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
        State("wildfire_id_on_display", "data"),
        State("store_wildfires_data", "data"),
    ],
    prevent_initial_call=True,
)
def auto_move_slider(n_intervals, current_value, max_value, auto_move_clicks, wildfire_id_on_display, local_wildfires):
    """
    Automatically moves the image slider based on a regular interval and the current auto-move state.

    Parameters:
    - n_intervals (int): Number of intervals passed since the start of the auto-move.
    - current_value (int): Current value of the image slider.
    - max_value (int): Maximum value of the image slider.
    - auto_move_clicks (int): Number of clicks on the auto-move button.
    - detection_list(list) : Ongoing detection list

    Returns:
    - int: Updated value for the image slider.
    """
    local_wildfires, data_loaded = read_stored_DataFrame(local_wildfires)
    if data_loaded:
        detection_ids_list = local_wildfires[local_wildfires["id"] == wildfire_id_on_display]["detection_ids"].values[0]
    else:
        detection_ids_list = []

    if auto_move_clicks % 2 != 0 and len(detection_ids_list):  # Auto-move is active and there is ongoing detections
        return (current_value + 1) % (max_value + 1)
    else:
        raise PreventUpdate


@app.callback(
    Output("download-link", "href"),
    [Input("image-slider", "value")],
    [State("wildfire_id_on_display", "data"), State("store_wildfires_data", "data"), State("media_url", "data")],
    prevent_initial_call=True,
)
def update_download_link(slider_value, wildfire_id, wildfires, media_url):
    """
    Updates the download link for the currently displayed image.

    Parameters:
    - slider_value (int): Current value of the image slider.
    - detection_data (json): JSON formatted data for the selected wildfire.
    - media_url (dict): Dictionary containing media URLs for detections.

    Returns:
    - str: URL for downloading the current image.
    """
    wildfires_df, data_loaded = read_stored_DataFrame(wildfires)
    detection_ids_list = wildfires_df.loc[wildfires_df["id"] == wildfire_id, "detection_ids"].tolist()[0]
    if data_loaded and len(detection_ids_list):
        try:
            detection_id = detection_ids_list[slider_value]
            if str(detection_id) in media_url.keys():
                return media_url[str(detection_id)]
        except Exception as e:
            logger.info(e)
            logger.info(f"Size of the detections list: {len(detection_ids_list)}")
    return ""  # Return empty string if no image URL is available


# Map
@app.callback(
    [
        Output("vision_polygons", "children"),
        Output("map", "center"),
        Output("vision_polygons-md", "children"),
        Output("map-md", "center"),
        Output("alert-camera", "children"),
        Output("alert-location", "children"),
        Output("alert-azimuth", "children"),
        Output("alert-date", "children"),
        Output("alert-information", "style"),
        Output("slider-container", "style"),
    ],
    Input("detection_on_display", "data"),
    [State("store_wildfires_data", "data"), State("wildfire_id_on_display", "data")],
    prevent_initial_call=True,
)
def update_map_and_alert_info(detection_data, local_wildfires, wildfire_id_on_display):
    """
        Updates the map's vision polygons, center, and alert information based on the current alert data.
    )
    Parameters:
        - detection_data (json): JSON formatted data for the selecte dwildfire.

    Returns:
        - list: List of vision polygon elements to be displayed on the map.
        - list: New center coordinates for the map.
        - list: List of vision polygon elements to be displayed on the modal map.
        - list: New center coordinates for the modal map.
        - str: Camera information for the alert.
        - str: Location information for the alert.
        - str: Detection angle for the alert.
        - str: Date of the alert.
    """
    detection_data, data_loaded = read_stored_DataFrame(detection_data)

    if not data_loaded:
        raise PreventUpdate

    if not detection_data.empty:
        local_wildfires, wildfire_data_loaded = read_stored_DataFrame(local_wildfires)
        if not wildfire_data_loaded:
            raise PreventUpdate

        # Convert the 'localization' column to a list (empty lists if the original value was '[]').
        detection_data["localization"] = detection_data["localization"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() != "[]" else []
        )  # WHY?

        # Filter out rows where 'localization' is not empty and get the last one.
        # If all are empty, then simply get the last row of the DataFrame.
        row_with_localization = (
            detection_data[detection_data["localization"].astype(bool)].iloc[-1]
            if not detection_data[detection_data["localization"].astype(bool)].empty
            else detection_data.iloc[-1]
        )

        polygon, detection_azimuth = build_vision_polygon(
            site_lat=row_with_localization["lat"],
            site_lon=row_with_localization["lon"],
            azimuth=row_with_localization["azimuth"],
            opening_angle=cfg.CAM_OPENING_ANGLE,
            dist_km=cfg.CAM_RANGE_KM,
            localization=row_with_localization["processed_loc"],
        )

        date_val, cam_name = local_wildfires[local_wildfires["id"] == wildfire_id_on_display][
            ["created_at", "camera_name"]
        ].values[0]

        camera_info = f"Camera: {cam_name}"
        location_info = f"Localisation: {row_with_localization['lat']:.4f}, {row_with_localization['lon']:.4f}"
        angle_info = f"Azimuth de detection: {detection_azimuth}°"
        date_info = f"Date: {date_val}"

        return (
            polygon,
            [row_with_localization["lat"], row_with_localization["lon"]],
            polygon,
            [row_with_localization["lat"], row_with_localization["lon"]],
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
        State("store_wildfires_data", "data"),
        State("wildfire_id_on_display", "data"),
        State("client_token", "data"),
    ],
    prevent_initial_call=True,
)
def acknowledge_wildfire(n_clicks, local_wildfires, wildfire_id_on_display, client_token):
    """
    Acknowledges the selected wildfire and updates the state to reflect this.

    Parameters:
    - n_clicks (int): Number of clicks on the acknowledge button.
    -wildfire_id_on_display (int): Currently displayedwildfire ID.
    - client_token (str): Token used for API requests.

    Returns:
    - int: The ID of the wildfire that has been acknowledged.
    """
    if wildfire_id_on_display == 0 or n_clicks == 0:
        raise PreventUpdate
    local_wildfires, _ = read_stored_DataFrame(local_wildfires)
    wildfire_id = int(wildfire_id_on_display)
    detection_ids = local_wildfires[local_wildfires["id"] == wildfire_id][["detection_ids"]].values
    for detection_id in detection_ids:
        Client(client_token, cfg.API_URL).label_detection(detection_id=detection_id, is_wildfire=False)

    return wildfire_id_on_display


# Modal issue let's add this later
@app.callback(
    Output("map-modal", "is_open"),  # Toggle the modal
    Input("map-button", "n_clicks"),
    State("map-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_fullscreen_map(n_clicks_open, is_open):
    if n_clicks_open:
        return not is_open  # Toggle the modal
    return is_open  # Keep the current state


# Define the callback to reset the zoom level
@app.callback(
    Output("map", "zoom"),
    [
        Input({"type": "wildfire-button", "index": ALL}, "n_clicks"),
    ],
)
def reset_zoom(n_clicks):
    if n_clicks:
        return 10  # Reset zoom level to 10
    return dash.no_update
