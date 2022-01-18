# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following file is dedicated to the navigation bar at the top of the web application.

Its main component is the Navbar function that instantiates the navigation bar.
"""


# ----------------------------------------------------------------------------------------------------------------------
# Imports

import dash_bootstrap_components as dbc
from dash import html


# ----------------------------------------------------------------------------------------------------------------------
# Content

# Pyronear Logo
pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"


def Navbar(dropdown=False):
    """
    This function allows to instantiate the navigation bar at the top of the web-app.

    It takes 'dropdown' as an input, a boolean set by default to False, which indicates
    whether to include or not in the navigation bar a Dropdown menu. For now, such a
    menu is not used but it could be reactivated for other purposes such as the log in.

    The returned 'navbar' object is an instantiation of the class dbc.Navbar.
    """

    # Dropdown menu
    if dropdown is True:
        dropdown = dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Page d'Accueil", href='home'),
                dbc.DropdownMenuItem('Alertes et Infrastructures', href='alerts'),
                dbc.DropdownMenuItem('Niveaux de Risque', href='risks'),
            ],
            label="Tableaux de bord",
            className="ml-auto flex-nowrap mt-3 mt-md-0 btn-group dropleft",
            color="warning",
            direction="left",
        )
    else:
        dropdown = ""

    # Navbar Title
    user_item = html.Div(
        "Surveillez les départs de feux",
        id="user-div",
        className="mx-auto order-0",
        style={'color': 'white', 'align': 'center', 'justify': 'center'})

    # Alert monitoring screen, to be displayed in CODIS
    alert_screen_button = dbc.NavLink(
        children=[
            html.Div(
                children=[
                    html.I(
                        className="mx-auto order-0",
                    ),
                    html.Span("Ecran de monitoring"),
                ]
            )
        ],
        href="alert_screen",
        style={
            "font-size": "15px",
            "color": "white",
        },
        className="btn btn-warning"
    )

    # Navbar
    navbar = dbc.Navbar(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=pyro_logo, width="120px")),
                    ],
                    align="center",
                    justify="center"
                ),
                href="#",
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse([user_item, dropdown], id="navbar-collapse", navbar=True),
            html.Div(alert_screen_button)
        ],
        id="main_navbar",
        color='#044448',
        dark=True,
        style={'display': 'none'}
    )

    return navbar
