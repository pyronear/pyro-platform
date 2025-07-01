# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import dcc, html
from translations import translate

from components.alerts import create_event_list
from utils.display import build_alerts_map


def homepage_layout(user_token, api_cameras, lang="fr"):
    return dbc.Container(
        [
            dbc.Row([
                dbc.Col([create_event_list()], width=2, className="mb-4"),
                dbc.Col(
                    [
                        html.Div(
                            dcc.Dropdown(
                                id="sequence_dropdown",
                                options=[],  # Populated via callback
                                placeholder="Sélectionner une caméra",
                                style={
                                    "border": "none",
                                    "color": "#c97a00",
                                    "fontWeight": "bold",
                                    "fontSize": "15px",
                                    "background": "transparent",
                                    "boxShadow": "none",
                                    "minWidth": "220px",
                                },
                                className="dropdown-no-arrow",
                            ),
                            id="sequence_dropdown_container",
                            style={
                                "padding": "10px 20px",
                                "borderRadius": "8px",
                                "backgroundColor": "#f5f9f8",
                                "display": "none",  # Default hidden
                            },
                        ),
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
                                                    src=translate("no_alert_default_image", lang),
                                                    className="zoomable-image",
                                                    style={"maxWidth": "100%", "height": "auto"},
                                                )
                                            ],
                                        ),
                                        html.Div(
                                            id="bbox-container",
                                            style={
                                                "display": "block",
                                                "position": "absolute",
                                                "top": "0",
                                                "left": "0",
                                                "width": "100%",
                                                "height": "100%",
                                            },
                                            children=[
                                                html.Div(id="bbox-0", style={"display": "none"}),
                                                html.Div(id="bbox-1", style={"display": "none"}),
                                                html.Div(id="bbox-2", style={"display": "none"}),
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
                                        dcc.Slider(id="image-slider", min=0, max=0, step=1, value=0, marks={}),
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
                                        translate("show_hide_prediction", lang),
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
                                            translate("download_image", lang),
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
                                    dbc.Button(translate("download", lang), id="dl-button", className="btn-uniform"),
                                    width=3,
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        translate("acknowledge_alert", lang),
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
                                            translate("confirmation_modal_title", lang),
                                            style={
                                                "margin-bottom": "20px",
                                                "font-size": "20px",
                                                "font-weight": "bold",
                                            },
                                        ),
                                        html.Div(
                                            [
                                                html.Button(
                                                    translate("confirmation_modal_yes", lang),
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
                                                    translate("confirmation_modal_no", lang),
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
                                                    translate("confirmation_modal_cancel", lang),
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
                                        "border-radius": "8px",
                                        "box-shadow": "0 4px 8px rgba(0, 0, 0, 0.2)",
                                        "max-width": "600px",
                                        "width": "100%",
                                        "text-align": "center",
                                    },
                                ),
                            ],
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
                                                translate("alert_information", lang), style={"text-align": "center"}
                                            ),
                                            html.Div(
                                                id="alert-camera",
                                                children=[
                                                    html.Span(
                                                        id="alert-camera-header",
                                                        children=translate("camera", lang),
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
                                                style={"display": "flex", "alignItems": "center"},
                                                children=[
                                                    html.Span(
                                                        translate("camera_location", lang),
                                                        className="alert-information-title",
                                                        style={"margin-right": "6px"},
                                                    ),
                                                    html.Span(
                                                        id="camera-location-copy-content",
                                                        children="",
                                                        style={"display": "none"},
                                                    ),
                                                    dcc.Clipboard(
                                                        id="clipboard-location",
                                                        target_id="camera-location-copy-content",
                                                        title="Copier",
                                                        style={
                                                            "border": "none",
                                                            "background": "transparent",
                                                            "cursor": "pointer",
                                                        },
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="alert-azimuth",
                                                children=[
                                                    html.Span(
                                                        id="alert-azimuth-header",
                                                        children=translate("detection_azimuth", lang),
                                                        className="alert-information-title",
                                                    ),
                                                    html.Span(
                                                        id="alert-azimuth-value",
                                                        children=[],
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="alert-time-range",
                                                style={"display": "flex", "alignItems": "center", "gap": "16px"},
                                                children=[
                                                    html.Div(
                                                        id="alert-start-date",
                                                        children=[
                                                            html.Span(
                                                                id="alert-start-date-header",
                                                                children=translate("start_time", lang),
                                                                className="alert-information-title",
                                                            ),
                                                            html.Span(
                                                                id="alert-start-date-value",
                                                                children=[],
                                                            ),
                                                        ],
                                                    ),
                                                    html.Div(
                                                        id="alert-end-date",
                                                        children=[
                                                            html.Span(
                                                                id="alert-end-date-header",
                                                                children=translate("end_time", lang),
                                                                className="alert-information-title",
                                                            ),
                                                            html.Span(
                                                                id="alert-end-date-value",
                                                                children=[],
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="smoke-location",
                                                style={
                                                    "display": "flex",
                                                    "alignItems": "center",
                                                    "marginTop": "6px",
                                                },
                                                children=[
                                                    html.Span(
                                                        translate("smoke_location", lang),
                                                        className="alert-information-title",
                                                        style={"margin-right": "6px"},
                                                    ),
                                                    html.Span(
                                                        id="smoke-location-copy-content",
                                                        children="",  # mis à jour par le callback
                                                        style={"display": "none"},
                                                    ),
                                                    dcc.Clipboard(
                                                        id="clipboard-smoke-location",
                                                        target_id="smoke-location-copy-content",
                                                        title="Copier",
                                                        style={
                                                            "border": "none",
                                                            "background": "transparent",
                                                            "cursor": "pointer",
                                                        },
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
                                build_alerts_map(api_cameras),
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
                                translate("enlarge_map", lang),
                                className="common-style",
                                style={"backgroundColor": "#FEBA6A", "color": "black", "width": "100%"},
                                id="map-button",
                            ),
                        ),
                        dbc.Button(id="start-live-stream", color="primary", className="mb-1"),
                        dbc.Button(id="create-occlusion-mask", color="primary", className="mb-1"),
                    ],
                    width=2,
                    style={
                        "display": "flex",
                        "flex-direction": "column",
                        "gap": "16px",
                    },
                ),
            ]),
            dcc.Interval(id="auto-slider-update", interval=500, n_intervals=0),
            dbc.Modal(
                [
                    dbc.ModalHeader(translate("map", lang)),
                    dbc.ModalBody(
                        build_alerts_map(api_cameras, id_suffix="-md"),
                    ),
                ],
                id="map-modal",
                keyboard=False,
                fullscreen=True,
                is_open=False,
            ),
            dcc.Store(id="bbox-store"),
            dbc.Modal(
                id="bbox-modal",
                is_open=False,
                fullscreen=True,
                children=[
                    dbc.ModalHeader(translate("occlusion_modal", lang)),
                    dbc.ModalBody(
                        html.Div(
                            id="bbox-image-container", style={"width": "100%", "height": "100%", "overflow": "hidden"}
                        )
                    ),
                    dbc.ModalFooter([
                        dbc.Button(translate("confirm_bbox", lang), id="confirm-bbox-button", color="primary"),
                        dbc.Button(
                            translate("delete_bbox", lang),
                            id="delete-bbox-button",
                            color="danger",
                            className="ms-2",
                        ),
                    ]),
                ],
            ),
            dcc.Store(id="bbox-store"),
            dbc.Modal(
                id="zip-modal",
                is_open=False,
                centered=True,
                children=[
                    dbc.ModalHeader(id="zip-modal-header", children=translate("archive_ready", lang)),
                    dbc.ModalFooter(
                        html.A(
                            dbc.Button(translate("download", lang), id="confirm-dl-button", color="success"),
                            id="zip-dl-link",
                            href="",
                            download="",
                            target="_blank",
                        )
                    ),
                ],
            ),
        ],
        fluid=True,
    )
