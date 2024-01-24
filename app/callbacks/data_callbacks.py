# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json

import dash
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from pyroclient import Client

import config as cfg
from app import app
from services import api_client, call_api
from utils.data import (
    past_ndays_api_events,
    process_bbox,
    read_stored_DataFrame,
    retrieve_site_from_device_id,
)


@app.callback(
    [
        Output("user_credentials", "data"),
        Output("user_headers", "data"),
        Output("form_feedback_area", "children"),
    ],
    Input("send_form_button", "n_clicks"),
    [
        State("username_input", "value"),
        State("password_input", "value"),
        State("user_headers", "data"),
    ],
)
def login_callback(n_clicks, username, password, user_headers):
    if user_headers is not None:
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
                client = Client(cfg.API_URL, username, password)

                return (
                    {"username": username, "password": password},
                    client.headers,
                    dash.no_update,
                )
            except Exception:
                # This if statement is verified if credentials are invalid
                form_feedback.append(html.P("Nom d'utilisateur et/ou mot de passe erroné."))

                return dash.no_update, dash.no_update, form_feedback

    raise PreventUpdate


@app.callback(
    [
        Output("store_api_events_data", "data"),
        Output("store_api_alerts_data", "data"),
        Output("trigger_no_events", "data"),
    ],
    [Input("main_api_fetch_interval", "n_intervals")],
    [
        State("store_api_events_data", "data"),
        State("store_api_alerts_data", "data"),
        State("user_headers", "data"),
        State("user_credentials", "data"),
    ],
    prevent_initial_call=True,
)
def api_watcher(n_intervals, local_events, local_alerts, user_headers, user_credentials):
    """
    Fetches and processes live event and alert data from the API at regular intervals.

    This callback periodically checks for new event and alert data from the API.
    It processes the new data, updates local storage with the latest information,
    and prepares it for displaying in the application.

    Parameters:
    - n_intervals (int): Number of intervals passed since the start of the app,
                         used to trigger the periodic update.
    - local_events (json): Currently stored events data in JSON format.
    - local_alerts (json): Currently stored alerts data in JSON format.
    - user_headers (dict): User authorization headers for API requests.
    - user_credentials (tuple): User credentials (username, password).

    Returns:
    - json: Updated events data in JSON format.
    - json: Updated alerts data in JSON format.
    """
    if user_headers is None:
        raise PreventUpdate
    user_token = user_headers["Authorization"].split(" ")[1]
    api_client.token = user_token

    # Read local data
    local_events, event_data_loaded = read_stored_DataFrame(local_events)
    local_alerts, alerts_data_loaded = read_stored_DataFrame(local_alerts)

    # Fetch events
    api_events = pd.DataFrame(call_api(api_client.get_unacknowledged_events, user_credentials)())
    api_events = past_ndays_api_events(api_events, n_days=1)  # keep only events from today
    if api_events.empty:
        return dash.no_update, dash.no_update, True
    api_events = api_events[::-1]  # Display the last alert first

    if event_data_loaded:
        new_api_events = api_events[~api_events["id"].isin(local_events["id"])]

    else:
        new_api_events = api_events

    if alerts_data_loaded:
        # drop old alerts
        local_alerts = local_alerts[local_alerts["event_id"].isin(api_events["id"])]

        # Find ongoing alerts for the events started within 30 minutes;
        # after that, any new alert is part of a new event
        local_alerts["created_at"] = pd.to_datetime(local_alerts["created_at"])

        # Define the end_event timestamp as timezone-naive
        end_event = pd.Timestamp.utcnow().replace(tzinfo=None) - pd.Timedelta(minutes=30)

        # Filter local_alerts based on the 'created_at' condition
        ongoing_local_alerts = local_alerts[local_alerts["created_at"] > end_event].copy()
        get_alerts = call_api(api_client.get_alerts_for_event, user_credentials)
        v = ongoing_local_alerts["event_id"].drop_duplicates().apply(lambda x: pd.DataFrame(get_alerts(x)))

        if len(v) == 0:
            raise PreventUpdate

        api_alerts = pd.concat(v.values).groupby(["event_id"]).head(cfg.MAX_ALERTS_PER_EVENT).reset_index(drop=True)
        new_api_alerts = api_alerts[~api_alerts["id"].isin(local_alerts["id"])].copy()
        local_alerts["processed_loc"] = local_alerts["localization"].apply(process_bbox)
        if len(new_api_alerts) == 0:
            raise PreventUpdate
        local_alerts = pd.concat([local_alerts, new_api_alerts], join="outer")
        local_alerts = local_alerts.drop_duplicates(subset=["id"])
        local_alerts = local_alerts.groupby(["event_id"]).head(cfg.MAX_ALERTS_PER_EVENT).reset_index(drop=True)
    else:
        get_alerts = call_api(api_client.get_alerts_for_event, user_credentials)
        _ = api_events["id"].apply(lambda x: pd.DataFrame(get_alerts(x)))  # type: ignore[arg-type, return-value]
        local_alerts = pd.concat(_.values).groupby(["event_id"]).head(cfg.MAX_ALERTS_PER_EVENT).reset_index(drop=True)
        local_alerts["created_at"] = pd.to_datetime(local_alerts["created_at"])
        local_alerts["processed_loc"] = local_alerts["localization"].apply(process_bbox)

    if len(new_api_events):
        alerts_data = new_api_events.merge(local_alerts, left_on="id", right_on="event_id").drop_duplicates(
            subset=["id_x"]
        )[["azimuth", "device_id"]]

        new_api_events["device_name"] = [
            f"{retrieve_site_from_device_id(api_client, user_credentials, device_id)} - {int(azimuth)}°".title()
            for _, (azimuth, device_id) in alerts_data.iterrows()
        ]

        if event_data_loaded:
            local_events = pd.concat([local_events, new_api_events], join="outer")
            local_events = local_events.drop_duplicates()

        else:
            local_events = new_api_events

    return [
        json.dumps({"data": local_events.to_json(orient="split"), "data_loaded": True}),
        json.dumps({"data": local_alerts.to_json(orient="split"), "data_loaded": True}),
        dash.no_update,
    ]


