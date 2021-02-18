# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following file gathers several items (variables, functions...) that are common to both views of the dashboard.

Following a first section dedicated to imports, the content section is made of 5 code blocks:

- a map layer block, used to switch between the schematic and satellite background layers;
- an information box block, used to build the info object at the top-right of the map and fill it in;
- a legend block, used to build the legend box at the bottom right of each map with the relevant indications;
- a past fires block, which fetches information from the dedicated csv file and adds related markers to the map;
- a block for API calls, designed to gather information about ongoing alerts and build the site markers.

NB: some sections and/or functions still have to be completed, especially API calls.
"""

# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# Useful imports to open and read the 'historic_fires.csv' file
from pathlib import Path
import pandas as pd

# Useful import to reformat the date information associated with past fires
import datetime as dt

# Various modules provided by Dash to build app components
import dash_html_components as html
import dash_leaflet as dl


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT

# ----------------------------------------------------------------------------------------------------------------------
# Diverse
# The following block is used for the definition of small variables and/or functions.

map_style = {'width': '100%',
             'height': '90vh',
             'margin': 'auto',
             'display': 'block'}


# ----------------------------------------------------------------------------------------------------------------------
# Map layer
# The following block is used to determine what layer we use for the map and enable the user to change it.

def build_layer_style_button():
    """
    This function creates and returns the button allowing users to change the map
    background layer (either topographic/schematic or satellite).
    """
    button = html.Button(children='Activer la vue satellite',
                         id='layer_style_button',
                         className="btn btn-warning")

    return html.Center(button)


def choose_layer_style(n_clicks):
    """
    This function takes as input the number of clicks on the button defined above and returns:

    - the appropriate message for the button (changed at each click);
    - the background layer style to use (URL and attribution).
    """

    # Because we start with the topographic view, if the number of clicks is even, this means
    # that we are still using the topographic view and we may want to activate the satellite one.
    if n_clicks % 2 == 0:
        button_content = 'Activer la vue satellite'
        layer_url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        layer_attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

    # If the number of clicks is odd, this means we are using the satellite view
    # and may want to come back to the topographic one.
    else:
        button_content = 'Revenir à la vue schématique'
        layer_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        layer_attribution = ('Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, '
                             'Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community')

    return button_content, layer_url, layer_attribution


# ----------------------------------------------------------------------------------------------------------------------
# Information box
# The following block is used to build the box in the top-right corner and fill it in with the relevant information.

def build_info_box(feature=None):
    """
    This function creates the HTML components of the information box.

    It takes as argument the polygon hovered by the user in the departments GeoJSON object, if any.

    It returns:

    - the title of the information box and the name of the hovered when relevant;
    - the title of the information box and a generic message when there is no department being hovered.
    """
    header_dept = [html.H4('Département sélectionné :')]

    if feature:
        return header_dept + [html.B(feature['properties']['nom'])]

    # If no object is hovered, it just returns a standard statement
    return header_dept + [html.P('Faites glisser votre curseur sur un département')]


def build_info_object(map_type):
    """
    This function builds upon the build_info_box function defined above.

    It takes as input the type of map considered (either 'alerts' or 'risks') and returns
    an information box object located in the top-right corner of the map with a relevant id.
    """
    if map_type == 'alerts':
        object_id = 'alerts_info'

    else:
        object_id = 'risks_info'

    return html.Div(children=build_info_box(),
                    id=object_id,
                    className='info',
                    style={'position': 'absolute',
                           'top': '10px',
                           'right': '10px',
                           'z-index': '1000'}
                    )


# ----------------------------------------------------------------------------------------------------------------------
# Legend
# The following block is used to build the legend in the bottom-right corner of the map.

def build_legend_box(map_type=None):
    """
    This function generates a legend box, whose content depends on the view chosen.

    It takes as argument the type of the map ('alerts' or 'risks' chosen by the user).

    It returns the appropriate legend for each of the two maps in the box, with a dedicated id.
    """
    site_img_url = '../assets/pyro_site_icon.png'
    past_fire_img_url = '../assets/pyro_oldfire_icon.png'
    alert_img_url = '../assets/pyro_alert_icon.png'

    img_style = {'width': '4.5vh',
                 'height': '4.5vh'}

    image_div_style = {'display': 'inline-block', 'height': '22px', 'margin-left': '2px'}
    text_div_style = {'display': 'inline-block', 'height': '22px', 'margin-left': '7px'}

    if map_type == 'alerts':

        # Site de surveillance
        legend_body = [html.Div([html.Div(html.Img(src=site_img_url, style=img_style),
                                          style=image_div_style),
                                 html.Div(html.P('Matériel installé'),
                                          style=text_div_style)])]

        # Historique des feux
        legend_body.append(html.Div([html.Div(html.Img(src=past_fire_img_url, style=img_style),
                                              style=image_div_style),
                                     html.Div(html.P('Incendie passé'),
                                              style=text_div_style)]))

        # Alerte
        legend_body.append(html.Div([html.Div(html.Img(src=alert_img_url, style=img_style),
                                              style=image_div_style),
                                     html.Div(html.P('Alerte en cours'),
                                              style=text_div_style)]))

    elif map_type == 'risks':
        legend_body = [html.Div([html.Div(html.Img(src=past_fire_img_url, style=img_style),
                                          style=image_div_style),
                                 html.Div(html.P('Incendie passé'),
                                          style=text_div_style)])]

    legend_id = 'legend_' + map_type

    return html.Div(children=legend_body,
                    id=legend_id,
                    className='info',
                    style={'position': 'absolute',
                           'bottom': '30px',
                           'right': '10px',
                           'z-index': '1000'}
                    )


# ----------------------------------------------------------------------------------------------------------------------
# Past fires
# The following block is used to fetch the positions of past fires and build the related map attribute.

# Fetching the positions of past fires in a given department
def build_historic_markers(dpt_code=None):
    """
    This function reads through the 'historic_fires.csv' file stored in the /data folder.

    It takes as input a department code (as a character string), which will correspond to the department
    on which the user chooses to click and it returns past fires (as markers on the map) for this area.

    More precisely, it returns a dl.LayerGroup object that gathers all relevant past fire markers.
    """

    # As long as the user does not click on a department, dpt_code is None and we return no fire marker
    if not dpt_code:
        return None

    # We read the csv file that locates the old fires
    old_fire_positions = pd.read_csv(Path(__file__).parent.joinpath('data', 'historic_fires.csv'), ',')

    # The line below allows us to filter for the department of interest
    old_fire_positions = old_fire_positions[old_fire_positions['Département'] == int(dpt_code)].copy()

    icon = {"iconUrl": '../assets/pyro_oldfire_icon.png',
            "iconSize": [50, 50],       # Size of the icon
            "iconAnchor": [25, 45],      # Point of the icon which will correspond to marker's and popup's location
            "popupAnchor": [0, -20]  # Point from which the popup should open relative to the iconAnchor
            }

    # We build a list of dictionaries containing the coordinates of each fire
    fire_markers = []
    for i, row in old_fire_positions.iterrows():
        lat = row['latitude']
        lon = row['longitude']
        location = row['location']
        date = dt.datetime.strptime(row['acq_date'], '%Y-%m-%d')\
                          .strftime('%d %b %Y')

        if row['daynight'] == 'D':
            daynight = 'Diurne'
        elif row['daynight'] == 'N':
            daynight = 'Nocturne'
        else:
            daynight = None

        fire_markers.append(dl.Marker(id=f'historic_fire_{i}',  # Set an id for each marker to receive callbacks
                                      position=(lat, lon),
                                      icon=icon,
                                      children=[dl.Tooltip(f"Date: {date}"),
                                                dl.Popup([html.H4(f'Incendie du {date}'),
                                                          html.P(f'Commune : {location}'),
                                                          html.P(f'Type : {daynight}')])
                                                ]
                                      )
                            )

    # We gather all markers stored in the fire_markers list in a dl.LayerGroup object, which is returned
    return dl.LayerGroup(children=fire_markers,
                         id='historic_fires_markers')


# ----------------------------------------------------------------------------------------------------------------------
# API calls
# The following block is used to fetch alerts and sites data from the database.
# NB: for now, this is still a drafted response; proper API calls still have to be implemented

def build_live_alerts_metadata():
    """
    This function is used to fetch all metadata available in the DB about ongoing alerts via the API client.


    NB: for now, it is simply a handwritten example of API response and still needs to be written down.
    """

    alert_metadata = {
        "id": 0,
        "created_at": "2020-11-25T15:22:21.690Z",
        "media_url": "https://photos.lci.fr/images/613/344/photo-incendie-generac-gard-e8f2d9-0@1x.jpeg",
        "lat": 44.765181,
        "lon": 4.51488,
        "event_id": 0,
        "azimuth": "49.2°",
        "site_name": "Serre de pied de Boeuf",
        "type": "start",
        "is_acknowledged": False,
        "device_id": 123
    }

    return alert_metadata
