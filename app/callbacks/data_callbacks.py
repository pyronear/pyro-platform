# Copyright (C) 2020-2024, Pyronear.

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
from pyroclient import Client

import config as cfg
from services import instantiate_token
from utils.data import process_bbox

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    [
        Output("client_token", "data"),
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
        State("user_headers", "data"),
        State("language", "data"),
    ],
)
def login_callback(n_clicks, username, password, client_token, lang):
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

    if client_token is not None:
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
                client = instantiate_token(username, password)

                return (
                    client.token,
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
        Output("store_wildfires_data", "data"),
        Output("store_detections_data", "data"),
        Output("media_url", "data"),
        Output("trigger_no_wildfires", "data"),
        Output("previous_time_event", "data"),
    ],
    [Input("main_api_fetch_interval", "n_intervals")],
    [
        State("client_token", "data"),
        State("media_url", "data"),
        State("store_wildfires_data", "data"),
        State("previous_time_event", "data"),
    ],
    prevent_initial_call=True,
)
def data_transform(n_intervals, client_token, media_url, store_wildfires_data, previous_time_event):
    """
    Fetches and processes live wildfire and detection data from the API at regular intervals.

    This callback periodically checks for new wildfire and detection data from the API.
    It processes the new data, updates local storage with the latest information,
    and prepares it for displaying in the application.

    Parameters:
    - n_intervals (int): Number of intervals passed since the start of the app,
                         used to trigger the periodic update.
    - client_token (str): Client token for API calls


    Returns:
    - json: Updated wildfires data in JSON format.
    - json: Updated detections data in JSON format.
    """
    if client_token is None:
        raise PreventUpdate

    logger.info("Start Fetching the events")
    # Fetch Detections
    # Use the last event time or default to yesterday
    if previous_time_event is None:
        previous_time_event = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d_%H:%M:%S")
    else:
        previous_time_event = pd.to_datetime(previous_time_event).strftime("%Y-%m-%d_%H:%M:%S")

    api_client = Client(client_token, cfg.API_URL)
    response = api_client.fetch_unlabeled_detections(from_date=previous_time_event)
    api_detections = pd.DataFrame(response.json())
    previous_time_event = api_detections["created_at"].max()
    if api_detections.empty:
        return [
            json.dumps(
                {
                    "data": store_wildfires_data,
                    "data_loaded": False,
                }
            ),
            json.dumps(
                {
                    "data": pd.DataFrame().to_json(orient="split"),
                    "data_loaded": False,
                }
            ),
            [],
            True,
            previous_time_event,
        ]

    # Find ongoing detections for the wildfires started within 30 minutes;
    # after that, any new detection is part of a new wildfire
    api_detections["created_at"] = pd.to_datetime(api_detections["created_at"])

    # Trier les détections par "created_at"
    api_detections = api_detections.sort_values(by="created_at")

    # Initialiser la liste pour les wildfires
    cameras = pd.DataFrame(api_client.fetch_cameras().json())
    api_detections["lat"] = None
    api_detections["lon"] = None
    api_detections["wildfire_id"] = None
    api_detections["processed_loc"] = None
    api_detections["processed_loc"] = api_detections["bboxes"].apply(process_bbox)

    wildfires_dict = json.loads(store_wildfires_data)["data"]
    # Load existing wildfires data
    if wildfires_dict != {}:
        id_counter = (
            max(wildfire["id"] for camera_wildfires in wildfires_dict.values() for wildfire in camera_wildfires) + 1
        )
    else:
        wildfires_dict = {}
        id_counter = 1

    last_detection_time_per_camera: dict[int, str] = {}
    media_dict = api_detections.set_index("id")["url"].to_dict()

    # Parcourir les détections pour les regrouper en wildfires
    for i, detection in api_detections.iterrows():
        camera_id = api_detections.at[i, "camera_id"]
        camera = cameras.loc[cameras["id"] == camera_id]
        camera = camera.iloc[0]  # Ensure camera is a Series
        api_detections.at[i, "lat"] = camera["lat"]
        api_detections.at[i, "lon"] = camera["lon"]

        media_url[detection["id"]] = media_dict[detection["id"]]

        if camera_id not in wildfires_dict:
            wildfires_dict.setdefault(camera_id, [])
            last_detection_time_per_camera.setdefault(camera_id, "")
            # Initialize the first wildfire for this camera
            wildfire = {
                "id": id_counter,
                "camera_name": camera["name"],
                "created_at": detection["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "detection_ids": [detection["id"]],
            }
            wildfires_dict[camera_id] = [wildfire]
            id_counter += 1
        else:
            time_diff = detection["created_at"] - last_detection_time_per_camera[camera_id]

            if time_diff <= pd.Timedelta(minutes=30):
                # Si la différence de temps est inférieure à 30 minutes, ajouter à l'actuel wildfire
                wildfires_dict[camera_id][-1]["detection_ids"].append(detection["id"])
            else:
                # Initialize a new wildfire for this camera
                wildfire = {
                    "id": id_counter,
                    "camera_name": camera["name"],
                    "created_at": detection["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    "detection_ids": [detection["id"]],
                }
                wildfires_dict[camera_id].append(wildfire)
                id_counter += 1
        api_detections.at[i, "wildfire_id"] = wildfires_dict[camera_id][-1]["id"]
        last_detection_time_per_camera[camera_id] = detection["created_at"]

    wildfires_dict = {int(k): v for k, v in wildfires_dict.items()}
    # Convertir la liste des wildfires en DataFrame
    return [
        json.dumps({"data": wildfires_dict, "data_loaded": True}),
        json.dumps({"data": api_detections.to_json(orient="split"), "data_loaded": True}),
        media_url,
        dash.no_update,
        previous_time_event,
    ]
