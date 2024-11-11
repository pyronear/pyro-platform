# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json

import dash
import logging_config
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from main import app
from pyroclient import Client

import config as cfg
from services import api_client, call_api
from utils.data import (
    convert_time,
    past_ndays_api_events,
    process_bbox,
    read_stored_DataFrame,
)

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    [
        Output("user_credentials", "data"),
        Output("user_headers", "data"),
        Output("form_feedback_area", "children"),
        Output("username_input", "style"),
        Output("password_input", "style"),
        Output("send_form_button", "style"),
        Output("form_feedback_area", "style"),
        Output("loading_spinner", "style"),
    ],
    [
        Input("language", "data"),
        Input("send_form_button", "n_clicks"),
    ],
    [
        State("username_input", "value"),
        State("password_input", "value"),
        State("user_headers", "data"),
    ],
)
def login_callback(lang, n_clicks, username, password, user_headers):
    """
    Callback to handle user login.

    Parameters:
        n_clicks (int): Number of times the login button has been clicked.
        username (str or None): The value entered in the username input field.
        password (str or None): The value entered in the password input field.
        user_headers (dict or None): Existing user headers, if any, containing authentication details.

    This function is triggered when the login button is clicked. It verifies the provided username and password,
    attempts to authenticate the user via the API, and updates the user credentials and headers.
    If authentication fails or credentials are missing, it provides appropriate feedback.
    After login succeeds and while data required to boot the dashboard is being fetched from the API,
    the login form is hidden and a spinner is displayed.

    Returns:
        dash.dependencies.Output: Updated user credentials and headers, and form feedback + styles to hide/show login elements and loading spinners.
    """
    print("login_callback")
    print(lang)

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

    if user_headers is not None:
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
        form_feedback = [dcc.Markdown("---")]
        # First check verifies whether both a username and a password have been provided
        if username is None or password is None or len(username) == 0 or len(password) == 0:
            # If either the username or the password is missing, the condition is verified

            # We add the appropriate feedback
            form_feedback.append(html.P(translate[lang]["missing_password_or_user_name"]))

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
                client = Client(cfg.API_URL, username, password)

                return (
                    {"username": username, "password": password},
                    client.headers,
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
    [
        Output("store_api_alerts_data", "data"),
    ],
    [Input("main_api_fetch_interval", "n_intervals"), Input("user_credentials", "data")],
    [
        State("store_api_alerts_data", "data"),
        State("user_headers", "data"),
    ],
    prevent_initial_call=True,
)
def api_watcher(n_intervals, user_credentials, local_alerts, user_headers):
    """
    Callback to periodically fetch alerts data from the API.

    Parameters:
        n_intervals (int): Number of times the interval has been triggered.
        user_credentials (dict or None): Current user credentials for API authentication.
        local_alerts (dict or None): Locally stored alerts data, serialized as JSON.
        user_headers (dict or None): Current user headers containing authentication details.

    This function is triggered at specified intervals and when user credentials are updated.
    It retrieves unacknowledged events from the API, processes the data, and stores it locally.
    If the local data matches the API data, no updates are made.

    Returns:
        dash.dependencies.Output: Serialized JSON data of alerts and a flag indicating if data is loaded.
    """
    if user_headers is None:
        raise PreventUpdate
    user_token = user_headers["Authorization"].split(" ")[1]
    api_client.token = user_token

    # Read local data
    local_alerts, alerts_data_loaded = read_stored_DataFrame(local_alerts)
    logger.info("Start Fetching the events")

    # Fetch events
    api_alerts = pd.DataFrame(call_api(api_client.get_unacknowledged_events, user_credentials)())
    api_alerts["created_at"] = convert_time(api_alerts)
    api_alerts = past_ndays_api_events(api_alerts, n_days=0)

    if len(api_alerts) == 0:
        return [
            json.dumps(
                {
                    "data": pd.DataFrame().to_json(orient="split"),
                    "data_loaded": True,
                }
            )
        ]

    else:
        api_alerts["processed_loc"] = api_alerts["localization"].apply(process_bbox)
        if alerts_data_loaded and not local_alerts.empty:
            aligned_api_alerts, aligned_local_alerts = api_alerts["alert_id"].align(local_alerts["alert_id"])
            if all(aligned_api_alerts == aligned_local_alerts):
                return [dash.no_update]

        return [json.dumps({"data": api_alerts.to_json(orient="split"), "data_loaded": True})]
