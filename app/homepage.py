"""The following is dedicated to the homepage.

The main item is the HomePage function that returns the corresponding page layout.
"""

# ------------------------------------------------------------------------------
# Imports

# Various modules provided by Dash to build the page layout
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

# From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

# Didn't know what to put as a basic map here, so I just implemented the alert map
from alerts import build_alerts_map

# importing plotly fig objects from graphs.py
from graphs import generate_meteo_fig


# ------------------------------------------------------------------------------
# Content (NB: not modified from the tutorial)

# instantiating the map object from alerts.py: to be modified depending on
# what we expect the user to view first on homepage
map_object = build_alerts_map()

# instantiating fig objects from graphs.py functions
meteo_fig = generate_meteo_fig()

nav = Navbar()

body = dbc.Container(
    [
    dbc.Row(
        [dbc.Col(html.H1('Bienvenue sur Pyronear')),
        dbc.Col(dcc.Dropdown(id='user_department_input',
                            options=[
                            {'label': 'Ardèche', 'value': 'Ardèche'},
                            {'label': 'Gard', 'value': 'Gard'},
                            {'label': 'Landes', 'value': 'Landes'}
                            ]))
        ]),
    dbc.Row(
        [dbc.Col(
            [html.H2('Description du projet'),
             html.P(("Cette application a pour but de fournir un outil facilitant l'action"
                     "des pompiers dans leur lutte contre les incendies."
                     "L'outil repose sur des images vidéos prises depuis des tours de guêt."
                     "En plus des alertes incendies, cette application s'appuie également sur un"
                     "ensemble de données météorologiques, topographiques, géographiques, pour"
                     "fournir une évaluation du niveau de risque associé à une zone géographique pour un temps donné.")),
            ],
            md=12)]),
    dbc.Row(
        [dbc.Col(
            # add the slider + map options here
            html.P(("Ici vient s'ajouter le slider et les options pour reliefs, vue sat, ...")),
            md=4),
        dbc.Col([
            # add the map here
            html.Div(map_object)
            ],
            md=8)]),
    dbc.Row(
        [dbc.Col([html.H2("Données météorologiques"),
                dcc.Graph(figure=meteo_fig)
            ],
            md=4),
        dbc.Col([html.H2("another indicator"),
                dcc.Graph(figure={"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}]})
            ],
            md=4),
        dbc.Col([html.H2("a third indicator"),
                dcc.Graph(figure={"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}]})
            ],
            md=4)
        ])
     ],
    className="mt-4")


def Homepage():

    layout = html.Div([nav, body])

    return layout