@app.callback(
    Output("media_url", "data"),
    Input("store_api_alerts_data", "data"),
    [
        State("media_url", "data"),
        State("user_headers", "data"),
        State("user_credentials", "data"),
    ],
    prevent_initial_call=True,
)
def get_media_url(
    local_alerts,
    media_url,
    user_headers,
    user_credentials,
):
    """
    Retrieves media URLs for alerts and manages the fetching process from the API.

    This callback is designed to efficiently load media URLs during app initialization
    and subsequently update them. Initially, it focuses on loading URLs event by event
    to quickly provide data for visualization. Once URLs for all events are loaded, the
    callback then methodically checks for and retrieves any missing URLs.

    The callback is triggered by two inputs: a change in the data to load and a regular
    interval check. It includes a cleanup step to remove event IDs no longer present in
    local alerts.

    Parameters:

    - interval (int): Current interval for fetching URLs.
    - local_alerts (json): Currently stored alerts data in JSON format.
    - media_url (dict): Dictionary holding media URLs for alerts.
    - user_headers (dict): User authorization headers for API requests.
    - user_credentials (tuple): User credentials (username, password).


    Returns:
    - dict: Updated dictionary with media URLs for each alert.
    """
    if user_headers is None:
        raise PreventUpdate
    user_token = user_headers["Authorization"].split(" ")[1]
    api_client.token = user_token

    local_alerts, alerts_data_loaded = read_stored_DataFrame(local_alerts)

    if not alerts_data_loaded:
        raise PreventUpdate

    current_event_ids = set(local_alerts["event_id"].astype(str))

    # Cleanup: Remove any event_ids from media_url not present in local_alerts
    media_url_keys = set(media_url.keys())
    for event_id in media_url_keys - current_event_ids:
        del media_url[event_id]

    # Loop through each row in local_alerts
    for _, row in local_alerts.iterrows():
        event_id = str(row["event_id"])
        media_id = str(row["media_id"])
        if event_id not in media_url:
            media_url[event_id] = {}

        # Check if the URL for this event_id and media_id already exists
        if media_id not in media_url[event_id]:
            # Fetch the URL for this media_id
            try:
                media_url[event_id][media_id] = call_api(api_client.get_media_url, user_credentials)(media_id)["url"]
            except Exception:  # General catch-all for other exceptions
                media_url[event_id][media_id] = ""  # Handle potential exceptions

    return media_url
