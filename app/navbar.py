"""The following is dedicated to the navigation bar at the top of the web application.

Its main component is the Navbar function that instantiates the navigation bar.
"""

# ------------------------------------------------------------------------------
# Imports

import dash_bootstrap_components as dbc
import dash_html_components as html
from pathlib import Path
import base64

# ------------------------------------------------------------------------------
# Content


# Encoding logo image file
pyro_logo = Path(__file__).parent.joinpath('data', 'pyro_logo.png')
encoded_image = base64.b64encode(open(pyro_logo, 'rb').read())


def Navbar():

    # Dropdown menu
    dropdown = dbc.DropdownMenu(
        children=[
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
        tyle={'color': 'white'})

    # Navbar
    navbar = dbc.Navbar(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src='data:image/png;base64,{}'.format(encoded_image.decode()), width="120px")),
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
