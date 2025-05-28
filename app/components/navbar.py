# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import dcc, html

pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"


def Navbar(lang="fr"):
    navbar = dbc.Navbar(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.A(
                            html.Img(src=pyro_logo, height="30px"),
                            href="/",
                        ),
                        width=3,
                    ),
                ],
                align="center",
            ),
            html.Div(
                className="ml-auto",
                style={
                    "display": "flex",
                    "flexDirection": "row",
                    "gap": "10px",
                    "marginRight": "10px",
                },
                children=[
                    # 🔔 Home Alerte
                    dbc.Button(
                        id="home-button",
                        children=["🔔 ", html.Span(id="home_button_text")],
                        href="/",
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 🎥 Live Stream
                    dbc.Button(
                        id="live-stream-button",
                        children=["🎥 ", html.Span(id="live_stream_button_text")],
                        href="/live-stream",
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 📅 Date Picker
                    dbc.Button(
                        id="open-datepicker-modal",
                        children=["📅 ", html.Span(id="datepicker_button_text")],
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 📷 Camera Status
                    dbc.Button(
                        id="camera-status-button",
                        children=["📷 ", html.Span(id="camera_status_button_text")],
                        href="/cameras-status",
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 🚨 Alarm
                    dbc.Button(
                        id="alarm-status-button",
                        children=["🚨 ", html.Span(id="blinking_alarm_button_text")],
                        href="/blinking-alarm",
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 🌐 Langues
                    dcc.Dropdown(
                        id="language-selector",
                        options=[
                            {"label": "🇫🇷 Français", "value": "fr"},
                            {"label": "🇪🇸 Español", "value": "es"},
                            {"label": "🇬🇧 English", "value": "en"},
                        ],
                        value="fr",  # valeur initiale par défaut
                        clearable=False,
                        style={"width": "150px"},
                    ),
                ],
            ),
        ],
        id="main_navbar",
        color="#044448",
        dark=True,
        style={"display": "flex", "justify-content": "space-between"},
    )

    datepicker_modal = dbc.Modal(
        [
            dbc.ModalHeader("Sélectionnez une date" if lang == "fr" else "Seleccione una fecha"),
            dbc.ModalBody(dcc.DatePickerSingle(id="my-date-picker-single")),
            dbc.ModalFooter(
                dbc.Button("Fermer" if lang == "fr" else "Cerrar", id="close-datepicker-modal", className="ml-auto")
            ),
        ],
        id="datepicker-modal",
        is_open=False,
        centered=True,
    )

    return html.Div([navbar, datepicker_modal])
