# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following Python file is dedicated to the homepage of the web application.

The main item of this module is the Homepage function that returns the core layout of the web application.

More precisely, after a first block dedicated to imports, the content section is divided between:

- an alert simulation block dedicated to the radio button used in debugging mode to simulate alert events;
- a map style block that allows the user to choose between the "Alerts and Infrastructure" and the "Risk Scores" views;
- a past fires button block, thanks to which the user can choose to display or hide historic fire markers;
- a block dedicated to the user selection area, located in the blank space on the left of the map;
- an alert frame and metadata block which allows to display the detection information on the left of the map;
- a meteo graphs block used to display or hide meteorological indicators below the map;
- an app layout block where the Homepage function is defined.

Most functions defined below are designed to be called in the main.py file.
"""

# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# Various modules provided by Dash to build the page layout
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

# From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

# Importing alerts map builder from alerts.py
from alerts import build_alerts_map

# Importing risks map and opacity slider builders from risks.py
from risks import build_risks_map, build_opacity_slider

# Importing plotly fig objects from graphs.py
from graphs import generate_meteo_fig

# Importing layer style button builder and fetched API data from utils.py
from utils import build_layer_style_button, build_live_alerts_metadata


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT

# ----------------------------------------------------------------------------------------------------------------------
# Alert simulation
# The following block is used to create the radio button that allows to simulate alerts.

def build_alert_radio_button():
    """
    -- For debug purposes only --

    This function instantiates a radio button which allows, for debug purposes, to simulate an alert event.
    """
    alert_radio_button = dcc.RadioItems(
        options=[
            {'label': 'no alert', 'value': 0},
            {'label': 'alert', 'value': 1},
        ],
        value=0,
        labelStyle={'display': 'inline-block'},
        id='alert_radio_button'
    )

    return alert_radio_button


# ----------------------------------------------------------------------------------------------------------------------
# Map style
# The following block is used to determine which map style (risks or alerts) to use and allow the user to change it.

def build_map_style_button():
    """
    This function instantiates the button which allows users to change the style of the map.
    """
    button = html.Button(children='Afficher les niveaux de risques',
                         id='map_style_button',
                         className='btn btn-warning')

    return html.Center(button)


# This function takes as input the number of clicks on the button defined above and returns the layer style to use
def choose_map_style(n_clicks):
    """
    This function allows, depending on user's choice, to display the right style of map and button content.

    It takes as input (thanks to a callback in main.py) the number of clicks on the button defined above and returns:

    - the alerts map and its attributes if the number of clicks is even;
    - the risks map and its attributes if the number of clicks on the button is odd.

    More precisely, it returns three elements:

    - the appropriate message for the button defined above;
    - the chosen map object;
    - and the slider object (simply a void string if the alerts view was chosen).
    """

    # Because we start with the alerts map, if the number of clicks is even, this means that
    # we are still using the "Alerts and Infrastructure" map and we may want to switch to the "Risk Scores" one
    if n_clicks % 2 == 0:
        button_content_map = 'Afficher les niveaux de risques'
        map_object = build_alerts_map()
        slider = ' '
        map_style_in_use = 'alerts'

    # If the number of clicks is odd, this means we are using the "Risk Scores" map
    # and we may want to come back to the "Alerts and Infrastructure" one
    else:
        button_content_map = 'Revenir à la carte Alertes'
        map_object = build_risks_map()
        slider = build_opacity_slider()
        map_style_in_use = 'risks'

    return button_content_map, map_object, slider, map_style_in_use


# ----------------------------------------------------------------------------------------------------------------------
# Past fires button
# The following block is used to build the radio button with which users choose to display or not past fires.

def build_historic_fires_radio_button():
    """
    This function allows users to select whether to display past fires as markers on the map.

    It instantiates and returns the appropriate radio button (inside a html.Center wrapping).
    """

    historic_fires_radio_button = dcc.RadioItems(
        options=[
            {'label': 'Oui', 'value': 1},
            {'label': 'Non', 'value': 0},
        ],
        value=1,
        labelStyle={'display': 'inline-block',
                    'margin': '0 10px'},
        id='historic_fires_radio_button'
    )

    return html.Center(historic_fires_radio_button)


# ----------------------------------------------------------------------------------------------------------------------
# User selection area
# The following block gathers previously defined functions to construct the generic user selection area.

#This function returns the user selection area in the left side bar
def build_user_selection_area():
    """
    This function builds upon all the methods defined above to output the user selection area,
    common to both alerts and risks views and placed in the blank space on the left of the map.

    It returns a list of Dash core and HTML components to be used below in the Homepage function.
    """
    return [html.Div(build_alert_radio_button(), style={'display': 'none'}),
            dcc.Markdown('---'),

            # Map filters added below
            html.H5(("Filtres Carte"), style={'text-align': 'center'}),

            # Button allowing users to change the layer style (topgraphic / satellite)
            html.P(build_layer_style_button()),
            dcc.Markdown('---'),

            # Button allowing users to change the map style (alerts / risks)
            html.P(build_map_style_button()),
            dcc.Markdown('---'),

            # Radio button allowing users to display or not past fires as markers on the map
            html.Center(dcc.Markdown("Afficher l'historique des feux :")),
            html.P(build_historic_fires_radio_button()),
            dcc.Markdown('---'),

            # Opacity slider for the risks view
            html.P(id="hp_slider"),

            # Placeholder containing the detection data for any alert of interest
            html.P(id="hp_alert_frame_metadata")
            ]


# ----------------------------------------------------------------------------------------------------------------------
# Alert frame and metadata
# The following block is used to display the metadata and the detection frame associated with a given alert.

def display_alerts_frames(n_clicks=None, alert_metadata=None, img_url=None):
    """
    This function builds the components that display the detection image and metadata related to a given alert
    in the blank space on the left of the map, whenever the user clicks on an alert marker and on the following button.

    It can take several arguments which default to None:

    - 'n_clicks': number of clicks on the button that triggers the display of detection data for a given alert;
    - 'alert_metadata': dictionary containing information (to be displayed via this function) about an ongoing alert;
    - 'img_url': URL address of the image based on which the detection unit has triggered an alert.

    It then returns an html.Div component that contains several elements (detection frame and metadata).
    """

    # If there is no alert_metadata argument to reuse, we instantiate it with a function imported from utils.py
    if alert_metadata is None:
        alert_metadata = build_live_alerts_metadata()

    # Defining style parameters for the detection frame
    frame_style = {
        'width': '50vh',
        'height': '35vh',
        'margin': 'auto',
        'display': 'block',
        'text-align': 'center',
    }

    if n_clicks is not None:
        # Title located above the detection frame
        frame_title = html.H5("Image de détection", style={'text-align': 'center'})

        # Detection frame
        alert_frame = html.Img(
            id='alert_frame',
            src=img_url,
            style=frame_style
        )

        separator = dcc.Markdown('---')

        # Title located above the detection metadata
        alert_metadata_title = html.H5("Données de détection", style={'text-align': 'center'})

        # Summary of the detection metadata
        alert_metadata = html.Div(
            id="alert_metadata_user_selection",
            children=[
                "Tour: {}".format(alert_metadata['site_name']),
                html.Br(),
                "Coordonnées de la tour: {}, {}".format(alert_metadata['lat'], alert_metadata['lon']),
                html.Br(),
                "Id de caméra: {}".format(alert_metadata['device_id']),
                html.Br(),
                "Azimuth: {}".format(alert_metadata['azimuth'])]
        )

        # Gathering all elements in a single html.Div component
        alert_frame_metadata = html.Div(
            children=[frame_title, alert_frame, separator, alert_metadata_title, alert_metadata]
        )

        return html.Div(alert_frame_metadata)

    # If no button click is triggering the display of the alert frame and metadata, function returns a void string
    return ""


# ----------------------------------------------------------------------------------------------------------------------
# Meteo graphs
# The following block builds upon functions defined in graphs.py and is used to display or hide meteo graphs.

def display_meteo_graphs(display=False):
    """
    This function takes a boolean, 'display', as argument which indicates whether to display or hide
    graphs related to meteorological indicators. To do so, it builds upon the generate_meteo_fig defined
    in the graphs.py file.
    """
    if display is True:
        # If the 'display' argument is True, graphs are instantiated and returned
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
        # If the 'display' argument is False, the function returns a void string
        return ''

# ----------------------------------------------------------------------------------------------------------------------
# Login modal
# The following block defines the build_login_modal, which allows to instantiate the modal opened at the beginning of
# each session for the user to enter his/her credentials.

def build_login_modal():
    """
    This function simply creates and returns the login modal, which opens up at the beginning of each session to obtain
    the credentials of the user.
    """
    return dbc.Modal(
        [
            dbc.ModalBody(
                [
                    html.Center(
                        dbc.Col(
                            [
                                html.Div(style={'height': '10px'}),
                                html.Img(src=pyro_logo, width="190px"),
                                html.Div(style={'height': '30px'}),
                                dbc.FormGroup(
                                    [
                                        dbc.Input(
                                            id='username_input',
                                            type='text',
                                            placeholder="UTILISATEUR",
                                            style={'width': '250px'},
                                            autoFocus=True
                                        )
                                    ],
                                ),
                                dbc.FormGroup(
                                    [
                                        dbc.Input(
                                            id='password_input',
                                            type='password',
                                            placeholder='MOT DE PASSE',
                                            style={'width': '250px'},
                                        )
                                    ],
                                ),
                            ],
                            align='center'
                        ),
                    ),
                    html.Div(style={'height': '15px'}),
                    html.Center(
                        dbc.Button(
                            "Connexion",
                            id='send_form_button',
                            color='primary',
                            className='ml-3'
                        ),
                    ),
                    html.Div(style={'height': '15px'}),
                    html.Div(id='form_feedback_area')
                ],
                style={'background': '#F8FAFF'}
            ),
        ],
        id="login_modal",
        backdrop='static',
        keyboard=False,
        style={"max-width": "none", "width": "500px"}
    )


# ----------------------------------------------------------------------------------------------------------------------
# App layout
# The following block gathers elements defined above and returns them via the Homepage function

def Homepage():
    """
    The following function is used in the main.py file to build the layout of the web application.

    It builds upon methods defined above or in alerts.py or navbar.py files to instantiate the various components.
    """

    # Body container
    body = dbc.Container([
        # Markdown separator below the navigation bar
        dbc.Row(dcc.Markdown('---')),

        html.Center(
                html.Div(
                    id='login_background',
                    children=[
                        html.Img(src='assets/background.png', width="100%")
                    ]
                )
            ),

        # Optional radio button to simulate alert events in debugging mode
        dbc.Row(dbc.Col(id='live_alert_header_btn')),

        # Main part of the page layout
        dbc.Row(
            [
                # Left column containing the user selection area
                dbc.Col(
                    build_user_selection_area(),
                    id='user_selection_column',
                    md=3),

                # Right column containing the map and various hidden components
                dbc.Col([
                    # Map object added here
                    html.Div(build_alerts_map(), id='hp_map'),

                    # Two placeholders updated by callbacks in main.py to trigger a change in map style
                    html.Div(id='map_style_btn_switch_view'),   # Associated with the main map style button
                    html.Div(id='alert_btn_switch_view'),   # Associated with the alert banner in risks mode

                    # Simple placeholder - Source of truth for the map style being viewed
                    html.Div(id='current_map_style', children='alerts'),

                    # Hidden html.Div storing the URL address of the detection frame of the latest alert
                    html.Div(id='img_url', style={'display': 'none'})],
                    md=9),
            ]
        ),

        # Login modal added here
        build_login_modal(),

        # Meteo graphs added here
        display_meteo_graphs(display=False)
    ],
        fluid=True,
    )

    # Instantiating navbar object from navbar.py
    layout = html.Div([Navbar(), body])

    return layout
