# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import List, TypedDict

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash_extensions import EventListener  # type: ignore
from translations import translate

from utils.display import build_alerts_map


class Option(TypedDict):
    label: str
    value: str


# --- Styles ---
STATUS_BAR_STYLE = {
    "backgroundColor": "black",
    "height": "50px",
    "width": "100%",
    "marginBottom": "8px",
    "marginTop": "-32px",
    "padding": "0",
    "display": "flex",
    "justifyContent": "space-between",
    "alignItems": "center",
}

STREAM_STATUS_STYLE = {
    "color": "white",
    "fontWeight": "bold",
    "fontSize": "16px",
    "paddingLeft": "16px",
    "height": "50px",
    "display": "flex",
    "alignItems": "center",
}

CLOSE_BUTTON_STYLE = {
    "background": "none",
    "border": "1px solid white",
    "color": "white",
    "borderRadius": "8px",
    "padding": "6px 12px",
    "cursor": "pointer",
    "fontSize": "14px",
    "marginRight": "16px",
    "height": "36px",
}

BUTTON_STYLE = {
    "background": "none",
    "border": "none",
    "fontSize": "28px",
    "padding": "0",
    "margin": "0",
    "cursor": "pointer",
}

SLIDER_BOX_STYLE = {
    "border": "2px solid #098386",
    "borderRadius": "10px",
    "padding": "8px",
    "marginBottom": "16px",
}

DROPDOWN_STYLE = {
    "border": "none",
    "borderRadius": "8px",
    "backgroundColor": "white",
    "fontWeight": "bold",
    "width": "100%",
}

WRAPPED_DROPDOWN_STYLE = {
    "border": "2px solid #098386",
    "borderRadius": "10px",
    "marginBottom": "9px",
}

POSE_BUTTONS_STYLE = {
    "display": "flex",
    "flexWrap": "wrap",
    "justifyContent": "center",
    "gap": "8px",
    "marginBottom": "9px",
}

STREAM_PAGE_STYLE = {
    "padding": "0",
    "margin": "0",
    "width": "100%",
    "height": "100%",
}

PICK_STREAM_STYLE = {
    "width": "200px",
    "marginRight": "10px",
    "borderRadius": "6px",
    "fontWeight": "bold",
}


