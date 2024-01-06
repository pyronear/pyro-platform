# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_bootstrap_components as dbc
from dash import dcc, html

from components.alerts import create_event_list
from utils.display import build_alerts_map


def homepage_layout(user_headers, user_credentials):
    return dbc.Container(
        [
            dbc.Row(
                [
                    # Column for the alert list
                    dbc.Col(create_event_list(), width=2, className="mb-4"),
                    # Column for the image
                    dbc.Col(
                        [
                            html.Div(
                                id="image-container-with-bbox",
                                style={"position": "relative"},  # Ensure this container is relatively positioned
                                children=[
                                    html.Div(id="image-container"),  # This will contain the image
                                    html.Div(
                                        id="bbox-container", style={"display": "block"}
                                    ),  # This will contain the bounding box
                                ],
                            ),
                            dcc.Slider(id="image-slider", min=0, max=0, step=1, value=0),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Activer / Désactiver l'animation",
                                            id="auto-move-button",
                                            n_clicks=1,
                                            style={
                                                "backgroundColor": "#FD5252",
                                                "width": "100%",
                                                "border": "none",
                                            },
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Afficher / Cacher la prédiction",
                                            id="hide-bbox-button",
                                            n_clicks=0,
                                            style={
                                                "backgroundColor": "#FEBA6A",
                                                "width": "100%",
                                                "border": "none",
                                            },
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        html.A(
                                            dbc.Button(
                                                "Télécharger l'image",
                                                style={
                                                    "backgroundColor": "#2C796E",
                                                    "width": "100%",
                                                    "border": "none",
                                                },
                                                id="dl-image-button",
                                            ),
                                            id="download-link",
                                            download="",
                                            href="",
                                            target="_blank",
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Acquitter l'alerte",
                                            id="acknowledge-button",
                                            n_clicks=1,
                                            style={
                                                "backgroundColor": "#054546",
                                                "width": "100%",
                                                "border": "none",
                                            },
                                        ),
                                        width=3,
                                    ),
                                ],
                                className="mb-4",
                            ),
                        ],
                        width=8,
                    ),
                    # Column for buttons with added margins
                    dbc.Col(
                        [
                            # Modal issue let's add this later
                            dbc.Row(
                                dbc.Button(
                                    "Agrandir la carte",
                                    style={
                                        "backgroundColor": "#FEBA6A",
                                        "width": "100%",
                                        "border": "none",
                                    },
                                    id="map-button",
                                ),
                                className="mb-2",
                            ),
                            dbc.Row(
                                # This row contains the map
                                dbc.Col(
                                    build_alerts_map(user_headers, user_credentials),
                                    style={
                                        "position": "relative",
                                        "width": "100%",
                                        "paddingTop": "100%",  # This creates the square aspect ratio
                                        "margin": "auto",
                                    },
                                ),
                            ),
                        ],
                        width=2,
                        className="mb-4",
                    ),
                ]
            ),
            dcc.Interval(id="auto-slider-update", interval=500, n_intervals=0),  # in milliseconds
            dbc.Modal(
                [
                    dbc.ModalHeader("Carte"),
                    dbc.ModalBody(
                        build_alerts_map(user_headers, user_credentials, id_suffix="-md"),
                    ),
                ],
                id="map-modal",
                keyboard=False,
                fullscreen=True,
                is_open=False,
            ),
        ],
        fluid=True,
    )
