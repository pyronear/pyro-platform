# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from components.alerts import create_event_list
from utils.display import build_alerts_map

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.css.append_css({"external_url": "/assets/style.css"})


def homepage_layout(user_token, api_cameras, lang="fr"):
    print("user token 00", user_token)
    translate = {
        "fr": {
            "animate_on_off": "Activer / Désactiver l'animation",
            "show_hide_prediction": "Afficher / Cacher la prédiction",
            "download_image": "Télécharger l'image",
            "acknowledge_alert": "Acquitter l'alerte",
            "enlarge_map": "Agrandir la carte",
            "alert_information": "Information Alerte",
            "camera": "Caméra: ",
            "location": "Localisation: ",
            "detection_azimuth": "Azimuth de detection: ",
            "date": "Date: ",
            "map": "Carte",
            "no_alert_default_image": "./assets/images/no-alert-default.png",
        },
        "es": {
            "animate_on_off": "Activar / Desactivar la animación",
            "show_hide_prediction": "Mostrar / Ocultar la predicción",
            "download_image": "Descargar la imagen",
            "acknowledge_alert": "Descartar la alerta",
            "enlarge_map": "Ampliar el mapa",
            "alert_information": "Información sobre alerta",
            "camera": "Cámara: ",
            "location": "Ubicación: ",
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
                                            translate[lang]["animate_on_off"],
                                            id="auto-move-button",
                                            n_clicks=1,
                                            className="btn-uniform common-style",
                                            style={"backgroundColor": "#FD5252"},
                                        ),
                                        width=3,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            translate[lang]["show_hide_prediction"],
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
                                                translate[lang]["download_image"],
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
                                            translate[lang]["acknowledge_alert"],
                                            id="acknowledge-button",
                                            n_clicks=0,
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
                                    translate[lang]["enlarge_map"],
                                    className="common-style",
                                    style={"backgroundColor": "#FEBA6A"},
                                    id="map-button",
                                ),
                                className="mb-2",
                            ),
                            dbc.Row(
                                dbc.Col(
                                    build_alerts_map(api_cameras),
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
                                    className="common-style",
                                    style={"display": "none"},
                                    children=[
                                        html.Div(
                                            id="alert-information-styling-container",
                                            style={"padding": "5px"},
                                            children=[
                                                html.H4(translate[lang]["alert_information"]),
                                                html.Div(
                                                    id="alert-camera",
                                                    style={"marginBottom": "10px"},
                                                    children=[
                                                        html.Span(
                                                            id="alert-camera-header", children=translate[lang]["camera"]
                                                        ),
                                                        html.Span(id="alert-camera-value", children=[]),
                                                    ],
                                                ),
                                                html.Div(
                                                    id="alert-location",
                                                    style={"marginBottom": "10px"},
                                                    children=[
                                                        html.Span(
                                                            id="alert-location-header",
                                                            children=translate[lang]["location"],
                                                        ),
                                                        html.Span(id="alert-location-value", children=[]),
                                                    ],
                                                ),
                                                html.Div(
                                                    id="alert-azimuth",
                                                    style={"marginBottom": "10px"},
                                                    children=[
                                                        html.Span(
                                                            id="alert-azimuth-header",
                                                            children=translate[lang]["detection_azimuth"],
                                                        ),
                                                        html.Span(id="alert-azimuth-value", children=[]),
                                                    ],
                                                ),
                                                html.Div(
                                                    id="alert-date",
                                                    children=[
                                                        html.Span(
                                                            id="alert-date-header", children=translate[lang]["date"]
                                                        ),
                                                        html.Span(id="alert-date-value", children=[]),
                                                    ],
                                                ),
                                            ],
                                        ),
                                    ],
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
                    dbc.ModalHeader(translate[lang]["map"]),
                    dbc.ModalBody(
                        build_alerts_map(api_cameras, id_suffix="-md"),
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