# --- Layout ---
def live_stream_layout(user_token, api_cameras, available_stream, selected_camera_info=None, lang="fr"):
    # Default fallback
    default_stream = next(iter(available_stream.keys()))[0] if available_stream else None

    dropdown_options: List[Option] = []

    if available_stream:
        dropdown_options = [{"label": name, "value": name} for name in available_stream.keys()]

    # Try to derive stream from selected camera info
    if selected_camera_info and available_stream:
        cam_name, _ = selected_camera_info
        site_name = cam_name.lower()
        if site_name in available_stream:
            default_stream = site_name

    return html.Div(
        [
            # Status bar
            html.Div(
                [
                    html.Div(id="stream-status", style=STREAM_STATUS_STYLE),
                    html.Div(
                        [  # GROUPED RIGHT SECTION
                            dcc.Dropdown(
                                id="available-stream-sites-dropdown",
                                placeholder=translate("select_stream", lang),
                                value=default_stream,
                                options=dropdown_options if available_stream else [],  # type: ignore[arg-type]
                                style=PICK_STREAM_STYLE,
                            ),
                            html.Div(
                                html.Button(
                                    translate("capture_image", lang),
                                    id="capture-image-button",
                                    n_clicks=0,
                                    className="btn btn-primary",
                                ),
                                style={"textAlign": "center"},
                            ),
                        ],
                        style={"display": "flex", "alignItems": "center", "gap": "8px", "marginRight": "16px"},
                    ),
                ],
                style=STATUS_BAR_STYLE,
            ),
            # Main layout: stream + map
            html.Div(
                dbc.Row(
                    [
                        # LEFT COLUMN: Stream + Controls
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Iframe(
                                                    id="video-stream",
                                                    src="",
                                                    style={
                                                        "position": "absolute",
                                                        "top": "0",
                                                        "left": "0",
                                                        "width": "100%",
                                                        "height": "100%",
                                                        "border": "none",
                                                        "borderRadius": "10px",
                                                    },
                                                ),
                                                EventListener(
                                                    id="click-listener",
                                                    children=html.Div(
                                                        id="click-overlay",
                                                        n_clicks=0,
                                                        style={
                                                            "position": "absolute",
                                                            "top": 0,
                                                            "left": 0,
                                                            "width": "100%",
                                                            "height": "100%",
                                                            "zIndex": 2,
                                                            "cursor": "crosshair",
                                                            "backgroundColor": "rgba(255, 255, 255, 0.01)",
                                                        },
                                                    ),
                                                    events=[{"event": "pointerdown"}],
                                                ),
                                                html.Div(
                                                    [
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(),
                                                                dbc.Col(
                                                                    html.Button(
                                                                        "⬆️",
                                                                        id="move-up",
                                                                        n_clicks=0,
                                                                        style=BUTTON_STYLE,
                                                                    )
                                                                ),
                                                                dbc.Col(),
                                                            ],
                                                            justify="center",
                                                        ),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(
                                                                    html.Button(
                                                                        "⬅️",
                                                                        id="move-left",
                                                                        n_clicks=0,
                                                                        style=BUTTON_STYLE,
                                                                    )
                                                                ),
                                                                dbc.Col(
                                                                    html.Button(
                                                                        "🛑",
                                                                        id="stop-move",
                                                                        n_clicks=0,
                                                                        style=BUTTON_STYLE,
                                                                    )
                                                                ),
                                                                dbc.Col(
                                                                    html.Button(
                                                                        "➡️",
                                                                        id="move-right",
                                                                        n_clicks=0,
                                                                        style=BUTTON_STYLE,
                                                                    )
                                                                ),
                                                            ],
                                                            justify="center",
                                                        ),
                                                        dbc.Row(
                                                            [
                                                                dbc.Col(),
                                                                dbc.Col(
                                                                    html.Button(
                                                                        "⬇️",
                                                                        id="move-down",
                                                                        n_clicks=0,
                                                                        style=BUTTON_STYLE,
                                                                    )
                                                                ),
                                                                dbc.Col(),
                                                            ],
                                                            justify="center",
                                                        ),
                                                    ],
                                                    style={
                                                        "position": "absolute",
                                                        "bottom": "10px",
                                                        "right": "10px",
                                                        "padding": "5px",
                                                        "borderRadius": "8px",
                                                        "zIndex": 3,
                                                    },
                                                ),
                                            ],
                                            style={
                                                "position": "relative",
                                                "width": "100%",
                                                "paddingBottom": "56.25%",  # 16:9 aspect ratio
                                                "borderRadius": "10px",
                                                "boxShadow": "0 0 8px rgba(0,0,0,0.2)",
                                                "overflow": "hidden",
                                            },
                                        ),
                                    ],
                                    style={
                                        "width": "100%",
                                        "maxWidth": "1000px",  # Optional: limit max width for large screens
                                        "margin": "auto",
                                    },
                                ),
                                # Sliders
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            html.Div(
                                                [
                                                    html.Div(
                                                        translate("move_speed", lang),
                                                        style={
                                                            "textAlign": "center",
                                                            "fontWeight": "bold",
                                                            "marginBottom": "8px",
                                                        },
                                                    ),
                                                    dcc.Slider(
                                                        id="speed-input",
                                                        min=0,
                                                        max=100,
                                                        step=10,
                                                        value=0,
                                                        marks={i: str(i) for i in range(0, 101, 10)},
                                                    ),
                                                ],
                                                style=SLIDER_BOX_STYLE,
                                            ),
                                            width=6,
                                        ),
                                        dbc.Col(
                                            html.Div(
                                                [
                                                    html.Div(
                                                        translate("zoom_level", lang),
                                                        style={
                                                            "textAlign": "center",
                                                            "fontWeight": "bold",
                                                            "marginBottom": "8px",
                                                        },
                                                    ),
                                                    dcc.Slider(
                                                        id="zoom-input",
                                                        min=0,
                                                        max=100,
                                                        step=10,
                                                        value=0,
                                                        marks={i: str(i) for i in range(0, 101, 10)},
                                                    ),
                                                ],
                                                style=SLIDER_BOX_STYLE,
                                            ),
                                            width=6,
                                        ),
                                    ],
                                    className="mt-3",
                                ),
                            ],
                            md=8,
                            style={"padding": "0"},
                        ),
                        # RIGHT COLUMN: Dropdown + map
                        dbc.Col(
                            [  # Panneau affichage des infos caméra
                                html.Div(
                                    id="stream-camera-info-panel",
                                    className="common-style",
                                    style={
                                        "padding": "12px",
                                        "marginTop": "0px",
                                        "marginBottom": "10px",
                                        "backgroundColor": "#f0f4f7",
                                        "borderRadius": "8px",
                                    },
                                    children=[
                                        html.H5(
                                            translate("camera_info", lang),
                                            style={"textAlign": "center", "marginBottom": "12px"},
                                        ),
                                        html.Div(
                                            [
                                                html.Span(
                                                    translate("camera_name", lang), className="alert-information-title"
                                                ),
                                                html.Span(id="stream-camera-name"),
                                            ],
                                            style={"marginBottom": "8px"},
                                        ),
                                        html.Div(
                                            [
                                                html.Span(
                                                    translate("current_azimuth", lang),
                                                    className="alert-information-title",
                                                ),
                                                dcc.Input(
                                                    id="stream-current-azimuth",
                                                    type="number",
                                                    min=0,
                                                    max=359,
                                                    step=1,
                                                    placeholder="0-359",
                                                    debounce=True,
                                                    style={"width": "80px", "marginLeft": "8px", "borderRadius": "6px"},
                                                ),
                                            ],
                                            style={"marginBottom": "12px", "display": "flex", "alignItems": "center"},
                                        ),
                                        html.Div(
                                            [
                                                html.Span(
                                                    translate("preset_azimuths", lang),
                                                    className="alert-information-title",
                                                ),
                                                html.Span(id="stream-preset-azimuths", style={"marginLeft": "8px"}),
                                            ],
                                            style={"marginBottom": "8px", "display": "flex", "alignItems": "center"},
                                        ),
                                    ],
                                ),
                                # Map
                                html.Div(
                                    [
                                        html.Div(
                                            build_alerts_map(api_cameras, id_suffix="-stream"),
                                            style={
                                                "position": "absolute",
                                                "top": "0",
                                                "left": "0",
                                                "width": "100%",
                                                "height": "100%",
                                            },
                                        )
                                    ],
                                    style={
                                        "position": "relative",
                                        "width": "100%",
                                        "paddingBottom": "100%",
                                        "borderRadius": "10px",
                                        "overflow": "hidden",
                                        "boxShadow": "0 0 8px rgba(0,0,0,0.2)",
                                    },
                                    className="common-style",
                                ),
                            ],
                            md=4,
                            style={"padding": "0", "paddingLeft": "16px"},
                        ),
                    ],
                    className="mb-4",
                ),
                style={"paddingLeft": "20px", "paddingRight": "20px"},
            ),
            # Hidden components
            # Modal for image preview
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(translate("image_preview_title", lang))),
                    dbc.ModalBody(
                        html.Img(id="captured-image", src="", style={"width": "100%", "borderRadius": "8px"})
                    ),
                    dbc.ModalFooter(
                        html.A(
                            translate("download_image_button", lang),
                            id="download-captured-image",
                            download="capture.jpg",
                            href="",
                            target="_blank",
                            className="btn btn-success",
                        ),
                    ),
                ],
                id="capture-modal",
                is_open=False,
                fullscreen=True,
            ),
            dcc.Interval(id="stream-timer", interval=1000, n_intervals=0),  # every second
            dcc.Store(id="stream-start-time"),
            dcc.Store(id="detection-status", data="running"),  # or "stopped", etc.
            html.Div(id="dummy-output", style={"display": "none"}),
            html.Div(id="dummy-output2", style={"display": "none"}),
            dcc.Store(id="pi_api_url"),
            dcc.Store(id="pi_cameras"),
            dcc.Store(id="current_camera"),
            dcc.Store(id="trigered_from_alert", data=True if available_stream else False),
            dcc.Store(id="hide-stream-flag", data=False),
            dcc.Store(id="click-coords"),
            dcc.Store(id="click-coords2"),
            dbc.Modal(
                id="inactivity-modal",
                is_open=False,
                centered=True,
                children=[
                    dbc.ModalHeader(translate("auto_end_modal_title", lang)),
                    dbc.ModalBody(translate("auto_end_modal_body", lang)),
                ],
            ),
            dcc.Store(id="hide-stream-flag", data=False),
        ],
        style=STREAM_PAGE_STYLE,
    )
