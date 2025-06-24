# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json
from io import StringIO

import dash
import logging_config
import pandas as pd
from dash import callback_context, dcc, html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from main import app
from translations import translate

import config as cfg
from pages.cameras_status import display_cam_cards
from services import get_client, get_token
from utils.data import compute_overlap, process_bbox, sequences_have_changed

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    [
        Output("user_token", "data"),
        Output("user_name", "data"),
        Output("form_feedback_area", "children"),
        Output("username_input", "style"),
        Output("password_input", "style"),
        Output("send_form_button", "style"),
        Output("form_feedback_area", "style"),
        Output("loading_spinner", "style"),
    ],
    Input("send_form_button", "n_clicks"),
    [
        State("username_input", "value"),
        State("password_input", "value"),
        State("user_token", "data"),
        State("language", "data"),
    ],
)
def login_callback(n_clicks, username, password, user_token, lang):
    """
    Callback to handle user login.

    Parameters:
        n_clicks (int): Number of times the login button has been clicked.
        username (str or None): The value entered in the username input field.
        password (str or None): The value entered in the password input field.
        user_token (dict or None): Existing user headers, if any, containing authentication details.

    This function is triggered when the login button is clicked. It verifies the provided username and password,
    attempts to authenticate the user via the API, and updates the user credentials and headers.
    If authentication fails or credentials are missing, it provides appropriate feedback.
    After login succeeds and while data required to boot the dashboard is being fetched from the API,
    the login form is hidden and a spinner is displayed.

    Returns:
        dash.dependencies.Output: Updated user credentials and headers, and form feedback + styles to hide/show login elements and loading spinners.
    """
    input_style_unchanged = {"width": "250px"}
    empty_style_unchanged = {"": ""}
    hide_element_style = {"display": "none"}
    show_spinner_style = {"transform": "scale(4)"}

    if user_token is not None:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            input_style_unchanged,
            input_style_unchanged,
            empty_style_unchanged,
            empty_style_unchanged,
            hide_element_style,
        )

    if n_clicks:
        # We instantiate the form feedback output
        form_feedback: list[Component] = [dcc.Markdown("---")]
        # First check verifies whether both a username and a password have been provided
        if username is None or password is None or len(username) == 0 or len(password) == 0:
            # If either the username or the password is missing, the condition is verified

            # We add the appropriate feedback
            form_feedback.append(html.P(translate("missing_password_or_user_name", lang)))

            # The login modal remains open; other outputs are updated with arbitrary values
            return (
                dash.no_update,
                dash.no_update,
                form_feedback,
                input_style_unchanged,
                input_style_unchanged,
                empty_style_unchanged,
                empty_style_unchanged,
                hide_element_style,
            )
        else:
            # This is the route of the API that we are going to use for the credential check
            try:
                user_token = get_token(username, password)

                return (
                    user_token,
                    username,
                    dash.no_update,
                    hide_element_style,
                    hide_element_style,
                    hide_element_style,
                    hide_element_style,
                    show_spinner_style,
                )
            except Exception:
                # This if statement is verified if credentials are invalid
                form_feedback.append(html.P(translate("wrong_credentials", lang)))

                return (
                    dash.no_update,
                    dash.no_update,
                    form_feedback,
                    input_style_unchanged,
                    input_style_unchanged,
                    empty_style_unchanged,
                    empty_style_unchanged,
                    hide_element_style,
                )

    raise PreventUpdate


@app.callback(
    Output("available-stream-sites", "data"),
    Input("user_name", "data"),
)
def load_available_stream(user_name):
    if not user_name:
        raise PreventUpdate

    try:
        with open("available_stream.json", "r") as f:
            full_data = json.load(f)
    except (FileNotFoundError, IsADirectoryError, json.JSONDecodeError):
        logger.warning("available_stream.json not found or invalid. Using empty dict.")
        full_data = {}

    user_streams = full_data.get(user_name)
    if not user_streams:
        logger.info(f"No stream config found for user '{user_name}'")
        raise PreventUpdate

    return user_streams


@app.callback(
    Output("api_cameras", "data"),
    Input("user_token", "data"),
    prevent_initial_call=True,
)
def get_cameras(user_token):
    logger.info("Get cameras data")
    if user_token is None:
        return dash.no_update
    else:
        client = get_client(user_token)
        cameras = pd.DataFrame(client.fetch_cameras().json())

        return cameras.to_json(orient="split")


@app.callback(
    Output("camera-cards-container", "children"),
    [Input("main_api_fetch_interval", "n_intervals"), Input("api_cameras", "data")],
    State("user_token", "data"),
)
def api_cameras_watcher(n_intervals, api_cameras, user_token):
    logger.info("Get cameras data")
    if user_token is None:
        raise PreventUpdate

    client = get_client(user_token)
    cameras = pd.DataFrame(client.fetch_cameras().json())
    cameras["last_active_at"] = pd.to_datetime(cameras["last_active_at"]).dt.strftime("%Y-%m-%d %H:%M")
    cameras = cameras.sort_values("name")

    return display_cam_cards(cameras)


