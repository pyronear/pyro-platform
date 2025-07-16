# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json

import pandas as pd
from dash import dcc, html

import config as cfg
from components.navbar import Navbar
from services import get_token

if not cfg.LOGIN:
    user_token = get_token(cfg.API_LOGIN, cfg.API_PWD)

else:
    user_token = None


def get_main_layout():
    return html.Div([
        dcc.Location(id="url", refresh=False),
        html.Div(
            id="custom_js_trigger",
            className="custom_js_trigger",
            title="none",
            style={"display": "none"},
        ),
        html.Div([
            Navbar(),  # This includes the navbar at the top of the page
            html.Div(id="page-content"),
        ]),
        dcc.Interval(id="main_api_fetch_interval", interval=30 * 1000),
        dcc.Store(
            id="api_sequences",
            storage_type="session",
            data=pd.DataFrame().to_json(orient="split"),
        ),
        dcc.Store(
            id="sub_api_sequences",
            storage_type="session",
            data=pd.DataFrame().to_json(orient="split"),
        ),
        dcc.Store(
            id="event_id_table",
            storage_type="session",
            data=pd.DataFrame().to_json(orient="split"),
        ),
        dcc.Store(
            id="api_detections",
            storage_type="session",
            data=json.dumps({}),
        ),
        dcc.Store(
            id="are_detections_loaded",
            storage_type="session",
            data=json.dumps({}),
        ),
        dcc.Store(
            id="api_cameras",
            storage_type="session",
            data=pd.DataFrame().to_json(orient="split"),
        ),
        dcc.Store(
            id="sequence_on_display",
            storage_type="session",
            data=pd.DataFrame().to_json(orient="split"),
        ),
        dcc.Store(
            id="unmatched_event_id_table",
            storage_type="session",
            data=pd.DataFrame().to_json(orient="split"),
        ),
        dcc.Store(id="sequence_id_on_display", storage_type="session", data=0),
        dcc.Store(id="auto-move-state", storage_type="session", data={"active": True}),
        # Add this to your app.layout
        dcc.Store(id="bbox_visibility", storage_type="session", data={"visible": True}),
        # Storage components saving the user's headers and credentials
        dcc.Store(id="user_token", storage_type="session", data=user_token),
        dcc.Store(id="user_name", storage_type="session"),
        dcc.Store(id="to_acknowledge", storage_type="session", data=0),
        dcc.Store(id="trigger_no_detections", storage_type="session", data=False),
        dcc.Store(id="available-stream-sites", storage_type="session"),
        dcc.Store(id="selected-camera-info", storage_type="session"),
        dcc.Store(id="language", storage_type="session", data="fr"),
        dcc.Store(id="selected_event_id", storage_type="session", data=None),
        dcc.Store(id="detection_fetch_limit", storage_type="session", data=10),
    ])
