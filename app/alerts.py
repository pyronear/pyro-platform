# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following Python file is dedicated to the "Alerts and Infrastructure" view of the dashboard.

After a first block dedicated to imports, the content section is divided between:

- a departments block used to read the local geojson file and create the corresponding object on the map;
- a sites markers block used to instantiate markers corresponding to detection units on the field;
- a fire alerts block used to create alert-related objects and the interactive zoom;
- a final block mobilising previously defined functions to instantiate the "Alertes et Infrastructure" map.

Most functions defined below are called in the main.py file, in the alerts callbacks.
"""


# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# Useful imports to handle API payloads
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import json

# Useful imports to read the GeoJSON file from Pyro-Risk release
import requests
import config as cfg

# Various modules provided by Dash to build app components
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import dash_leaflet.express as dlx

# Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_filters_object, build_legend_box

# Importing a pre-instantiated client
from services import api_client

# Imports allowing to build the vision angle of the cameras
from geopy import Point
from geopy.distance import geodesic


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT

# ----------------------------------------------------------------------------------------------------------------------
# Departments
# The following block is used to display the borders of the departments on the map and to add interactivity.

# We read the GeoJSON file from the Pyro-Risk release (URL in config.py) and store it in the departments variable
departments = requests.get(cfg.GEOJSON_FILE).json()


def build_departments_geojson():
    """
    This function reads the departments.geojson file in the /data folder thanks to the json module
    and returns an interactive dl.GeoJSON object containing its information, to be displayed on the map.
    """

    # We plug departments in a Dash Leaflet GeoJSON object that will be added to the map
    geojson = dl.GeoJSON(data=departments,
                         id='geojson_departments',
                         zoomToBoundsOnClick=False,
                         hoverStyle=dict(weight=3,
                                         color='#666',
                                         dashArray='')
                         )

    # We simply return the GeoJSON object for now
    return geojson


# ----------------------------------------------------------------------------------------------------------------------
# Site devices
# The following block is used to load the data relative to site devices.
# It is called in main.py by the callback that is itself triggered by the user's login.

def get_site_devices_data(client):
    """
    This short function takes as input a pre-instantiated Pyro-API client and returns the site devices data as a dict.
    """
    response = client.get_sites()
    sites = response.json()
    data = {site['name']: client.get_site_devices(site['id']).json() for site in sites}

    return data


def retrieve_site_from_device_id(device_id, site_devices_data):

    for key, value in site_devices_data.items():
        if device_id in value:
            site_name = key.replace('_', ' ').title()
            return site_name
        else:
            continue

    raise Exception('Device ID not found in site devices data.')


# ----------------------------------------------------------------------------------------------------------------------
# Sites markers
# The following block is used to fetch and display on the map the positions of detection units.

# We import the cameras's positions from the API that locates the cameras
# Fetching the response in a variable
response = api_client.get_sites()

# Check token expiration
if response.status_code == 401:
    api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
    response = api_client.get_sites()

site_devices = get_site_devices_data(client=api_client)

# Getting the json data out of the response
camera_positions = response.json()


def build_sites_markers(dpt_code=None):
    """
    This function reads the site markers by making the API, that contains all the
    information about the sites equipped with detection units.

    It then returns a dl.MarkerClusterGroup object that gathers all relevant site markers.

    NB: certain parts of the function, which we do not use at the moment and that were initially
    designed to bind the display of site markers to a click on the corresponding department, are
    commented for now but could prove useful later on.
    """

    # Building alerts_markers objects and wraps them in a dl.LayerGroup object
    icon = {
        "iconUrl": '../assets/pyro_site_icon.png',
        "iconSize": [50, 50],        # Size of the icon
        "iconAnchor": [25, 45],      # Point of the icon which will correspond to marker's location
        "popupAnchor": [0, -20]      # Point from which the popup should open relative to the iconAnchor
    }

    # We build a list of markers containing the info of each site/camera
    markers = []
    for row in camera_positions:
        site_id = row['id']
        lat = round(row['lat'], 4)
        lon = round(row['lon'], 4)
        site_name = row['name'].replace('_', ' ').title()
        markers.append(
            dl.Marker(
                id=f'site_{site_id}',    # Necessary to set an id for each marker to receive callbacks
                position=(lat, lon),
                icon=icon,
                children=[
                    dl.Tooltip(site_name),
                    dl.Popup(
                        [
                            html.H2(f'Site {site_name}'),
                            html.P(f'Coordonnées : ({lat}, {lon})'),
                            html.P(
                                f"Nombre de caméras : {len(site_devices.get(row['name']))}"
                            )
                        ]
                    )
                ]
            )
        )

    # We group all dl.Marker objects in a dl.MarkerClusterGroup object and return it
    return dl.MarkerClusterGroup(children=markers, id='sites_markers')


def build_vision_polygon(event_id, site_lat, site_lon, yaw, opening_angle, dist_km):
    """
    This function allows to build the vision angle of a camera, ie. the zone covered by the detection device.

    It takes as input:

    - site_lat, the latitude of the detection device;

    - site_lon, the longitude of the detection device;

    - yaw, the orientation of the device expressed in degrees;

    - opening_angle, the width of the zone covered by the device expressed in degrees;

    - dist_km, the distance that the detection device is able to cover in kilometers.

    The function then builds and returns the zone covered by the detection device as a Dash Leaflet Polygon, which can
    be represented on the map.
    """

    # The center corresponds the point from which the vision angle "starts"
    center = [site_lat, site_lon]

    print(center)

    points1 = []
    points2 = []

    for i in reversed(range(1, opening_angle + 1)):
        yaw1 = (yaw - i / 2) % 360
        yaw2 = (yaw + i / 2) % 360

        point = geodesic(kilometers=dist_km).destination(Point(site_lat, site_lon), yaw1)
        points1.append([point.latitude, point.longitude])

        point = geodesic(kilometers=dist_km).destination(Point(site_lat, site_lon), yaw2)
        points2.append([point.latitude, point.longitude])

    points = [center] + points1 + list(reversed(points2))

    polygon = dl.Polygon(
        id={
            'type': 'vision_polygon',
            'index': str(event_id)
        },
        color="#ff7800",
        opacity=0.5,
        positions=points
    )

    return polygon


# ----------------------------------------------------------------------------------------------------------------------
# Fire alerts
# The following block is dedicated to fetching information about fire alerts and displaying them on the map.

def build_alerts_elements(images_url_live_alerts, live_alerts, map_style, blocked_event_ids):
    """
    This function is used in the main.py file to create alerts-related elements such as the alert button (banner)
    or the alert markers on the map.

    It takes as arguments:

    - 'images_url_live_alerts': url dict with live_alerts urls having event_id keys
    - 'live_alerts': json containing live_alerts data
    - 'map_style': the type of map in place, either 'alerts' or 'risks'.

    All these inputs are instantiated in the main.py file via a POST from the API.

    In the base case, the function returns:

    - the urls addresses of the image to be displayed on the left of the map;

    - the new_alert_button;

    - the alert markers displayed on the map;

    - new navbar_color as in alert mode;

    - new navbar title;

    - a list of individual storage components, one for each alert/event to be displayed, that give the URL addresses of
    the corresponding frames.

    But if the style of map in place is 'risks', we don't want to display neither the alert markers.
    So in this case, the third output of the function is a void string.
    """

    # Changing the navabar color and title
    navbar_color = "#f34848"
    navbar_title = "Départs de feux détectés"

    # Format of the alert marker icon
    icon = {
        "iconUrl": '../assets/pyro_alert_icon.png',
        "iconSize": [50, 50],        # Size of the icon
        "iconAnchor": [25, 45],      # Point of the icon which will correspond to marker's and popup's location
        "popupAnchor": [0, -20]      # Point from which the popup should open relative to the iconAnchor
    }

    # Building the list of alert markers to be displayed
    alerts_markers = []
    live_alerts_check = json.loads(live_alerts)

    if (
        (
            isinstance(live_alerts_check, dict) and
            'status' in live_alerts_check.keys() and
            live_alerts_check['status'] == 'never_loaded_alerts_data'
        )
        or not live_alerts
    ):
        # When there is no live alert to display, we return a alert header button that will remain hidden
        hidden_header_alert_button = html.Div(
            html.Button(
                id=f'alert_button_{map_style}'
            ),
            style={'display': 'none'}
        )

        # This is to ensure that the "click_new_alerts_button" callback gets triggered with n_clicks=0 and hides the
        # blank user selection area, letting the map take the full width of the screen

        # (It can be interesting to test returning [] instead of [hidden_header_alert_button] and erase all alerts one
        # by one if explanations are unclear)

        return [hidden_header_alert_button], [], '#054546', 'Surveillez les départs de feux'

    else:
        all_alerts = pd.read_json(live_alerts)

    all_alerts = all_alerts[~all_alerts['event_id'].isin(blocked_event_ids['event_ids'])].copy()

    all_events = all_alerts.drop_duplicates(['id', 'event_id']).groupby('event_id').head(1)  # Get unique events
    for _, row in all_events.iterrows():
        alert_id = str(row['event_id'])
        alert_lat = row['lat']
        alert_lon = row['lon']

        alerts_markers.append(dl.Marker(
            id={'type': 'alert_marker', 'index': alert_id},   # Setting a unique id for each alert marker
            position=(alert_lat, alert_lon),
            icon=icon
        ))

    # Wrapping all markers in the list into a dl.LayerGroup object
    alerts_markers_layer = dl.LayerGroup(children=alerts_markers, id='alerts_markers')

    # Building the alerts notification btn
    nb_alerts = len(all_events)  # Number of unique events
    alert_button = html.Div(dbc.Button(
        "Nouvelles alertes | {}".format(nb_alerts), className="btn-header-alerts"),
        id=f'alert_button_{map_style}',
        style={'position': 'absolute', 'top': '10px', 'right': '30px', 'z-index': '1000'}
    )

    individual_alert_frame_placeholder_children = []
    for event_id, frame_url_list in images_url_live_alerts.items():

        individual_alert_frame_placeholder_children.append(
            html.Div(
                id={
                    'type': 'individual_alert_frame_storage',
                    'index': str(event_id)
                },
                children=frame_url_list,
                style={'display': 'none'}
            )
        )

    return [alert_button, alerts_markers_layer, navbar_color, navbar_title]


def build_alert_modal(event_id, device_id, lat, lon, site_name, urls):

    number_of_images = len(urls)

    return dbc.Modal(
        id={
            'type': 'alert_modal',
            'index': str(event_id)
        },
        is_open=False,
        keyboard=True,
        size='xl',
        children=[
            dbc.ModalBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        html.P(
                                            f'{site_name}',
                                            style={
                                                'color': 'white',
                                                'text-indent': '15px',
                                                'font-size': '20px'
                                            }
                                        ),
                                        style={
                                            'backgroundColor': '#054546',
                                            'height': '40px'
                                        }
                                    ),
                                    html.Div(
                                        html.P(
                                            f'Caméra ID {device_id}',
                                            style={
                                                'color': '#054546',
                                                'font-size': '15px',
                                                'text-indent': '15px'
                                            }
                                        ),
                                        style={
                                            'backgroundColor': '#FFECC1',
                                            'height': '25px'
                                        }
                                    ),
                                    html.Div(
                                        [
                                            html.P(
                                                f'Latitude : {round(lat, 4)}',
                                                style={
                                                    'text-indent': '15px',
                                                    'font-size': '18px'
                                                }
                                            ),
                                            html.P(
                                                f'Longitude : {round(lon, 4)}',
                                                style={
                                                    'text-indent': '15px',
                                                    'font-size': '18px'
                                                }
                                            )
                                        ],
                                        style={
                                            'backgroundColor': '#5BBD8C',
                                            'fontColor': '#2C796E'
                                        }
                                    ),
                                    html.Br(),
                                    html.Div(
                                        id={
                                            'type': 'alert_relevance_space',
                                            'index': str(event_id)
                                        },
                                        children=[
                                            html.P(
                                                "L'alerte est-elle pertinente ?",
                                                style={'text-indent': '15px'}
                                            ),
                                            dbc.RadioItems(
                                                id={
                                                    'type': 'alert_relevance_radio_button',
                                                    'index': str(event_id)
                                                },
                                                options=[
                                                    {'label': 'Oui', 'value': True},
                                                    {'label': 'Non', 'value': False}
                                                ],
                                                value=None,
                                                labelStyle={'display': 'inline-block'}
                                            )
                                        ]
                                    ),
                                    html.Br(),
                                    html.Div(
                                        id={
                                            'type': 'alert_type_space',
                                            'index': str(event_id)
                                        },
                                        children=[
                                            html.P(
                                                "Quel type de fumée a été détecté ?",
                                                style={'text-indent': '15px'}
                                            ),
                                            dbc.RadioItems(
                                                id={
                                                    'type': 'alert_type_radio_button',
                                                    'index': str(event_id)
                                                },
                                                options=[
                                                    {'label': 'Feu de forêt', 'value': 'wildfire'},
                                                    {'label': 'Incendie domestique', 'value': 'domestic_fire'},
                                                    {'label': 'Cheminée', 'value': 'chimney'},
                                                    {'label': 'Nuage', 'value': 'cloud'},
                                                    {'label': 'Autre', 'value': 'other'}
                                                ],
                                                value=None,
                                            )
                                        ],
                                    )
                                ],
                                width=4
                            ),
                            dbc.Col(
                                [
                                    html.Img(
                                        id={
                                            'type': 'alert_frame',
                                            'index': str(event_id)
                                        },
                                        src=urls[0],
                                        width='700px'
                                    ),
                                    dcc.Markdown('---'),
                                    dcc.Slider(
                                        id={
                                            'type': 'alert_slider',
                                            'index': str(event_id)
                                        },
                                        min=1, max=number_of_images,
                                        step=1,
                                        marks={i + 1: str(i + 1) for i in range(number_of_images)},
                                        value=1
                                    )
                                ],
                                width=16
                            )
                        ],
                        no_gutters=True
                    )
                ]
            )
        ]
    )


def display_alert_selection_area(n_clicks):
    """
    Used in main.py in the "click_new_alerts_button" callback, this function takes as input the number of clicks on the
    alert header button (in the top-right corner of the map) and returns the appropriate:

    - width of the user selection area column on the left-hand side of the map;
    - width of the map;
    - style (being displayed or not) of the alert header button;
    - style (being displayed or not) of the alert selection area.

    If the number of clicks is 0, the user selection area is fully hidden and the button is displayed on the map. On the
    other hand, if the number of clicks is stricly above 0, the various attributes are set so as to let the user sele-
    ction area appear.
    """
    if n_clicks > 0:
        # Defining col width for both user selection area and map
        md_user = 3
        md_map = 9

        # Disabling alert_button
        alert_button_status = {'display': 'none'}

        # Displaying the alert selection area
        alert_selection_area_style = {}

    else:
        md_user = 0
        md_map = 12
        alert_button_status = {}
        alert_selection_area_style = {'display': 'none'}

    return [md_user, md_map, alert_button_status, alert_selection_area_style]


def build_individual_alert_components(live_alerts, alert_frame_urls, blocked_event_ids, site_devices_data):
    """
    This function builds the user selection area containing the alert list

    - it creates the alerts_list based on live alerts data;
    - it creates the vision angle polygons of each alert that should be displayed;
    - it instantiates the modal corresponding to each live alert.

    To do so, it takes three arguments:

    - the live alerts data filling the alert_list;
    - the URL addresses of alert frames, gathered by event_id in the alert_frame_urls dictionary.
    """

    # Creating the alert_list based on live_alerts
    live_alerts_check = json.loads(live_alerts)

    if (
        (
            isinstance(live_alerts_check, dict) and
            'status' in live_alerts_check.keys() and
            live_alerts_check['status'] == 'never_loaded_alerts_data'
        )
        or not live_alerts_check
    ):
        return [], [], []

    else:
        all_alerts = pd.read_json(live_alerts)

    all_alerts = all_alerts[~all_alerts['event_id'].isin(blocked_event_ids['event_ids'])].copy()

    all_events = all_alerts.drop_duplicates(['id', 'event_id']).groupby('event_id').head(1)  # Get unique events

    # Instantiating the void lists that will contain the basic alert elements
    alert_list = []
    vision_polygons_children = []
    alert_modals_children = []

    for _, row in all_events.iterrows():

        alert_id = str(row['event_id'])
        alert_lat = round(row['lat'], 4)
        alert_lon = round(row['lon'], 4)
        alert_azimuth = round(row['yaw'], 1)
        alert_date = datetime.fromisoformat(str(row['created_at'])).date()
        alert_time = datetime.fromisoformat(str(row['created_at'])) + timedelta(hours=2)
        alert_time = alert_time.time()

        device_id = row['device_id']
        try:
            site_name = retrieve_site_from_device_id(device_id, site_devices_data)
        except Exception:
            site_name = ''

        alert_selection_button = html.Div([
            dcc.Markdown('---'),
            dbc.Button(children=[
                       html.Span('Azimuth : {}°'.format(alert_azimuth), style={'font-weight': 'bold'}),
                       html.Span('Lat : {} / Lon : {}'.format(alert_lat, alert_lon), style={'display': 'block'}),
                       html.Span(f'Tour : {site_name}', style={'display': 'block'}),
                       html.Span('{} / {}:{}'.format(alert_date, alert_time.hour, alert_time.minute),
                                 style={'display': 'block'})],
                       id={'type': 'alert_selection_btn', 'index': alert_id},
                       className='btn-alerts'),
        ])

        alert_list.append(alert_selection_button)

        polygon = build_vision_polygon(
            event_id=alert_id,
            site_lat=row['lat'],
            site_lon=row['lon'],
            yaw=row['yaw'],
            opening_angle=60,
            dist_km=2
        )

        vision_polygons_children.append(polygon)

        frames_to_display = alert_frame_urls.get(alert_id, [''])[-15:]

        modal = build_alert_modal(
            event_id=alert_id,
            device_id=row['device_id'],
            lat=row['lat'],
            lon=row['lon'],
            site_name=site_name,
            urls=frames_to_display
        )

        alert_modals_children.append(modal)

    user_alerts_selection = [html.Div([
        dcc.Markdown('---'),
        html.H5(children="Nouvelles alertes !", style={'text-align': 'center'})]),
        dbc.Container(alert_list)]

    return [
        user_alerts_selection,
        vision_polygons_children,
        alert_modals_children
    ]


def build_alert_overview(live_alerts, frame_urls, event_id, acknowledged):

    if not acknowledged:

        acknowledge_alert_space_children = [
            dcc.Markdown('---'),
            html.Div(dbc.Button(
                id={
                    'type': 'acknowledge_alert_button',
                    'index': event_id
                },
                children="Acquitter l'alerte",
                className="btn-layers",
                size="sm"
            ))
        ]

    else:

        acknowledge_alert_space_children = [
            html.P('Alerte acquittée.')
        ]

    df = pd.read_json(live_alerts)
    df = df.drop_duplicates(['id', 'event_id']).groupby('event_id').head(1)  # Get unique events

    df['event_id'] = df['event_id'].astype(str)

    lat = df[df['event_id'] == event_id]['lat'].iloc[0]
    lon = df[df['event_id'] == event_id]['lon'].iloc[0]
    alert_azimuth = df[df['event_id'] == event_id]['yaw'].iloc[0]

    div = html.Div(
        id={
            'type': 'alert_overview',
            'index': event_id
        },
        children=[
            html.Center(
                children=[
                    dcc.Markdown('---'),
                    html.B(f'Alerte n°{event_id}'),
                    html.P(f'Azimuth : {alert_azimuth}'),
                    html.P(f'Latitude : {lat}'),
                    html.P(f'Longitude: {lon}'),
                    html.Img(
                        id={
                            'type': 'alert_frame_small',
                            'index': event_id
                        },
                        src=frame_urls[event_id][0],
                        width="300px"
                    ),
                    html.Div(
                        id={
                            'type': 'acknowledge_alert_space',
                            'index': event_id
                        },
                        children=acknowledge_alert_space_children
                    ),
                    html.Div(
                        dbc.Button(
                            id={
                                'type': 'close_alert_overview_button',
                                'index': event_id
                            },
                            children="Fermer l'aperçu de l'alerte",
                            className="btn-layers",
                            size="sm"
                        )
                    ),
                    dbc.Modal(
                        id={
                            'type': 'acknowledgement_confirmation_modal',
                            'index': event_id
                        },
                        is_open=False,
                        keyboard=True,
                        size='sm',
                        children=[
                            dbc.ModalHeader("Confirmer l'acquittement de l'alerte ?"),
                            dbc.ModalBody(
                                dbc.Button(
                                    id={
                                        'type': 'acknowledgement_confirmation_button',
                                        'index': event_id
                                    },
                                    children='Oui',
                                    className='btn-layers',
                                    size='sm'
                                ),
                                dbc.Button(
                                    id={
                                        'type': 'close_confirmation_modal_button',
                                        'index': event_id
                                    },
                                    children='Non',
                                    className='btn-layers',
                                    size='sm'
                                )
                            )
                        ]
                    ),
                    html.Div(
                        id={
                            'type': 'manage_confirmation_modal_acknowlegdment_button',
                            'index': event_id
                        },
                        style={'display': 'none'}
                    ),
                    html.Div(
                        id={
                            'type': 'manage_confirmation_modal_close_button',
                            'index': event_id
                        },
                        style={'display': 'none'}
                    ),
                    html.Div(
                        id={
                            'type': 'manage_confirmation_modal_confirmation_button',
                            'index': event_id
                        },
                        style={'display': 'none'}
                    )
                ]
            )
        ]
    )

    return lat, lon, div


# ----------------------------------------------------------------------------------------------------------------------
# Map instantiation
# The last block gathers previously defined functions to output the "Alerts and Infrastructure" map.

def build_alerts_map():
    """
    The following function mobilises functions defined hereabove or in the utils module to
    instantiate and return a dl.Map object, corresponding to the "Alerts and Infrastructure" view.
    """
    map_object = dl.Map(center=[44.73, 4.27],  # Determines the point around which the map is centered
                        zoom=9,               # Determines the initial level of zoom around the center point
                        children=[
                            dl.TileLayer(id='tile_layer'),
                            build_departments_geojson(),
                            build_filters_object(map_type='alerts'),
                            build_legend_box(map_type='alerts'),
                            build_sites_markers(),
                            dl.LayerGroup(id='vision_polygons'),
                            html.Div(id="live_alerts_marker"),
                            html.Div(id="live_alert_header_btn"),
                            html.Div(id='fire_markers_alerts')],  # Will contain the past fire markers of the alerts map
                        style=map_style,      # Reminder: map_style is imported from utils.py
                        id='map')

    return map_object
