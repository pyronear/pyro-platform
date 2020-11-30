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

# Importing utils fetched API data
from utils import build_live_alerts_metadata


# ------------------------------------------------------------------------------
# Before moving to the app layout

#Fetching reusable alert metadata
alert_metadata = build_live_alerts_metadata()
if alert_metadata:
    frame_url = alert_metadata["media_url"]


# This function creates a radio button in order to simulate an alert event that will be later catched through the API
def build_alert_radio_button():

    alert_radio_button = dcc.RadioItems(
        options=[
            {'label': 'no alert', 'value': 1},
            {'label': 'alert', 'value': 0},
        ],
        value=1,
        labelStyle={'display': 'inline-block'},
        id='alert_radio_button'
    )

    return alert_radio_button


# The following block is used to determine which map styles (risks or alerts) we use and enable the user to change it
# This function creates the button that allows users to change the map style
def build_map_style_button():

    button = html.Button(children='Afficher les niveaux de risques',
                         id='map_style_button',
                         className='btn btn-warning')

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

    return [build_alert_radio_button(),
            dcc.Markdown('---'),
            html.H5(("Filtres Carte"), style={'text-align': 'center'}),  # Map filters added here
            html.P(build_layer_style_button()),                          # Changes layer view style btn
            dcc.Markdown('---'),
            html.P(build_map_style_button()),                            # Changes map style btn
            html.P(id="hp_slider"),                                      # Opacity sliders for risks map
            html.P(id="hp_alert_frame_metadata")                         # Displays alert_frame and alert_metadata
            ]


# Displays alert_frame and metadata related to a specific alert_markers after a click on display_alert_frame_btn
def display_alerts_frames(feature=None):

    # Fetching alert status and reusable metadata
    alert_metadata = build_live_alerts_metadata()
    alert_lat = str(alert_metadata["lat"])
    alert_lon = str(alert_metadata["lon"])
    alert_frame = alert_metadata["media_url"]
    alert_device = str(alert_metadata["device_id"])
    alert_site = alert_metadata["site_name"]
    alert_azimuth = alert_metadata["azimuth"]

    frame_style = {'width': '50vh',
                   'height': '35vh',
                   'margin': 'auto',
                   'display': 'block',
                   'text-align': 'center',
                   }

    if feature is not None:
        separator1 = dcc.Markdown('---')
        frame_title = html.H5("Image de détection", style={'text-align': 'center'})
        alert_frame = html.Img(
            id='alert_frame',
            src=frame_url,
            style=frame_style,)
        separator2 = dcc.Markdown('---')
        alert_metadata_title = html.H5("Données de détection", style={'text-align': 'center'})
        alert_metadata = html.Div(
            id="alert_metadata_user_selection",
            children=[
                "Tour: {}".format(alert_site), html.Br(),
                "Coordonnées de la tour: {}, {}".format(alert_lat, alert_lon), html.Br(),
                "Id de caméra: {}".format(alert_device), html.Br(),
                "Azimuth: {}".format(alert_azimuth)])

        alert_frame_metadata = html.Div(
            children=[separator1, frame_title, alert_frame, separator2, alert_metadata_title, alert_metadata])

        return html.Div(alert_frame_metadata)
    return ""


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

# Body container
body = dbc.Container([
    dbc.Row(
        [dbc.Col(html.H1('Plateforme de Monitoring', style={'text-align': 'center'}), className="pt-4"),
         ]),
    dbc.Row(
        [dbc.Col(
            #side bar for the user to apply filter
            user_selection_area(),
            id='user_selection_column',
            md=3),
         dbc.Col(
            # map object added here
            html.Div(build_alerts_map(), id='hp_map'),
            md=9)]
    ),
    # Instantiating meteo graphs, set to True to display them under the map, False to hide them
    meteo_graphs(display=False)
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
            [dbc.Col(id='live_alert_header_btn'),
             ]),
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
