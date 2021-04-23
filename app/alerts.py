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
from datetime import datetime
import pandas as pd

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
from utils import map_style, build_filters_object, build_legend_box, user_department_lat_lon

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
    data = {site['id']: client.get_site_devices(site['id']).json() for site in sites}

    return data


# ----------------------------------------------------------------------------------------------------------------------
# Sites markers
# The following block is used to fetch and display on the map the positions of detection units.

# We import the cameras's positions from the API that locates the cameras
# Fetching the response in a variable
response = api_client.get_sites()

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
        lat = row['lat']
        lon = row['lon']
        site_name = row['name']
        markers.append(dl.Marker(id=f'site_{site_id}',    # Necessary to set an id for each marker to receive callbacks
                                 position=(lat, lon),
                                 icon=icon,
                                 children=[dl.Tooltip(site_name),
                                           dl.Popup([html.H2(f'Site {site_name}'),
                                                     html.P(f'Coordonnées : ({lat}, {lon})'),
                                                     html.P(f'Nombre de caméras : {4}')])]))

    # We group all dl.Marker objects in a dl.MarkerClusterGroup object and return it
    return dl.MarkerClusterGroup(children=markers, id='sites_markers')


def build_vision_polygon(site_lat, site_lon, yaw, opening_angle, dist_km):
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

    center = [site_lat, site_lon]

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
        color="#ff7800",
        opacity=0.5,
        positions=points
    )

    return polygon


# ----------------------------------------------------------------------------------------------------------------------
# Fire alerts
# The following block is dedicated to fetching information about fire alerts and displaying them on the map.

