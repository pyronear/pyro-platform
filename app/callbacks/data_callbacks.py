# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json
from datetime import datetime, timedelta

import dash
import logging_config
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from main import app

import config as cfg
from services import api_client, get_token
from utils.data import assign_event_ids, process_bbox, read_stored_DataFrame

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
    cameras = pd.DataFrame(api_client.fetch_cameras().json())

    return json.dumps({"data": cameras.to_json(orient="split"), "data_loaded": True})


@app.callback(
    Output("api_detections", "data"),
    [Input("main_api_fetch_interval", "n_intervals"), Input("api_cameras", "data")],
    [
        State("api_detections", "data"),
        State("user_token", "data"),
    ],
    prevent_initial_call=True,
)
def api_watcher(n_intervals, api_cameras, local_detections, user_token):
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

    logger.info("Start Fetching the events")
    # Fetch Detections
    previous_time_event = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d_%H:%M:%S")
    response = api_client.fetch_unlabeled_detections(from_date=previous_time_event, limit=50)
    api_detections = pd.DataFrame(response.json())

    local_detections, _ = read_stored_DataFrame(local_detections)
    if len(api_detections) == 0:
        return json.dumps(
            {
                "data": pd.DataFrame().to_json(orient="split"),
                "data_loaded": True,
            }
        )

    else:
        api_detections["processed_bboxes"] = api_detections["bboxes"].apply(process_bbox)
        api_detections = assign_event_ids(api_detections, time_threshold=30 * 60)
        if not local_detections.empty:
            aligned_api_detections, aligned_local_detections = api_detections["id"].align(local_detections["id"])
            if all(aligned_api_detections == aligned_local_detections):
                return dash.no_update

        return json.dumps({"data": api_detections.to_json(orient="split"), "data_loaded": True})
