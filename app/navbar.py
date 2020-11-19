"""The following is dedicated to the navigation bar at the top of the web application.

Its main component is the Navbar function that instantiates the navigation bar.
"""

# ------------------------------------------------------------------------------
# Imports

import dash_bootstrap_components as dbc
import dash_html_components as html

# ------------------------------------------------------------------------------
# Content


# Pyronear Logo
pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"


def Navbar():

    # Dropdown menu
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

    # Logged user info
    user_item = html.Div(
        "SDIS PyroDev",
        id="user-div",
        className="ml-auto flex-nowrap mt-3 mt-md-0",
        style={'color': 'white'})

    # Navbar
    navbar = dbc.Navbar(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=pyro_logo, width="120px")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="http://pyronear.org/",
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
            dbc.Collapse([user_item, dropdown], id="navbar-collapse", navbar=True),
        ],
        color="black",
        dark=True,
    )

    return navbar
