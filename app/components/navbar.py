# Copyright (C) 2020-2023, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import html

pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"


def Navbar():
    # home_button = dbc.NavLink(
    #     children=[
    #         html.Div(
    #             children=[
    #                 html.I(className="mx-auto order-0"),
    #                 html.Span("Accueil"),
    #             ]
    #         )
    #     ],
    #     href="/",
    #     style={"font-size": "15px", "color": "white"},
    #     className="btn btn-warning mr-2",
    # )

    # alert_screen_button = dbc.NavLink(
    #     children=[
    #         html.Div(
    #             children=[
    #                 html.I(className="mx-auto order-0"),
    #                 html.Span("Statut des cameras"),
    #             ]
    #         )
    #     ],
    #     href="device_status",
    #     style={"font-size": "15px", "color": "white"},
    #     className="btn btn-warning",
    # )

    # # Navbar brand text without being a link
    # navbar_brand = dbc.NavbarBrand(
    #     "Surveillez les départs de feux",
    #     className="mx-auto order-0",
    #     style={"color": "white", "align": "center", "justify": "center"},
    # )

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
