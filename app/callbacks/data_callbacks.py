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
    ],
    Input("send_form_button", "n_clicks"),
    [
        State("username_input", "value"),
        State("password_input", "value"),
        State("client_token", "data"),
    ],
)
def login_callback(n_clicks, username, password, client_token):
    if client_token is not None:
        return dash.no_update, dash.no_update, dash.no_update

    if n_clicks:
        # We instantiate the form feedback output
        form_feedback = [dcc.Markdown("---")]
        # First check verifies whether both a username and a password have been provided
        if username is None or password is None or len(username) == 0 or len(password) == 0:
            # If either the username or the password is missing, the condition is verified

            # We add the appropriate feedback
            form_feedback.append(html.P("Il semble qu'il manque votre nom d'utilisateur et/ou votre mot de passe."))

            # The login modal remains open; other outputs are updated with arbitrary values
            return dash.no_update, dash.no_update, form_feedback
        else:
            # This is the route of the API that we are going to use for the credential check
            try:
                client = instantiate_token(username, password)

                return (
                    client.token,
                    dash.no_update,
                )
            except Exception:
                # This if statement is verified if credentials are invalid
                form_feedback.append(html.P("Nom d'utilisateur et/ou mot de passe erroné."))

                return dash.no_update, form_feedback

    raise PreventUpdate


@app.callback(
    [
        Output("store_wildfires_data", "data"),
        Output("store_detections_data", "data"),
        Output("media_url", "data"),
        Output("trigger_no_wildfires", "data"),
    ],
    [Input("main_api_fetch_interval", "n_intervals")],
    [
        State("client_token", "data"),
        State("media_url", "data"),
    ],
    prevent_initial_call=True,
)
def data_transform(n_intervals, client_token, media_url):
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
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d_%H:%M:%S")
    api_client = Client(client_token, cfg.API_URL)
    response = api_client.fetch_unlabeled_detections(from_date=yesterday)
    api_detections = pd.DataFrame(response.json())

    if api_detections.empty:
        return [
            json.dumps(
                {
                    "data": pd.DataFrame().to_json(orient="split"),
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
        ]

    # Find ongoing detections for the wildfires started within 30 minutes;
    # after that, any new detection is part of a new wildfire
    api_detections["created_at"] = pd.to_datetime(api_detections["created_at"])
    # Trier les détections par "created_at"
    api_detections = api_detections.sort_values(by="created_at")

    # Initialiser la liste pour les wildfires
    id_counter = 1
    cameras = pd.DataFrame(api_client.fetch_cameras().json())
    api_detections["lat"] = None
    api_detections["lon"] = None
    api_detections["wildfire_id"] = None
    api_detections["processed_loc"] = None
    api_detections["processed_loc"] = api_detections["bboxes"].apply(process_bbox)

    last_detection_time_per_camera: dict[int, str] = {}
    wildfires_dict: dict[int, list] = {}

    media_dict = api_detections.set_index("id")["url"].to_dict()

    # Parcourir les détections pour les regrouper en wildfires
    for i, detection in api_detections.iterrows():
        camera_id = api_detections.at[i, "camera_id"]
        camera = cameras.loc[cameras["id"] == camera_id]
        camera = camera.iloc[0]  # Ensure camera is a Series
        api_detections.at[i, "lat"] = camera["lat"]
        api_detections.at[i, "lon"] = camera["lon"]
        print("ICI")
        print(detection["id"])
        print(media_dict[int(detection["id"])])

        media_url[detection["id"]] = media_dict[detection["id"]]

        if camera_id not in wildfires_dict:
            wildfires_dict.setdefault(camera_id, [])
            last_detection_time_per_camera.setdefault(camera_id, "")
            # Initialize the first wildfire for this camera
            wildfire = {
                "id": id_counter,
                "camera_name": camera["name"],
                "created_at": detection["created_at"],
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
                    "created_at": detection["created_at"],
                    "detection_ids": [detection["id"]],
                }
                wildfires_dict[camera_id].append(wildfire)
                id_counter += 1
        api_detections.at[i, "wildfire_id"] = wildfires_dict[camera_id][-1]["id"]
        last_detection_time_per_camera[camera_id] = detection["created_at"]

    # Convert the dictionary to a list of wildfires
    wildfires = []
    for wildfire_list in wildfires_dict.values():
        wildfires.extend(wildfire_list)

    # Convertir la liste des wildfires en DataFrame
    wildfires_df = pd.DataFrame(wildfires)
    return [
        json.dumps({"data": wildfires_df.to_json(orient="split"), "data_loaded": True}),
        json.dumps({"data": api_detections.to_json(orient="split"), "data_loaded": True}),
        media_url,
        dash.no_update,
    ]
