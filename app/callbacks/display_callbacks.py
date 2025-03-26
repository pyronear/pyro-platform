# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import urllib
from io import StringIO

import dash
import logging_config
import pandas as pd
from dash.dependencies import ALL, Input, Output, State
from main import app

import config as cfg
from services import api_client
from utils.display import (
    auto_move_slider,
    create_event_list_from_alerts,
    select_event_with_button,
    toggle_auto_move,
    toggle_bbox_visibility,
    update_download_link,
    update_image_and_bbox,
    update_map_and_alert_info,
)

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    [Output("camera_status_button_text", "children"), Output("history_button_text", "children")], Input("url", "search")
)
def update_nav_bar_language(search):

    translate = {
        "fr": {"camera_status": "Statut des Caméras", "history": "Historique"},
        "es": {"camera_status": "Estado de las Cámaras", "history": "Histórico"},
    }

    params = dict(urllib.parse.parse_qsl(search.lstrip("?"))) if search else {}

    lang = params.get("lang", cfg.DEFAULT_LANGUAGE)

    return [[translate[lang]["camera_status"]], [translate[lang]["history"]]]


@app.callback(Output("url", "search"), [Input("btn-fr", "n_clicks"), Input("btn-es", "n_clicks")])
def update_language_url(fr_clicks, es_clicks):
    # Check which button has been clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # update the URL according to the button clicked
    if button_id == "btn-fr":
        return "?lang=fr"
    elif button_id == "btn-es":
        return "?lang=es"

    return ""


# Create history event list
@app.callback(
    [
        Output("api_sequences_history", "data"),
        Output("sequence-list-container-history", "children"),
    ],
    Input("my-date-picker-single", "date"),
    [State("api_cameras", "data"), State("user_token", "data")],
)
def load_history_sequence_list(selected_date, cameras, user_token):
    """
    Fetches and displays the event list for a selected date.

    This callback retrieves historical sequences from the API based on the selected date
    and updates the event list display.

    Parameters:
        selected_date (str): The date selected in the date picker.
        cameras (str): JSON string containing camera data.
        user_token (str): Authentication token for the API.

    Returns:
        list for related callbacks outputs api_sequences_history & sequence-list-container-history
    """
    if selected_date is None:
        return [
            pd.DataFrame().to_json(orient="split"),
            create_event_list_from_alerts(pd.DataFrame(), cameras, "-history"),
        ]

    logger.info("Start Fetching History Sequences")

    api_client.token = user_token

    # Fetch history Sequences
    response = api_client.fetch_sequences_from_date(selected_date)

    response_json = response.json()
    if len(response_json) == 0:
        api_sequences = pd.DataFrame()
    else:
        api_sequences = pd.DataFrame(response_json)

    cameras = pd.read_json(StringIO(cameras), orient="split")

    return [api_sequences.to_json(orient="split"), create_event_list_from_alerts(api_sequences, cameras, "-history")]


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


@app.callback(
    Output("date-picker-is-empty-info", "children"), Input("my-date-picker-single", "date"), State("language", "data")
)
def is_datepicker_empty(date_value, lang):
    if date_value is None:
        return cfg.TRANSLATION["history"][lang]["pick_date_msg"]


