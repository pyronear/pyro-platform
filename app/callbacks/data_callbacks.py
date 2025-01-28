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
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from services import api_client, get_token
from utils.data import process_bbox

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    [
        Output("user_token", "data"),
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

    translate = {
        "fr": {
            "missing_password_or_user_name": "Il semble qu'il manque votre nom d'utilisateur et/ou votre mot de passe.",
            "wrong_credentials": "Nom d'utilisateur et/ou mot de passe erroné.",
        },
        "es": {
            "missing_password_or_user_name": "Parece que falta su nombre de usuario y/o su contraseña.",
            "wrong_credentials": "Nombre de usuario y/o contraseña incorrectos.",
        },
    }

    if user_token is not None:
        return (
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
        form_feedback = [dcc.Markdown("---")]
        # First check verifies whether both a username and a password have been provided
        if username is None or password is None or len(username) == 0 or len(password) == 0:
            # If either the username or the password is missing, the condition is verified

            # We add the appropriate feedback
            form_feedback.append(html.P(translate[lang]["missing_password_or_user_name"]))

            # The login modal remains open; other outputs are updated with arbitrary values
            return (
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
                    dash.no_update,
                    hide_element_style,
                    hide_element_style,
                    hide_element_style,
                    hide_element_style,
                    show_spinner_style,
                )
            except Exception:
                # This if statement is verified if credentials are invalid
                form_feedback.append(html.P(translate[lang]["wrong_credentials"]))

                return (
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
    Output("api_cameras", "data"),
    Input("user_token", "data"),
    prevent_initial_call=True,
)
def get_cameras(user_token):
    logger.info("Get cameras data")
    if user_token is not None:
        api_client.token = user_token
    cameras = pd.DataFrame(api_client.fetch_cameras().json())

    return cameras.to_json(orient="split")


@app.callback(
    Output("api_sequences", "data"),
    [Input("main_api_fetch_interval", "n_intervals"), Input("api_cameras", "data")],
    [
        State("api_sequences", "data"),
        State("user_token", "data"),
    ],
    prevent_initial_call=True,
)
def api_watcher(n_intervals, api_cameras, local_sequences, user_token):
    """
    Callback to periodically fetch alerts data from the API.

    Parameters:
        n_intervals (int): Number of times the interval has been triggered.
        local_alerts (dict or None): Locally stored alerts data, serialized as JSON.
        user_token (dict or None): Current user headers containing authentication details.

    This function is triggered at specified intervals and when user credentials are updated.
    It retrieves unacknowledged events from the API, processes the data, and stores it locally.
    If the local data matches the API data, no updates are made.

    Returns:
        dash.dependencies.Output: Serialized JSON data of alerts and a flag indicating if data is loaded.
    """
    if user_token is None:
        raise PreventUpdate

    logger.info("Start Fetching Sequences")
    # Fetch Sequences
    response = api_client.fetch_latest_sequences()
    api_sequences = pd.DataFrame(response.json())

    local_sequences = pd.read_json(StringIO(local_sequences), orient="split")
    if len(api_sequences) == 0:
        return pd.DataFrame().to_json(orient="split")

    else:
        if not local_sequences.empty:
            aligned_api_sequences, aligned_local_sequences = api_sequences["id"].align(local_sequences["id"])
            if all(aligned_api_sequences == aligned_local_sequences):
                return dash.no_update

        return api_sequences.to_json(orient="split")


@app.callback(
    [Output("are_detections_loaded", "data"), Output("sequence_on_display", "data"), Output("api_detections", "data")],
    [Input("api_sequences", "data"), Input("sequence_id_on_display", "data"), Input("api_detections", "data")],
    State("are_detections_loaded", "data"),
    prevent_initial_call=True,
)
def load_detections(api_sequences, sequence_id_on_display, api_detections, are_detections_loaded):
    # Deserialize data
    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
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

    if triggered_input == "sequence_id_on_display":
        # If the displayed sequence changes, load its detections if not already loaded
        if sequence_id_on_display not in api_detections:
            response = api_client.fetch_sequences_detections(sequence_id_on_display)
            detections = pd.DataFrame(response.json())
            detections["processed_bboxes"] = detections["bboxes"].apply(process_bbox)
            api_detections[sequence_id_on_display] = detections.to_json(orient="split")

        sequence_on_display = api_detections[sequence_id_on_display]
        last_seen_at = api_sequences.loc[
            api_sequences["id"].astype("str") == sequence_id_on_display, "last_seen_at"
        ].iloc[0]

        # Ensure last_seen_at is stored as a string
        are_detections_loaded[sequence_id_on_display] = str(last_seen_at)

    else:
        # If no specific sequence is triggered, load detections for the first missing sequence
        for _, row in api_sequences.iterrows():
            sequence_id = str(row["id"])
            last_seen_at = row["last_seen_at"]

            if sequence_id not in are_detections_loaded or are_detections_loaded[sequence_id] != str(last_seen_at):
                response = api_client.fetch_sequences_detections(sequence_id)
                detections = pd.DataFrame(response.json())
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
