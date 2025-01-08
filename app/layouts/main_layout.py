# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json

import pandas as pd
from dash import dcc, html

import config as cfg
from components.navbar import Navbar
from services import api_client

if not cfg.LOGIN:
    user_token = api_client.token

else:
    user_token = None

print("user token AA", user_token)


def get_main_layout():
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            html.Div(
                id="custom_js_trigger",
                className="custom_js_trigger",
                title="none",
                style={"display": "none"},
            ),
            html.Div(
                [
                    Navbar(),  # This includes the navbar at the top of the page
                    html.Div(id="page-content"),
                ]
            ),
            dcc.Interval(id="main_api_fetch_interval", interval=30 * 1000),
            dcc.Store(
                id="api_detections",
                storage_type="session",
                data=json.dumps(
                    {
                        "data": pd.DataFrame().to_json(orient="split"),
                        "data_loaded": False,
                    }
                ),
            ),
            dcc.Store(
                id="api_cameras",
                storage_type="session",
                data=json.dumps(
                    {
                        "data": pd.DataFrame().to_json(orient="split"),
                        "data_loaded": False,
                    }
                ),
            ),
            dcc.Store(
                id="alert_on_display",
                storage_type="session",
                data=json.dumps(
                    {
                        "data": pd.DataFrame().to_json(orient="split"),
                        "data_loaded": False,
                    }
                ),
            ),
            dcc.Store(id="event_id_on_display", data=0),
            dcc.Store(id="auto-move-state", data={"active": True}),
            # Add this to your app.layout
            dcc.Store(id="bbox_visibility", data={"visible": True}),
            # Storage components saving the user's headers and credentials
            dcc.Store(id="user_token", storage_type="session", data=user_token),
            # [TEMPORARY FIX] Storing the user's credentials to refresh the token when needed
            dcc.Store(id="to_acknowledge", data=0),
            dcc.Store(id="trigger_no_detections", data=False),
        ]
    )
