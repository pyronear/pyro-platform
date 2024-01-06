# Copyright (C) 2023-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import html

pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"


def Navbar():
    buttons_container = html.Div(
        # children=[home_button, alert_screen_button],
        className="ml-auto",
        style={"display": "flex"},
    )

    navbar = dbc.Navbar(
        [
            dbc.Row(
                [
                    dbc.Col(html.Img(src=pyro_logo, height="30px"), width=3),
                ],
                align="center",
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse(buttons_container, id="navbar-collapse", navbar=True),
        ],
        id="main_navbar",
        color="#044448",
        dark=True,
        className="mb-4",
    )

    return navbar
