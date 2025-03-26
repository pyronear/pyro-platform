# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from io import StringIO

import dash
import logging_config
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from pages.cameras_status import display_cam_cards
from services import api_client, get_token
from utils.data import load_detections

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
    Output("camera-cards-container", "children"),
    [Input("main_api_fetch_interval", "n_intervals"), Input("api_cameras", "data")],
    State("user_token", "data"),
)
def api_cameras_watcher(n_intervals, api_cameras, user_token):

    logger.info("Get cameras data")
    if user_token is not None:
        api_client.token = user_token

    cameras = pd.DataFrame(api_client.fetch_cameras().json())
    cameras["last_active_at"] = pd.to_datetime(cameras["last_active_at"]).dt.strftime("%Y-%m-%d %H:%M")
    cameras = cameras.sort_values("name")

    return display_cam_cards(cameras)


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
        # Filter alerts before today
        started_at = pd.to_datetime(api_sequences["started_at"])
        today = pd.Timestamp.today().normalize()
        api_sequences = api_sequences[started_at > today]
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
def load_detections_homepage(api_sequences, sequence_id_on_display, api_detections, are_detections_loaded):
    return load_detections(api_sequences, sequence_id_on_display, api_detections, are_detections_loaded)


@app.callback(
    [
        Output("are_detections_loaded_history", "data"),
        Output("sequence_on_display_history", "data"),
        Output("api_detections_history", "data"),
    ],
    [
        Input("api_sequences_history", "data"),
        Input("sequence_id_on_display_history", "data"),
        Input("api_detections_history", "data"),
    ],
    State("are_detections_loaded_history", "data"),
    prevent_initial_call=True,
)
def load_detections_history(api_sequences, sequence_id_on_display, api_detections, are_detections_loaded):
    return load_detections(
        api_sequences, sequence_id_on_display, api_detections, are_detections_loaded, id_suffix="_history"
    )
