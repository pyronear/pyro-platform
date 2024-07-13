# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import json

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc, html

import config as cfg
from components.navbar import Navbar
from services import instantiate_token

if not cfg.LOGIN:
    api_client = instantiate_token()
    token = api_client.token
else:
    token = None


def get_main_layout():
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            html.Div(
                [
                    Navbar(),  # This includes the navbar at the top of the page
                    html.Div(id="page-content"),
                ]
            ),
            dcc.Interval(id="main_api_fetch_interval", interval=30 * 1000),
            dcc.Store(
                id="store_wildfires_data",
                storage_type="session",
                data=json.dumps(
                    {
                        "data": pd.DataFrame().to_json(orient="split"),
                        "data_loaded": False,
                    }
                ),
            ),
            dcc.Store(
                id="store_detections_data",
                storage_type="session",
                data=json.dumps(
                    {
                        "data": pd.DataFrame().to_json(orient="split"),
                        "data_loaded": False,
                    }
                ),
            ),
            dcc.Store(id="last_displayed_wildfire_id", storage_type="session"),
            dcc.Store(
                id="detection_on_display",
                storage_type="session",
                data=json.dumps(
                    {
                        "data": pd.DataFrame().to_json(orient="split"),
                        "data_loaded": False,
                    }
                ),
            ),
            dcc.Store(
                id="media_url",
                storage_type="session",
                data={},
            ),
            dcc.Store(id="wildfire_id_on_display", data=0),
            dcc.Store(id="auto-move-state", data={"active": True}),
            # Add this to your app.layout
            dcc.Store(id="bbox_visibility", data={"visible": True}),
            dbc.Modal(
                [
                    dbc.ModalBody(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        className="spinner-border text-primary",
                                        role="status",
                                    ),
                                    html.Div(
                                        "Chargement des données...",
                                        className="ml-2 d-inline-block align-top",
                                    ),  # Ensure text is inline with spinner
                                ],
                                className="d-flex align-items-center justify-content-center",  # Center both spinner and text
                            )
                        ],
                        style={"textAlign": "center"},  # Center the modal body content
                    )
                ],
                id="modal-loading",
                centered=True,
                is_open=False,
            ),
            # Storage components saving the user's headers and credentials
            dcc.Store(id="client_token", storage_type="session", data=token),
            # [TEMPORARY FIX] Storing the user's credentials to refresh the token when needed
            dcc.Store(id="to_acknowledge", data=0),
            dcc.Store(id="trigger_no_wildfires", data=False),
        ]
    )
