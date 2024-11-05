# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from components.alerts import create_event_list
from utils.display import build_alerts_map

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.css.append_css({"external_url": "/assets/style.css"})


def homepage_layout(user_headers, user_credentials):
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col([create_event_list()], width=2, className="mb-4"),
                    dbc.Col(
                        [
                            html.Div(
                                id="zoom-containement-container",
                                className="common-style",
                                style={"overflow": "hidden"},
                                children=[
                                    html.Div(
                                    id="image-container-with-bbox",
                                    style={"position": "relative"},
                                    children=[
                                        html.Div(
                                            id="image-container",
                                            children=[
                                                html.Img(
                                                    id="main-image",
                                                    src="./assets/images/no-alert-default.png",
                                                    className="zoomable-image",
                                                    style={"max-width": "100%", "height": "auto"},
                                                )
                                            ],
                                        ),
                                        html.Div(
                                            id="bbox-container", 
                                            style={"display": "block"},
                                            children=[
                                                html.Div(
                                                    id="bbox-positioning",
                                                    style={"display": "none"},
                                                    children=[
                                                        html.Div(
                                                            id="bbox-styling",
                                                            style={"border": "2px solid red",
                                                                   "height": "100%", 
                                                                   "width": "100%",
                                                                    "zIndex": "1"},
                                                        ),
                                                    ]
                                                )
                                            ],
                                            ),
                                    ],
                            ),
                                ]
                            ),
                            html.Div(
                                dcc.Slider(id="image-slider", min=0, max=10, step=1, value=0),
                                id="slider-container",
                                className="common-style-slider",
                                style={"display": "none", "marginTop": "10px"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Activer / Désactiver l'animation",
                                            id="auto-move-button",
                                            n_clicks=1,
                                            className="btn-uniform common-style",
                                            style={"backgroundColor": "#FD5252"},
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Afficher / Cacher la prédiction",
                                            id="hide-bbox-button",
                                            n_clicks=0,
                                            className="btn-uniform common-style",
                                            style={"backgroundColor": "#FEBA6A"},
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        html.A(
                                            dbc.Button(
                                                "Télécharger l'image",
                                                className="btn-uniform common-style",
                                                style={"backgroundColor": "#2C796E"},
                                                id="dl-image-button",
                                            ),
                                            className="no-underline",
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
                                            className="btn-uniform common-style",
                                            style={"backgroundColor": "#054546"},
                                        ),
                                        width=3,
                                    ),
                                ],
                                className="mb-4",
                                style={"display": "flex", "marginTop": "10px"},
                            ),
                        ],
                        width=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Row(
                                dbc.Button(
                                    "Agrandir la carte",
                                    className="common-style",
                                    style={"backgroundColor": "#FEBA6A"},
                                    id="map-button",
                                ),
                                className="mb-2",
                            ),
                            dbc.Row(
                                dbc.Col(
                                    build_alerts_map(user_headers, user_credentials),
                                    className="common-style",
                                    style={
                                        "position": "relative",
                                        "width": "100%",
                                        "paddingTop": "100%",
                                    },
                                ),
                            ),
                            dbc.Row(
                                html.Div(
                                    id="alert-information",
                                    children=[
                                        html.H4("Alerte Information"),
                                        html.P(id="alert-camera", children="Camera: "),
                                        html.P(id="alert-location", children="Localisation: "),
                                        html.P(id="alert-azimuth", children="Azimuth de detection: "),
                                        html.P(id="alert-date", children="Date: "),
                                    ],
                                    className="common-style",
                                    style={"fontSize": "15px", "fontWeight": "bold", "display": "none"},
                                ),
                                className="mt-4",
                                id="alert-panel",
                            ),
                        ],
                        width=2,
                        className="mb-4",
                    ),
                ]
            ),
            dcc.Interval(id="auto-slider-update", interval=500, n_intervals=0),
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
