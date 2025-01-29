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
                id="api_sequences",
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
            dcc.Store(id="sequence_id_on_display", data=0),
            dcc.Store(id="auto-move-state", data={"active": True}),
            # Add this to your app.layout
            dcc.Store(id="bbox_visibility", data={"visible": True}),
            # Storage components saving the user's headers and credentials
            dcc.Store(id="user_token", storage_type="session", data=user_token),
            # [TEMPORARY FIX] Storing the user's credentials to refresh the token when needed
            dcc.Store(id="to_acknowledge", data=0),
            dcc.Store(id="trigger_no_detections", data=False),
            html.Div(
                id="confirmation-modal",
                style={
                    "display": "none",  # Hidden by default
                    "position": "fixed",
                    "top": "0",
                    "left": "0",
                    "width": "100%",
                    "height": "100%",
                    "background-color": "rgba(0, 0, 0, 0.5)",
                    "z-index": "1000",
                    "justify-content": "center",
                    "align-items": "center",
                },
                children=[
                    html.Div(
                        [
                            html.H4(
                                "Est-ce une fumée suspecte ? ",
                                style={
                                    "margin-bottom": "20px",
                                    "font-size": "20px",
                                    "font-weight": "bold",
                                },
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "Oui, c'est une fumée",
                                        id="confirm-wildfire",
                                        n_clicks=0,
                                        style={
                                            "margin-right": "10px",
                                            "padding": "10px 20px",
                                            "background-color": "#4CAF50",
                                            "color": "white",
                                            "border": "none",
                                            "border-radius": "5px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    html.Button(
                                        "No, c'est un faux positif",
                                        id="confirm-non-wildfire",
                                        n_clicks=0,
                                        style={
                                            "margin-right": "10px",
                                            "padding": "10px 20px",
                                            "background-color": "#f44336",
                                            "color": "white",
                                            "border": "none",
                                            "border-radius": "5px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    html.Button(
                                        "Cancel",
                                        id="cancel-confirmation",
                                        n_clicks=0,
                                        style={
                                            "padding": "10px 20px",
                                            "background-color": "#555",
                                            "color": "white",
                                            "border": "none",
                                            "border-radius": "5px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "justify-content": "center"},
                            ),
                        ],
                        style={
                            "background-color": "white",
                            "padding": "30px",
                            "border-radius": "10px",
                            "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.2)",
                            "max-width": "400px",
                            "width": "100%",
                            "text-align": "center",
                        },
                    ),
                ],
            ),
        ]
    )
