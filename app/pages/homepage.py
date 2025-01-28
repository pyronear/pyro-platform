# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from components.alerts import create_event_list
from utils.display import build_alerts_map

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.css.append_css({"external_url": "/assets/style.css"})


def homepage_layout(user_headers, user_credentials, lang="fr"):
    translate = {
        "fr": {
            "show_hide_prediction": "Afficher / Cacher la prédiction",
            "download_image": "Télécharger l'image",
            "acknowledge_alert": "Acquitter l'alerte",
            "enlarge_map": "Agrandir la carte",
            "alert_information": "Information Alerte",
            "camera": "Caméra: ",
            "camera_location": "Position caméra: ",
            "detection_azimuth": "Azimuth de detection: ",
            "date": "Date: ",
            "map": "Carte",
            "no_alert_default_image": "./assets/images/no-alert-default.png",
        },
        "es": {
            "show_hide_prediction": "Mostrar / Ocultar la predicción",
            "download_image": "Descargar la imagen",
            "acknowledge_alert": "Descartar la alerta",
            "enlarge_map": "Ampliar el mapa",
            "alert_information": "Información sobre alerta",
            "camera": "Cámara: ",
            "camera_location": "Ubicación cámara: ",
            "detection_azimuth": "Azimut de detección: ",
            "date": "Fecha: ",
            "map": "Mapa",
            "no_alert_default_image": "./assets/images/no-alert-default-es.png",
        },
    }

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
                                                        src=translate[lang]["no_alert_default_image"],
                                                        className="zoomable-image",
                                                        style={"maxWidth": "100%", "height": "auto"},
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
                                                                style={
                                                                    "border": "2px solid red",
                                                                    "height": "100%",
                                                                    "width": "100%",
                                                                    "zIndex": "10",
                                                                },
                                                            ),
                                                        ],
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            html.Img(src="assets/images/play-pause.svg"),
                                            id="auto-move-button",
                                            n_clicks=1,
                                            style={"height": "100%", "width": "100%", "border": "0"},
                                        ),
                                        width=1,
                                    ),
                                    dbc.Col(
                                        html.Div(
                                            dcc.Slider(id="image-slider", min=0, max=10, step=1, value=0),
                                            id="slider-container",
                                            className="common-style-slider",
                                            style={"display": "none"},
                                        ),
                                        width=11,
                                    ),
                                ],
                                style={"marginTop": "10px"},
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            translate[lang]["show_hide_prediction"],
                                            id="hide-bbox-button",
                                            n_clicks=0,
                                            className="btn-uniform",
                                            style={},  # Will be overwritten dynamically
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        html.A(
                                            dbc.Button(
                                                translate[lang]["download_image"],
                                                className="btn-uniform",
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
                                            translate[lang]["acknowledge_alert"],
                                            id="acknowledge-button",
                                            n_clicks=0,
                                            className="btn-uniform",
                                        ),
                                        width=3,
                                    ),
                                ],
                                className="mb-4",
                                style={"display": "flex", "marginTop": "10px", "justify-content": "space-evenly"},
                            ),
                        ],
                        width=8,
                        style={"padding": "0"},
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                html.Div(
                                    id="alert-information",
                                    className="common-style",
                                    style={"display": "none", "padding": "8px"},
                                    children=[
                                        html.Div(
                                            id="alert-information-styling-container",
                                            children=[
                                                html.H5(
                                                    translate[lang]["alert_information"], style={"text-align": "center"}
                                                ),
                                                html.Div(
                                                    id="alert-camera",
                                                    children=[
                                                        html.Span(
                                                            id="alert-camera-header",
                                                            children=translate[lang]["camera"],
                                                            className="alert-information-title",
                                                        ),
                                                        html.Span(
                                                            id="alert-camera-value",
                                                            children=[],
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    id="camera-location",
                                                    children=[
                                                        html.Span(
                                                            id="camera-location-header",
                                                            children=translate[lang]["camera_location"],
                                                            className="alert-information-title",
                                                        ),
                                                        html.Span(
                                                            id="camera-location-value",
                                                            children=[],
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    id="alert-azimuth",
                                                    children=[
                                                        html.Span(
                                                            id="alert-azimuth-header",
                                                            children=translate[lang]["detection_azimuth"],
                                                            className="alert-information-title",
                                                        ),
                                                        html.Span(
                                                            id="alert-azimuth-value",
                                                            children=[],
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    id="alert-date",
                                                    children=[
                                                        html.Span(
                                                            id="alert-date-header",
                                                            children=translate[lang]["date"],
                                                            className="alert-information-title",
                                                        ),
                                                        html.Span(
                                                            id="alert-date-value",
                                                            children=[],
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                id="alert-panel",
                            ),
                            html.Div(
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
                            html.Div(
                                dbc.Button(
                                    translate[lang]["enlarge_map"],
                                    className="common-style",
                                    style={"backgroundColor": "#FEBA6A", "color": "black", "width": "100%"},
                                    id="map-button",
                                ),
                            ),
                        ],
                        width=2,
                        style={
                            "display": "flex",
                            "flex-direction": "column",
                            "gap": "16px",
                        },
                    ),
                ]
            ),
            dcc.Interval(id="auto-slider-update", interval=500, n_intervals=0),
            dbc.Modal(
                [
                    dbc.ModalHeader(translate[lang]["map"]),
                    dbc.ModalBody(
                        build_alerts_map(user_headers, user_credentials, id_suffix="-md"),
                    ),
                ],
                id="map-modal",
                keyboard=False,
                fullscreen=True,
                is_open=False,
            ),
            dcc.Store(id="language", data=lang),
        ],
        fluid=True,
    )