def build_alerts_elements(images_url_live_alerts, live_alerts, map_style):
    """
    This function is used in the main.py file to create alerts-related elements such as the alert button (banner)
    or the alert markers on the map.

    It takes as arguments:

    - 'images_url_live_alerts': url dict with live_alerts urls having event_id keys
    - 'live_alerts': json containing live_alerts data
    - 'map_style': the type of map in place, either 'alerts' or 'risks'.

    All these inputs are instantiated in the main.py file via a POST from the API.

    In the base case, the function returns:

    - the urls addresses of the image to be displayed on the left of the map
    - the new_alert_button
    - the alert markers displayed on the map
    - new navbar_color as in alert mode
    - new navbar title

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
    all_alerts = pd.read_json(live_alerts)
    all_events = all_alerts.drop_duplicates(['id', 'event_id']).groupby('event_id').head(1)  # Get unique events
    for _, row in all_events.iterrows():
        alert_id = str(row['event_id'])
        alert_lat = row['lat']
        alert_lon = row['lon']

        alerts_markers.append(dl.Marker(
            id={'type': 'alert_marker', 'index': alert_id},   # Setting a unique id for each alert marker
            position=(alert_lat, alert_lon),
            icon=icon,
            children=[dl.Popup(
                [
                    html.H2("Alerte détectée"),
                    html.P("Coordonées : {}, {} ".format(alert_lat, alert_lon)),

                    # Button allowing the user to check the detection data after clicking on an alert marker
                    html.Button("Afficher les données de détection",
                                id=({'type': 'display_alert_frame_btn', 'index': alert_id}),  # Setting a unique btn id
                                n_clicks=0,
                                className="btn btn-danger"),

                    # Adding a separator between the button and the checkbox
                    dcc.Markdown("---"),

                    # Alert acknowledgement checkbox with default value False and value True once checked
                    html.Div(id={'type': 'acknowledge_alert_div', 'index': alert_id},
                             children=[
                                 dbc.FormGroup([dbc.Checkbox(id={'type': 'acknowledge_alert_checkbox',
                                                                 'index': alert_id},
                                                             className="form-check-input"),
                                                dbc.Label("Confirmer la prise en compte de l'alerte",
                                                          className="form-check-label")],
                                               check=True,
                                               inline=True)])
                ])]))

    # Wrapping all markers in the list into a dl.LayerGroup object
    alerts_markers_layer = dl.LayerGroup(children=alerts_markers, id='alerts_markers')

    # Building the alerts notification btn
    nb_alerts = len(all_events)  # Number of unique events
    alert_button = html.Div(dbc.Button(
        "Nouvelles alertes | {}".format(nb_alerts), className="btn-header-alerts"),
        id=f'alert_button_{map_style}',
        style={'position': 'absolute', 'top': '10px', 'right': '30px', 'z-index': '1000'}
    )

    return alert_button, alerts_markers_layer, navbar_color, navbar_title


def build_user_alerts_selection_area(n_clicks, live_alerts):
    """
    This function builds the user selection area containing the alert list

    - it first sets the column sizes of each block (user area and map)
    - it creates the alerts_list based on live_alerts data

    To do so, it takes two arguments:
    - the number of clicks on the alert button;
    - the live_alerts data filling the alert_list
    """

    if n_clicks > 0:
        # Defining col width for both user selection area and map
        md_user = 3
        md_map = 9

        # Creating the alert_list based on live_alerts
        all_alerts = pd.read_json(live_alerts)
        all_events = all_alerts.drop_duplicates(['id', 'event_id']).groupby('event_id').head(1)  # Get unique events
        alert_list = []
        for _, row in all_events.iterrows():
            alert_id = str(row['event_id'])
            alert_lat = round(row['lat'], 4)
            alert_lon = round(row['lon'], 4)
            alert_azimtuth = round(row['azimuth'], 1)
            alert_date = datetime.fromisoformat(str(row['created_at'])).date()
            alert_time = datetime.fromisoformat(str(row['created_at'])).time()
            alert_list.append(html.Div([
                dcc.Markdown('---'),
                dbc.Button(children=[
                           html.Span('Azimuth : {}°'.format(alert_azimtuth), style={'font-weight': 'bold'}),
                           html.Span('Lat : {} / Lon : {}'.format(alert_lat, alert_lon), style={'display': 'block'}),
                           html.Span('Tour : ', style={'display': 'block'}),  # Not possible to fetch from alert today
                           html.Span('{} / {}:{}'.format(alert_date, alert_time.hour, alert_time.minute),
                                     style={'display': 'block'})],
                           id={'type': 'alert_selection_btn', 'index': alert_id},
                           className='btn-alerts'),
            ]))

        user_alerts_selection = [html.Div([
            dcc.Markdown('---'),
            html.H5(children="Nouvelles alertes !", style={'text-align': 'center'})]),
            dbc.Container(alert_list)]

        # Disabling alert_button
        alert_button_status = {'display': 'none'}

    else:
        md_user = 0
        md_map = 12
        user_alerts_selection = ""
        alert_button_status = {'display': 'block'}

    return md_user, md_map, user_alerts_selection, alert_button_status


# ----------------------------------------------------------------------------------------------------------------------
# Map instantiation
# The last block gathers previously defined functions to output the "Alerts and Infrastructure" map.

def build_alerts_map():
    """
    The following function mobilises functions defined hereabove or in the utils module to
    instantiate and return a dl.Map object, corresponding to the "Alerts and Infrastructure" view.
    """
    map_object = dl.Map(center=user_department_lat_lon(),  # Determines the point around which the map is centered
                        zoom=9,               # Determines the initial level of zoom around the center point
                        children=[
                            dl.TileLayer(id='tile_layer'),
                            build_departments_geojson(),
                            build_filters_object(map_type='alerts'),
                            build_legend_box(map_type='alerts'),
                            build_sites_markers(),
                            html.Div(id="live_alerts_marker"),
                            html.Div(id="live_alert_header_btn"),
                            html.Div(id='fire_markers_alerts')],  # Will contain the past fire markers of the alerts map
                        style=map_style,      # Reminder: map_style is imported from utils.py
                        id='map')

    return map_object
