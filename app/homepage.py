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

# Importing alerts map and layer style button from alerts.py
from alerts import build_alerts_map, build_layer_style_button

# Importing risks map opacity slider from risks.py
from risks import build_risks_map, build_opacity_slider

# Importing plotly fig objects from graphs.py
from graphs import generate_meteo_fig


# ------------------------------------------------------------------------------
# Before moving to the app layout

# The following block is used to determine what map styles (risks or alerts) we use for and enable the user to change it
# This function creates the button that allows users to change the map style
def build_map_style_button():

    button = html.Button(children='Afficher les niveaux de risques',
                         id='map_style_button')

    return html.Center(button)


# This function takes as input the number of clicks on the button defined above and returns the layer style to use
def choose_map_style(n_clicks):

    # Because we start with the alerts map, if the number of clicks is even, this means that
    # we are still using the alerts map and we may want to switch to the risks one
    if n_clicks % 2 == 0:
        button_content_map = 'Afficher les niveaux de risques'
        map_object = build_alerts_map()
        slider = ' '

    # If the number of clicks is odd, this means we are using the risks map and may
    # want to come back to alerts one
    else:
        button_content_map = 'Revenir à la carte Alertes'
        map_object = build_risks_map()
        slider = build_opacity_slider()

    return button_content_map, map_object, slider


# This function either displays or hides meteo graphs from graphs.py
def meteo_graphs(display=False):
    if display is True:
        return dbc.Row(
            [
                dbc.Col([html.H2("Données météorologiques"), dcc.Graph(figure=meteo_fig)],
                        md=4),
                dbc.Col([html.H2("another indicator"),
                        dcc.Graph(figure={"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}]})],
                        md=4),
                dbc.Col([html.H2("a third indicator"),
                        dcc.Graph(figure={"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}]})],
                        md=4),
            ])
    else:
        return ''


# ------------------------------------------------------------------------------
# Content and App layout

# Instantiating the alerts map object from alerts.py and setting it as the default map object:
map_object = build_alerts_map()

# Instantiating fig objects from graphs.py functions
meteo_fig = generate_meteo_fig()

# Instantiating navbar object from navbar.py
nav = Navbar()

# Instantiating map layers button object from alerts.py
map_layers_button = build_layer_style_button()

# Instantiating map style button object
map_style_button = build_map_style_button()

# Instantiating meteo graphs, set to True to display them under the map, False to hide them
meteo_graphs = meteo_graphs(display=False)

# Body container
body = dbc.Container([
    dbc.Row(
        [dbc.Col(html.H1('Plateforme de Monitoring', style={'text-align': 'center'}), className="pt-4"),
         ]),
    dbc.Row(
        [
            dbc.Col(
                dcc.Dropdown(
                    id='user_department_input',
                    options=[
                        {'label': 'Ardèche', 'value': 'Ardèche'},
                        {'label': 'Gard', 'value': 'Gard'},
                        {'label': 'Landes', 'value': 'Landes'}],
                    placeholder="Départements"),
                md=3),
        ]
    ),
    dbc.Row(
        [dbc.Col(
            [
                dcc.Markdown('---'),
                # map filters added here
                html.H5(("Filtres Carte"), style={'text-align': 'center'}),
                html.P(map_layers_button),
                dcc.Markdown('---'),
                html.P(map_style_button),
                html.P(id="hp_slider"),
            ],
            md=3),
         dbc.Col(
            # map object added here
            html.Div(map_object, id='hp_map'),
            md=9)]
    ),
    # meteo graphs added here
    meteo_graphs
],
    fluid=True,
)


# Gathering all these elements in a HTML Div and having it returned by the Homepage function
def Homepage():

    layout = html.Div([nav, body])

    return layout
