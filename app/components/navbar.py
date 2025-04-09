# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_bootstrap_components as dbc
from dash import html

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
                style={"display": "flex", "flexDirection": "row", "gap": "10px", "marginRight": "10px"},
                children=[
                    # Camera Status Button
                    dbc.Button(
                        html.Div(
                            [
                                html.Img(
                                    src="assets/images/camera.svg",
                                    style={"width": "20px", "height": "20px", "marginRight": "5px"},
                                ),
                                html.P(children=[], style={"margin": "0"}, id="camera_status_button_text"),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        href="/cameras-status",
                        outline=True,
                        className="navbar-button",
                    ),
                    # Blinking Alarm Button
                    dbc.Button(
                        html.Div(
                            [
                                html.Img(
                                    src="assets/images/alarm.svg",
                                    style={"width": "20px", "height": "20px", "marginRight": "5px"},
                                ),
                                html.P(children=[], style={"margin": "0"}, id="blinking_alarm_button_text"),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        href="/blinking-alarm",
                        outline=True,
                        className="navbar-button",
                    ),
                    # Language Buttons
                    dbc.Button(["🇫🇷", " FR"], id="btn-fr", color="light", className="mr-2"),
                    dbc.Button(["🇪🇸", " ES"], id="btn-es", color="light"),
                ],
            ),
        ],
        id="main_navbar",
        color="#044448",
        dark=True,
        style={"display": "flex", "justify-content": "space-between"},
    )

    return navbar
