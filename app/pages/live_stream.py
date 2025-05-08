# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash import dcc, html

from utils.display import build_vision_polygon

# Constants
site_lat = 48.426746125557
site_lon = 2.71087590966019
azimuth = 0
opening_angle = 54
dist_km = 15

# --- Styles ---
STATUS_BAR_STYLE = {
    "backgroundColor": "black",
    "height": "50px",
    "width": "100%",
    "marginBottom": "8px",
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

translate = {
    "fr": {
        "close_doubt": "Fermer la levée de doute",
        "move_speed": "Vitesse de déplacement",
        "zoom_level": "Niveau de zoom",
        "start": "▶️ Démarrer",
        "stop": "⏹️ Arrêter",
        "select_stream": "🎥 Sélectionner un flux",
    },
    "es": {
        "close_doubt": "Cerrar verificación visual",
        "move_speed": "Velocidad de movimiento",
        "zoom_level": "Nivel de zoom",
        "start": "▶️ Iniciar",
        "stop": "⏹️ Detener",
        "select_stream": "🎥 Seleccionar flujo",
    },
}



# --- Layout ---
def live_stream_layout(user_token, api_cameras, available_stream, selected_camera_info=None, lang="fr"):
    # Default fallback
    default_stream = list(available_stream.keys())[0] if available_stream else None

    # Try to derive stream from selected camera info
    if selected_camera_info and available_stream:
        cam_name, _ = selected_camera_info
        site_name = cam_name[:-3].strip().lower()
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
                        id="available-stream-dropdown",
                        placeholder=translate[lang]["select_stream"],
                        value=default_stream,
                        options=[
                            {"label": name, "value": name}
                            for name in available_stream.keys()
                        ] if available_stream else [],
                        style=PICK_STREAM_STYLE,
                    ),
                    html.Button(
                        translate[lang]["close_doubt"],
                        id="close-doubt",
                        n_clicks=0,
                        style=CLOSE_BUTTON_STYLE,
                    ),
                ],
                style={"display": "flex", "alignItems": "center", "gap": "8px", "marginRight": "16px"},
            ),
        ],
        style=STATUS_BAR_STYLE,
    ),

            # Main layout: stream + map
            dbc.Row(
                [
                    # LEFT COLUMN: Stream + Controls
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Iframe(
                                        id="video-stream",
                                        src="",
                                        style={
                                            "width": "100%",
                                            "height": "500px",
                                            "border": "none",
                                            "borderRadius": "10px",
                                        },
                                    ),
                                    # Joystick
                                    html.Div(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(),
                                                    dbc.Col(
                                                        html.Button("⬆️", id="move-up", n_clicks=0, style=BUTTON_STYLE)
                                                    ),
                                                    dbc.Col(),
                                                ],
                                                justify="center",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        html.Button("⬅️", id="move-left", n_clicks=0, style=BUTTON_STYLE)
                                                    ),
                                                    dbc.Col(
                                                        html.Button(
                                                            "🛑", id="stop-move", n_clicks=0, style=BUTTON_STYLE
                                                        )
                                                    ),
                                                    dbc.Col(
                                                        html.Button(
                                                            "➡️", id="move-right", n_clicks=0, style=BUTTON_STYLE
                                                        )
                                                    ),
                                                ],
                                                justify="center",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(),
                                                    dbc.Col(
                                                        html.Button("⬇️", id="move-down", n_clicks=0, style=BUTTON_STYLE)
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
                                        },
                                    ),
                                ],
                                style={"position": "relative"},
                            ),
                            # Sliders
                            dbc.Row(
                                [
                                    dbc.Col(
                                        html.Div(
                                            [
                                                html.Div(
                                                    translate[lang]["move_speed"],
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
                                                    translate[lang]["zoom_level"],
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
                        [
                            html.Div(
                                dcc.Dropdown(
                                    id="camera-select",
                                    options=[],
                                    value=None,
                                    clearable=False,
                                    className="mb-2",
                                    style=DROPDOWN_STYLE,
                                ),
                                style=WRAPPED_DROPDOWN_STYLE,
                            ),
                            # Start/Stop
                            dbc.Row(
                                [
                                    dbc.Col(
                                        html.Button(
                                            translate[lang]["start"],
                                            id="start-stream",
                                            n_clicks=0,
                                            style={
                                                **BUTTON_STYLE,
                                                "border": "2px solid #098386",
                                                "borderRadius": "8px",
                                                "fontSize": "18px",
                                                "width": "100%",
                                                "color": "#098386",
                                            },
                                        ),
                                        width=6,
                                    ),
                                    dbc.Col(
                                        html.Button(
                                            translate[lang]["stop"],
                                            id="stop-stream",
                                            n_clicks=0,
                                            style={
                                                **BUTTON_STYLE,
                                                "border": "2px solid #098386",
                                                "borderRadius": "8px",
                                                "fontSize": "18px",
                                                "width": "100%",
                                                "color": "#098386",
                                            },
                                        ),
                                        width=6,
                                    ),
                                ],
                                justify="center",
                                className="mb-2",
                            ),
                            # Pose buttons
                            html.Div(id="pose-buttons", style=POSE_BUTTONS_STYLE),
                            # Map
                            dl.Map(
                                center=[site_lat, site_lon],
                                zoom=10,
                                children=[
                                    dl.TileLayer(),
                                    dl.LayerGroup(
                                        id="vision-layer",
                                        children=[
                                            build_vision_polygon(site_lat, site_lon, azimuth, opening_angle, dist_km)[0]
                                        ],
                                    ),
                                    dl.Marker(position=[site_lat, site_lon]),
                                ],
                                style={"width": "100%", "height": "350px", "borderRadius": "10px"},
                            ),
                        ],
                        md=4,
                        style={"padding": "0", "paddingLeft": "16px"},
                    ),
                ],
                className="mb-4",
            ),
            # Hidden components
            dcc.Interval(id="stream-timer", interval=1000, n_intervals=0, disabled=True),
            dcc.Store(id="detection-status", data="stopped"),
            html.Div(id="dummy-output", style={"display": "none"})
        ],
        style=STREAM_PAGE_STYLE,
    )
