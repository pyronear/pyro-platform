# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_bootstrap_components as dbc
from dash import dcc, html

from utils.display import build_alerts_map


def create_event_list(sequence_list_container_id):
    """
    Creates a container for the alert list with a fixed height and scrollable content.

    This function generates a Dash HTML Div element containing a header and an empty container.
    The empty container ('sequence-list-container') is meant to be populated with alert buttons
    dynamically via a callback. The container has a fixed height and is scrollable, allowing
    users to browse through a potentially long list of alerts.

    Returns:
    - dash.html.Div: A Div element containing the header and the empty container for alert buttons.
    """
    # Set a fixed height for the alert list container and enable scrolling
    event_list_style = {
        "height": "calc(100vh - 120px)",  # Adjust the height as required
        "overflowY": "scroll",  # Enable vertical scrolling
        "padding-right": "10px",  # Prevent scroll bar from touching alerts list
    }

    return html.Div(
        [
            html.Div(id=sequence_list_container_id, style=event_list_style, children=[]),  # Empty container
        ]
    )


def alert_layout(api_cameras, translate, lang, id_suffix=""):
    """
    Creates a container for the alert section, used in both the homepage and the history page

    This function generates a Dash Bootstrap Container that includes various UI components such as images,
    bounding boxes, buttons, sliders, and alert information.

    Parameters:
    - api_cameras (dict): TTTTT A dictionary containing camera information, used for generating alert maps.
    - translate (dict): A dictionary for language translations
    - lang (str): The current language code used for translations.
    - id_suffix (str, optional): A suffix added to the IDs of HTML elements, allowing differentiation
      between different instances of the alert layout (default is an empty string "").

    Returns:
    - dbc.Container: A Dash Bootstrap Container component that holds the entire alert layout.

    The layout includes:
    - A sequence list container to navigate through alert events.
    - A main image display with bounding boxes overlayed for object detection.
    - Control buttons such as play/pause, a slider for image navigation, and a button to toggle bounding boxes.
    - Download and acknowledge alert buttons.
    - Optionnaly, a modal confirmation window for alert acknowledgment.
    - A section displaying detailed alert information (camera, location, azimuth, date, etc.).
    - A map visualization for alert locations.
    - A modal window for a larger map display.
    """
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col([create_event_list(f"sequence-list-container{id_suffix}")], width=2, className="mb-4"),
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
                                                        id=f"main-image{id_suffix}",
                                                        src=translate[lang]["no_alert_default_image"],
                                                        className="zoomable-image",
                                                        style={"maxWidth": "100%", "height": "auto"},
                                                    )
                                                ],
                                            ),
                                            html.Div(
                                                id=f"bbox-container{id_suffix}",
                                                style={
                                                    "display": "block",
                                                    "position": "absolute",
                                                    "top": "0",
                                                    "left": "0",
                                                    "width": "100%",
                                                    "height": "100%",
                                                },
                                                children=[
                                                    html.Div(id=f"bbox-0{id_suffix}", style={"display": "none"}),
                                                    html.Div(id=f"bbox-1{id_suffix}", style={"display": "none"}),
                                                    html.Div(id=f"bbox-2{id_suffix}", style={"display": "none"}),
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
                                            id=f"auto-move-button{id_suffix}",
                                            n_clicks=1,
                                            style={"height": "100%", "width": "100%", "border": "0"},
                                        ),
                                        width=1,
                                    ),
                                    dbc.Col(
                                        html.Div(
                                            dcc.Slider(id=f"image-slider{id_suffix}", min=0, max=10, step=1, value=0),
                                            id=f"slider-container{id_suffix}",
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
                                            id=f"hide-bbox-button{id_suffix}",
                                            n_clicks=0,
                                            className="btn-uniform",
                                            style={},
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
                                            id=f"download-link{id_suffix}",
                                            download="",
                                            href="",
                                            target="_blank",
                                        ),
                                        width=3,
                                    ),
                                    (
                                        dbc.Col(
                                            dbc.Button(
                                                translate[lang]["acknowledge_alert"],
                                                id="acknowledge-button",
                                                n_clicks=0,
                                                className="btn-uniform",
                                            ),
                                            width=3,
                                        )
                                        if id_suffix != "-history"
                                        else None
                                    ),
                                ],
                                className="mb-4",
                                style={"display": "flex", "marginTop": "10px", "justify-content": "space-evenly"},
                            ),
                            (
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
                                                    translate[lang]["confirmation_modal_title"],
                                                    style={
                                                        "margin-bottom": "20px",
                                                        "font-size": "20px",
                                                        "font-weight": "bold",
                                                    },
                                                ),
                                                html.Div(
                                                    [
                                                        html.Button(
                                                            translate[lang]["confirmation_modal_yes"],
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
                                                            translate[lang]["confirmation_modal_no"],
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
                                                            translate[lang]["confirmation_modal_cancel"],
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
                                )
                                if id_suffix != "-history"
                                else None
                            ),
                        ],
                        width=8,
                        style={"padding": "0"},
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                html.Div(
                                    id=f"alert-information{id_suffix}",
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
                                                            id=f"alert-camera-value{id_suffix}",
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
                                                            id=f"camera-location-value{id_suffix}",
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
                                                            id=f"alert-azimuth-value{id_suffix}",
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
                                                            id=f"alert-date-value{id_suffix}",
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
                                    build_alerts_map(api_cameras, id_suffix=id_suffix),
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
            dcc.Interval(id=f"auto-slider-update{id_suffix}", interval=500, n_intervals=0),
            dbc.Modal(
                [
                    dbc.ModalHeader(translate[lang]["map"]),
                    dbc.ModalBody(
                        build_alerts_map(api_cameras, id_suffix=f"-md{id_suffix}"),
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
