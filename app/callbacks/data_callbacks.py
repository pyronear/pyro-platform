# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json
from io import StringIO

import dash
import logging_config
import numpy as np
import pandas as pd
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from main import app
from translations import translate

import config as cfg
from pages.cameras_status import display_cam_cards
from services import get_client, get_token
from utils.data import compute_overlap, convert_dt_to_local_tz, process_bbox, sequences_have_changed

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


from dash import Input, Output, State, callback


@callback(
    Output("detection_fetch_limit", "data"),
    Input("detection_fetch_limit_input", "value"),
    prevent_initial_call=True,  # optional, remove if you want it to run on first load
)
def update_fetch_limit(value):
    if value is None:
        return 10  # fallback default
    return value


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

    if not cameras.empty:
        cameras["last_active_at"] = pd.to_datetime(cameras["last_active_at"])

        # Apply the local datetime transformation and formatting at once
        cameras["last_active_at_local"] = cameras.apply(
            lambda row: convert_dt_to_local_tz(row["lat"], row["lon"], row["last_active_at"])
            if pd.notnull(row["last_active_at"])
            else None,
            axis=1,
        )

        cameras = cameras.sort_values("name")

    return display_cam_cards(cameras)


@app.callback(
    [Output("api_sequences", "data"), Output("event_id_table", "data")],
    [
        Input("main_api_fetch_interval", "n_intervals"),
        Input("api_cameras", "data"),
        Input("to_acknowledge", "data"),
        Input("unmatched_event_id_table", "data"),
        Input("my-date-picker-single", "date"),
    ],
    [State("api_sequences", "data"), State("user_token", "data"), State("event_id_table", "data")],
    prevent_initial_call=True,
)
def api_watcher(
    n_intervals,
    api_cameras,
    to_acknowledge,
    unmatched_event_id_table,
    selected_date,
    local_sequences,
    user_token,
    local_event_id_table,
):
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
    client = get_client(user_token)

    try:
        if selected_date:
            response = client.fetch_sequences_from_date(selected_date, limit=100)
        else:
            response = client.fetch_latest_sequences()

        api_sequences = pd.DataFrame(response.json())

        if not api_sequences.empty:
            started_at = pd.to_datetime(api_sequences["started_at"], format="%Y-%m-%dT%H:%M:%S.%f", errors="coerce")
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

            api_sequences["started_at_local"] = api_sequences.apply(
                lambda row: convert_dt_to_local_tz(row["lat"], row["lon"], row["started_at"])
                if pd.notnull(row["started_at"])
                else None,
                axis=1,
            )
            api_sequences["last_seen_at_local"] = api_sequences.apply(
                lambda row: convert_dt_to_local_tz(row["lat"], row["lon"], row["last_seen_at"])
                if pd.notnull(row["last_seen_at"])
                else None,
                axis=1,
            )

            unmatched_event_id_table = json.loads(unmatched_event_id_table)

            api_sequences, event_id_table = compute_overlap(
                api_sequences, unmatched_event_table=unmatched_event_id_table
            )

            local_event_id_table = pd.read_json(StringIO(local_event_id_table), orient="split")

            # Load local sequences safely
            if local_sequences:
                local_sequences_df = pd.read_json(StringIO(local_sequences), orient="split")
            else:
                local_sequences_df = pd.DataFrame()

            # Ensure valid DataFrames
            if not isinstance(local_event_id_table, pd.DataFrame):
                local_event_id_table = pd.DataFrame()
            if not isinstance(event_id_table, pd.DataFrame):
                event_id_table = pd.DataFrame()

            # Check event condition: either empty or sequences match
            event_condition = event_id_table.empty or (
                "sequences" in local_event_id_table.columns
                and "sequences" in event_id_table.columns
                and np.array_equal(local_event_id_table["sequences"].values, event_id_table["sequences"].values)
            )

            # Now apply sequence comparison only if event condition is true
            if event_condition:
                if not local_sequences_df.empty and not api_sequences.empty:
                    if not sequences_have_changed(api_sequences, local_sequences_df):
                        logger.info("Skipping update: no significant change detected")
                        return dash.no_update

        return api_sequences.to_json(orient="split"), event_id_table.to_json(orient="split")

    except Exception as e:
        logger.error(f"Failed to fetch sequences: {e}")
        return pd.DataFrame().to_json(orient="split"), pd.DataFrame().to_json(orient="split")


@app.callback(
    Output("sub_api_sequences", "data"),
    Input("api_sequences", "data"),
    State("sub_api_sequences", "data"),
    prevent_initial_call=True,
)
def update_sub_api_sequences(api_sequences, local_sub_sequences):
    cols = ["id", "camera_id", "cone_azimuth", "is_wildfire", "started_at", "started_at_local", "overlap"]

    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")

    if api_sequences.empty:
        logger.info("api_sequences is empty, returning empty DataFrame with expected columns")
        empty_df = pd.DataFrame(columns=cols)
        return empty_df.to_json(orient="split")

    logger.info("update_sub_api_sequences triggered")

    sub_api_sequences = api_sequences[cols].copy()

    if not local_sub_sequences:
        logger.info("No previous local_sub_sequences, sending initial data")
        return sub_api_sequences.to_json(orient="split")

    local_sub_sequences_df = pd.read_json(StringIO(local_sub_sequences), orient="split")

    if local_sub_sequences_df.empty:
        logger.info("local_sub_sequences_df is empty, sending data")
        return sub_api_sequences.to_json(orient="split")

    if not sequences_have_changed(sub_api_sequences, local_sub_sequences_df, ["started_at_local", "is_wildfire"]):
        logger.info("No change in sub_api_sequences, skipping update")
        return dash.no_update

    logger.info("Change detected in sub_api_sequences")
    return sub_api_sequences.to_json(orient="split")