@app.callback(
    Output("api_sequences", "data"),
    [
        Input("main_api_fetch_interval", "n_intervals"),
        Input("api_cameras", "data"),
        Input("my-date-picker-single", "date"),  # NEW: date picker input
        Input("to_acknowledge", "data"),
    ],
    [
        State("api_sequences", "data"),
        State("user_token", "data"),
    ],
    prevent_initial_call=True,
)
def api_watcher(n_intervals, api_cameras, selected_date, to_acknowledge, local_sequences, user_token):
    """
    Callback to periodically fetch alerts data from the API or after date change.

    Parameters:
        n_intervals (int): Interval trigger.
        api_cameras (dict): Camera data.
        selected_date (str): Selected date from DatePicker.
        local_sequences (str): Cached sequences in JSON format.
        user_token (dict): Auth headers.

    Returns:
        JSON string of filtered sequence data.
    """
    if user_token is None:
        raise PreventUpdate

    logger.info("Start Fetching Sequences")
    print("New SEqqqqqqqqqqqqqqqqqqqqjbpbpijbpibpijbpbpibpbqqqqqqq")

    client = get_client(user_token)

    try:
        if selected_date:
            response = client.fetch_sequences_from_date(selected_date, limit=100)
        else:
            response = client.fetch_latest_sequences()

        api_sequences = pd.DataFrame(response.json())

        if not api_sequences.empty:
            started_at = pd.to_datetime(api_sequences["started_at"])
            if not selected_date:
                today = pd.Timestamp.today().normalize()
                api_sequences = api_sequences[started_at > today]

            api_cameras = pd.read_json(StringIO(api_cameras), orient="split")

            api_sequences = api_sequences.merge(
                api_cameras[["id", "name", "angle_of_view", "lat", "lon"]].rename(columns={"id": "camera_id"}),
                on="camera_id",
                how="left",
            )

            api_sequences["site_name"] = api_sequences["name"].str.replace(r"-\d{2}$", "", regex=True)

            api_sequences = compute_overlap(api_sequences)

        # Load local sequences safely
        if local_sequences:
            local_sequences_df = pd.read_json(StringIO(local_sequences), orient="split")
        else:
            local_sequences_df = pd.DataFrame()

        # Skip update if nothing changed
        if not local_sequences_df.empty and not api_sequences.empty:
            if not sequences_have_changed(api_sequences, local_sequences_df):
                logger.info("Skipping update: no significant change detected")
                return dash.no_update

        return api_sequences.to_json(orient="split")

    except Exception as e:
        logger.error(f"Failed to fetch sequences: {e}")
        return pd.DataFrame().to_json(orient="split")


@app.callback(
    [Output("are_detections_loaded", "data"), Output("sequence_on_display", "data"), Output("api_detections", "data")],
    [Input("api_sequences", "data"), Input("sequence_id_on_display", "data"), Input("api_detections", "data")],
    [State("are_detections_loaded", "data"), State("user_token", "data")],
    prevent_initial_call=True,
)
def load_detections(api_sequences, sequence_id_on_display, api_detections, are_detections_loaded, user_token):
    # Deserialize data

    if user_token is None:
        raise PreventUpdate

    print("sequence_id_on_display", sequence_id_on_display)

    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    if api_sequences.empty:
        return dash.no_update, dash.no_update, dash.no_update

    sequence_id_on_display = str(sequence_id_on_display)
    are_detections_loaded = json.loads(are_detections_loaded)
    api_detections = json.loads(api_detections)

    # Initialize sequence_on_display
    sequence_on_display = pd.DataFrame().to_json(orient="split")

    # Identify which input triggered the callback
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_input = ctx.triggered[0]["prop_id"].split(".")[0]

    client = get_client(user_token)

    if triggered_input == "sequence_id_on_display":
        # If the displayed sequence changes, load its detections if not already loaded
        if sequence_id_on_display not in api_detections:
            response = client.fetch_sequences_detections(sequence_id_on_display)
            data = response.json()
            if isinstance(data, list):
                detections = pd.DataFrame(data)
            else:
                detections = pd.DataFrame()
                logger.error("Error Reading detection")

            if not detections.empty and "bboxes" in detections.columns:
                detections = detections.iloc[::-1].reset_index(drop=True)
                detections["processed_bboxes"] = detections["bboxes"].apply(process_bbox)
            api_detections[sequence_id_on_display] = detections.to_json(orient="split")

        sequence_on_display = api_detections[sequence_id_on_display]
        filtered = api_sequences.loc[api_sequences["id"].astype("str") == sequence_id_on_display, "last_seen_at"]

        if filtered.empty:
            return dash.no_update  # or some fallback value / error handling

        last_seen_at = filtered.iloc[0]

        # Ensure last_seen_at is stored as a string
        are_detections_loaded[sequence_id_on_display] = str(last_seen_at)

    else:
        # If no specific sequence is triggered, load detections for the first missing sequence
        for _, row in api_sequences.iterrows():
            sequence_id = str(row["id"])
            last_seen_at = row["last_seen_at"]

            if sequence_id not in are_detections_loaded or are_detections_loaded[sequence_id] != str(last_seen_at):
                response = client.fetch_sequences_detections(sequence_id)
                data = response.json()
                if isinstance(data, list):
                    detections = pd.DataFrame(data)
                else:
                    detections = pd.DataFrame()
                    logger.error("Error Reading detection")

                if not detections.empty and "bboxes" in detections.columns:
                    detections = detections.iloc[::-1].reset_index(drop=True)
                    detections["processed_bboxes"] = detections["bboxes"].apply(process_bbox)
                api_detections[sequence_id] = detections.to_json(orient="split")
                are_detections_loaded[sequence_id] = str(last_seen_at)
                break

        # Clean up old sequences that are no longer in api_sequences
        sequences_in_api = api_sequences["id"].astype("str").values
        to_drop = [key for key in are_detections_loaded if key not in sequences_in_api]
        for key in to_drop:
            are_detections_loaded.pop(key, None)

    # Serialize and return data
    return json.dumps(are_detections_loaded), sequence_on_display, json.dumps(api_detections)
