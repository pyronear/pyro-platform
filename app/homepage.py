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


#This function returns the user selection area in the left side bar
def user_selection_area():
    """Summary : Define the components of the user selection area (left side bar)

    Desc: This function return the basic dash component of the the left side bar
    of the monitoring platform and has been create because it used several time in app.

    Parameters:
    None

    Returns:
    html dash components: A set of components that composed the left side bar of the app
    """
    return [dcc.Markdown('---'),
            html.H5(("Filtres Carte"), style={'text-align': 'center'}),  # map filters added here
            html.P(map_layers_button),
            dcc.Markdown('---'),
            html.P(map_style_button),
            html.P(id="hp_slider"),
            html.P(id="hp_video")
            ]


# This function either displays video of selected markers
def show_camera_video(feature=None):
    """Summary : Return video of the selected marker

    Desc : This function return the video of the marker and put it into the left side bar
    of the monitoring platform

    Parameters:
    Feature (geojson children): Number of clicks the marker has received

    Returns:
    html dash components: A default video for now (later, the real video / picture of the marker)
    """
    video_style = {'width': '50vh',
                   'height': '40vh',
                   'margin': 'auto',
                   'display': 'block'
                   }
    if feature is not None:
        separator = dcc.Markdown('---')
        video_title = html.H5("Camera selectionnée", style={'text-align': 'center'})
        video_html = html.Video(id='Video_Camera',
                                src='https://media.giphy.com/media/l2JeaPjeaR9DvDWXS/giphy.mp4',
                                style=video_style,
                                controls=True)

        video_div = html.Div(style=video_style,
                             children=[separator, video_title, video_html]
                             )
        return html.Center(video_div)
    return ' '


# This function either displays or hides meteo graphs from graphs.py
def meteo_graphs(display=False):
    if display is True:
        return dbc.Row(
            [
                # In the following line, we instantiate the Plotly Graph Objects figure storing the graphs
                dbc.Col([html.H2("Données météorologiques"), dcc.Graph(figure=generate_meteo_fig())],
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
# The following function is used in the main.py file to instantiate the layout of the homepage

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
            #side bar for the user to apply filter
            user_selection_area(),
            id='user_selection_column',
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
                    md=3)
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    user_selection_area(),
                    id='user_selection_column',
                    md=3),
                dbc.Col(
                    # map object added here
                    html.Div(build_alerts_map(), id='hp_map'),
                    md=9)
            ]
        ),
        # meteo graphs added here
        meteo_graphs(display=False)
    ],
        fluid=True,
    )
    # Instantiating navbar object from navbar.py
    layout = html.Div([Navbar(), body])
    return layout