# Select the event id
@app.callback(
    [
        Output({"type": "event-button", "index": ALL}, "style"),
        Output("sequence_id_on_display", "data"),
        Output("auto-move-button", "n_clicks"),
        Output("custom_js_trigger", "title", allow_duplicate=True),
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
def select_event_with_button_homepage(n_clicks, button_ids, api_sequences, sequence_id_on_display):

    return select_event_with_button(n_clicks, button_ids, api_sequences, sequence_id_on_display, logger)


# Select the event id
@app.callback(
    [
        Output({"type": "event-button-history", "index": ALL}, "style"),
        Output("sequence_id_on_display_history", "data"),
        Output("auto-move-button-history", "n_clicks"),
        Output("custom_js_trigger", "title", allow_duplicate=True),
    ],
    [
        Input({"type": "event-button-history", "index": ALL}, "n_clicks"),
    ],
    [
        State({"type": "event-button-history", "index": ALL}, "id"),
        State("api_sequences_history", "data"),
        State("sequence_id_on_display_history", "data"),
    ],
    prevent_initial_call=True,
)
def select_event_with_button_history(n_clicks, button_ids, api_sequences, sequence_id_on_display):

    return select_event_with_button(n_clicks, button_ids, api_sequences, sequence_id_on_display, logger)


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
def update_image_and_bbox_homepage(slider_value, sequence_on_display, sequence_list, lang):

    return update_image_and_bbox(slider_value, sequence_on_display, sequence_list, lang)


@app.callback(
    [
        Output("main-image-history", "src"),
        Output("bbox-0-history", "style"),
        Output("bbox-1-history", "style"),
        Output("bbox-2-history", "style"),
        Output("image-slider-history", "max"),
    ],
    [Input("image-slider-history", "value"), Input("sequence_on_display_history", "data")],
    [
        State("sequence-list-container-history", "children"),
        State("language", "data"),
    ],
    prevent_initial_call=True,
)
def update_image_and_bbox_history(slider_value, sequence_on_display, sequence_list, lang):

    return update_image_and_bbox(slider_value, sequence_on_display, sequence_list, lang, id_suffix="_history")


@app.callback(
    [
        Output("bbox-container", "style"),  # Update the style of the bounding box
        Output("hide-bbox-button", "style"),  # Update the style of the button
    ],
    [Input("hide-bbox-button", "n_clicks")],
    [State("hide-bbox-button", "style")],  # Get the current style of the button
    prevent_initial_call=True,
)
def toggle_bbox_visibility_homepage(n_clicks, button_style):

    return toggle_bbox_visibility(n_clicks, button_style, logger)


@app.callback(
    [
        Output("bbox-container-history", "style"),  # Update the style of the bounding box
        Output("hide-bbox-button-history", "style"),  # Update the style of the button
    ],
    [Input("hide-bbox-button-history", "n_clicks")],
    [State("hide-bbox-button-history", "style")],  # Get the current style of the button
    prevent_initial_call=True,
)
def toggle_bbox_visibility_history(n_clicks, button_style):

    return toggle_bbox_visibility(n_clicks, button_style, logger)


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
def toggle_auto_move_homepage(n_clicks, data, button_style):

    return toggle_auto_move(n_clicks, data, button_style, logger)


@app.callback(
    [
        Output("auto-move-state-history", "data"),
        Output("auto-move-button-history", "style"),  # Update the style of the button
    ],
    Input("auto-move-button-history", "n_clicks"),
    State("auto-move-state-history", "data"),
    State("auto-move-button-history", "style"),  # Get the current style of the button
    prevent_initial_call=True,
)
def toggle_auto_move_history(n_clicks, data, button_style):

    return toggle_auto_move(n_clicks, data, button_style, logger)


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
def auto_move_slider_homepage(n_intervals, current_value, max_value, auto_move_clicks, sequence_list):

    return auto_move_slider(n_intervals, current_value, max_value, auto_move_clicks, sequence_list)


@app.callback(
    Output("image-slider-history", "value"),
    [Input("auto-slider-update-history", "n_intervals")],
    [
        State("image-slider-history", "value"),
        State("image-slider-history", "max"),
        State("auto-move-button-history", "n_clicks"),
        State("sequence-list-container-history", "children"),
    ],
    prevent_initial_call=True,
)
def auto_move_slider_history(n_intervals, current_value, max_value, auto_move_clicks, sequence_list):

    return auto_move_slider(n_intervals, current_value, max_value, auto_move_clicks, sequence_list)


@app.callback(
    Output("download-link", "href"),
    [Input("image-slider", "value")],
    [State("sequence_on_display", "data")],
    prevent_initial_call=True,
)
def update_download_link_homepage(slider_value, sequence_on_display):
    return update_download_link(slider_value, sequence_on_display, logger)


@app.callback(
    Output("download-link-history", "href"),
    [Input("image-slider-history", "value")],
    [State("sequence_on_display_history", "data")],
    prevent_initial_call=True,
)
def update_download_link_history(slider_value, sequence_on_display):
    return update_download_link(slider_value, sequence_on_display, logger)


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
def update_map_and_alert_info_homepage(sequence_on_display, cameras):

    return update_map_and_alert_info(sequence_on_display, cameras, logger)


# Map
@app.callback(
    [
        Output("vision_polygons-history", "children"),
        Output("map-history", "center"),
        Output("vision_polygons-md-history", "children"),
        Output("map-md-history", "center"),
        Output("alert-camera-value-history", "children"),
        Output("camera-location-value-history", "children"),
        Output("alert-azimuth-value-history", "children"),
        Output("alert-date-value-history", "children"),
        Output("alert-information-history", "style"),
        Output("slider-container-history", "style"),
    ],
    Input("sequence_on_display_history", "data"),
    State("api_cameras", "data"),
    prevent_initial_call=True,
)
def update_map_and_alert_info_history(sequence_on_display, cameras):

    return update_map_and_alert_info(sequence_on_display, cameras, logger)


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