@app.callback(
    [Output("are_detections_loaded", "data"), Output("sequence_on_display", "data"), Output("api_detections", "data")],
    [
        Input("sequence_id_on_display", "data"),
        Input("detection_fetch_limit", "data"),
        Input("detection_fetch_desc_store", "data"),
    ],
    [
        State("api_sequences", "data"),
        State("api_detections", "data"),
        State("are_detections_loaded", "data"),
        State("user_token", "data"),
    ],
    prevent_initial_call=True,
)
def load_detections(
    sequence_id_on_display,
    detection_fetch_limit,
    detection_fetch_desc,
    api_sequences,
    api_detections,
    are_detections_loaded,
    user_token,
):
    if user_token is None or sequence_id_on_display is None:
        raise PreventUpdate

    detection_fetch_desc = detection_fetch_desc if detection_fetch_desc else False

    try:
        api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
        api_detections = dict(json.loads(api_detections))
        are_detections_loaded = dict(json.loads(are_detections_loaded))
        sequence_id_on_display = str(sequence_id_on_display)
    except Exception as e:
        logger.error(f"Deserialization error: {e}")
        return dash.no_update, dash.no_update, dash.no_update

    if api_sequences.empty:
        return dash.no_update, dash.no_update, dash.no_update

    sequence_on_display = pd.DataFrame().to_json(orient="split")
    client = get_client(user_token)

    detection_key = f"{sequence_id_on_display}_{detection_fetch_limit}_{detection_fetch_desc}"

    if detection_key not in api_detections.keys():
        try:
            response = client.fetch_sequences_detections(
                sequence_id=sequence_id_on_display, limit=detection_fetch_limit, desc=detection_fetch_desc
            )
            data = response.json()
            detections = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()

            if not detections.empty and "bboxes" in detections.columns:
                detections = detections.iloc[::-1].reset_index(drop=True)
                detections["processed_bboxes"] = detections["bboxes"].apply(process_bbox)

                sequence_meta = api_sequences.loc[api_sequences["id"].astype(str) == sequence_id_on_display]
                if not sequence_meta.empty:
                    lat = sequence_meta.iloc[0].get("lat")
                    lon = sequence_meta.iloc[0].get("lon")

                    if "created_at" in detections.columns and pd.notnull(lat) and pd.notnull(lon):
                        detections["created_at_local"] = detections["created_at"].apply(
                            lambda dt: convert_dt_to_local_tz(lat, lon, dt) if pd.notnull(dt) else None
                        )

            api_detections[detection_key] = detections.to_json(orient="split")

        except Exception as e:
            logger.error(f"Error fetching detections for {sequence_id_on_display}: {e}")
            return dash.no_update, dash.no_update, dash.no_update

    sequence_on_display = api_detections[detection_key]

    return json.dumps(are_detections_loaded), sequence_on_display, json.dumps(api_detections)


@app.callback(
    Output("unmatched_event_id_table", "data"),
    Input("unmatch-sequence-button", "n_clicks"),
    State("unmatched_event_id_table", "data"),
    State("sequence_id_on_display", "data"),
    State("event_id_table", "data"),
    State("selected_event_id", "data"),
    prevent_initial_call=True,
)
def unmatch_sequence_and_store(n_clicks, unmatched_event_json, sequence_id, event_id_table_json, selected_event_id):
    if not sequence_id or not selected_event_id or n_clicks is None:
        raise PreventUpdate

    try:
        sequence_id_int = int(sequence_id)

        # Load current unmatched list
        try:
            unmatched_list = json.loads(unmatched_event_json)
            if not isinstance(unmatched_list, list):
                unmatched_list = []
        except Exception as e:
            logger.warning(f"Invalid unmatched_event_id_table, resetting. Error: {e}")
            unmatched_list = []

        # Load event_id_table to find sequences of selected_event_id
        event_id_table = pd.read_json(StringIO(event_id_table_json), orient="split")
        row = event_id_table[event_id_table["event_id"] == selected_event_id]

        if row.empty:
            raise PreventUpdate

        group_sequences = tuple(row.iloc[0]["sequences"])

        # Add and deduplicate
        unmatched_list.append((sequence_id_int, group_sequences))
        unmatched_list = list({(sid, tuple(seq)) for sid, seq in unmatched_list})

        logger.info(f"Unmatched sequence {sequence_id_int} from event {selected_event_id}")

        return json.dumps(unmatched_list)

    except Exception as e:
        logger.error(f"Error unmatching sequence: {e}")
        raise PreventUpdate
