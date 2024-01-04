# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_bootstrap_components as dbc
from dash import html

# Pyronear - Horizontal Logo
pyro_logo = "https://pyronear.org/img/logo_letters.png"


def login_layout():
    """
    This function creates and returns the login page, which opens at the beginning of each session for user authentication.
    """
    return html.Div(
        [
            html.Center(
                [
                    html.Div(style={"height": "10px"}),
                    html.Img(src=pyro_logo, width="30%"),
                    html.Div(style={"height": "30px"}),
                    dbc.Input(
                        id="username_input",
                        type="text",
                        placeholder="UTILISATEUR",
                        style={"width": "250px"},
                        autoFocus=True,
                    ),
                    html.Div(style={"height": "15px"}),  # Spacing
                    dbc.Input(
                        id="password_input",
                        type="password",
                        placeholder="MOT DE PASSE",
                        style={"width": "250px"},
                    ),
                    html.Div(style={"height": "15px"}),  # Spacing
                    dbc.Button(
                        "Connexion",
                        id="send_form_button",
                        color="primary",
                        className="ml-3",
                    ),
                    html.Div(style={"height": "15px"}),  # Spacing
                    # Feedback message area
                    html.Div(id="form_feedback_area"),
                ],
            ),
        ]
    )
