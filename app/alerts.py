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

# Useful import to open local files (positions of cameras and department GeoJSON)
from pathlib import Path

# Pandas, to read the csv file with the positions of cameras on the field
import pandas as pd

# Useful import to read the GeoJSON file
import json

# Various modules provided by Dash to build app components
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import dash_leaflet.express as dlx

# Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_info_object, build_legend_box


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT

# ----------------------------------------------------------------------------------------------------------------------
# Departments
# The following block is used to display the borders of the departments on the map and to add interactivity.

def build_departments_geojson():
    """
    This function reads the departments.geojson file in the /data folder thanks to the json module
    and returns an interactive dl.GeoJSON object containing its information, to be displayed on the map.
    """

    # We read the json file in the data folder and store it in the departments variable
    with open(Path(__file__).parent.joinpath('data', 'departements.geojson'), 'rb') as response:
        departments = json.load(response)

    # We plug departments in a Dash Leaflet GeoJSON object that will be added to the map
    geojson = dl.GeoJSON(data=departments,
                         id='geojson_departments',
                         zoomToBoundsOnClick=True,
                         hoverStyle=dict(weight=3,
                                         color='#666',
                                         dashArray='')
                         )

    # We simply return the GeoJSON object for now
    return geojson


# ----------------------------------------------------------------------------------------------------------------------
# Sites markers
# The following block is used to fetch and display on the map the positions of detection units.

def build_sites_markers(dpt_code=None):
    """
    This function reads through the 'cameras.csv' file in the /data folder, that contains all the
    information about the sites equipped with detection units.

    It then returns a dl.MarkerClusterGroup object that gathers all relevant site markers.

    NB: certain parts of the function, which we do not use at the moment and that were initially
    designed to bind the display of site markers to a click on the corresponding department, are
    commented for now but could prove useful later on.
    """

    # As long as the user does not click on a department, dpt_code is None and we return no device
    # if not dpt_code:
    #     return None

    # We read the csv file that locates the cameras and filter for the department of interest
    camera_positions = pd.read_csv(Path(__file__).parent.joinpath('data', 'cameras.csv'), ';')
    # camera_positions = camera_positions[camera_positions['Département'] == int(dpt_code)].copy()

    # Building alerts_markers objects and wraps them in a dl.LayerGroup object
    icon = {
        "iconUrl": '../assets/pyro_site_icon.png',
        "iconSize": [50, 50],        # Size of the icon
        "iconAnchor": [25, 45],      # Point of the icon which will correspond to marker's location
        "popupAnchor": [0, -20]      # Point from which the popup should open relative to the iconAnchor
    }

    # We build a list of markers containing the info of each site/camera
    markers = []
    for i, row in camera_positions.iterrows():
        lat = row['Latitude']
        lon = row['Longitude']
        site_name = row['Tours']
        nb_device = row['Nombres Devices']
        markers.append(dl.Marker(id=f'site_{i}',    # Necessary to set an id for each marker to receive callbacks
                                 position=(lat, lon),
                                 icon=icon,
                                 children=[dl.Tooltip(site_name),
                                           dl.Popup([html.H2(f'Site {site_name}'),
                                                     html.P(f'Coordonnées : ({lat}, {lon})'),
                                                     html.P(f'Nombre de caméras : {nb_device}')])]))

    # We group all dl.Marker objects in a dl.MarkerClusterGroup object and return it
    return dl.MarkerClusterGroup(children=markers, id='sites_markers')


# ----------------------------------------------------------------------------------------------------------------------
# Fire alerts
# The following block is dedicated to fetching information about fire alerts and displaying them on the map.

def build_alerts_elements(img_url, alert_status, alert_metadata, map_style):
    """
    This function is used in the main.py file to create alerts-related elements such as the alert button (banner)
    or the alert markers on the map.

    It takes as arguments:

    - 'img_url': the URL address of the alert frame to be displayed on the left of the map;
    - 'alert_status': a binary variable indicating whether or not there is an ongoing alert to display;
    - 'alert_metadata': a dictionary containing;
    - 'map_style': the type of map in place, either 'alerts' or 'risks'.

    All these inputs are instantiated in the main.py file via a call to the API.

    In the base case, the function returns:

    - the URL address of the image to be displayed on the left of the map;
    - the alert button (banner above the map);
    - the alert markers displayed on the map.

    But if the style of map in place is 'risks', we don't want to display neither the alert markers.
    So in this case, the third output of the function is a void string.
    """

    # Fetching alert status and reusable metadata
    alert_lat = alert_metadata["lat"]
    alert_lon = alert_metadata["lon"]
    alert_id = str(alert_metadata["id"])

    if alert_status == 1:
        # Building the button that allows users to zoom towards the alert marker
        alert_button = dbc.Button(
            children="Départ de feu, cliquez-ici !",
            color="danger",
            block=True,
            id=f'alert_button_{map_style}'
        )

        # Format of the alert marker icon
        icon = {
            "iconUrl": '../assets/pyro_alert_icon.png',
            "iconSize": [50, 50],        # Size of the icon
            "iconAnchor": [25, 45],      # Point of the icon which will correspond to marker's and popup's location
            "popupAnchor": [0, -20]      # Point from which the popup should open relative to the iconAnchor
        }

        # Building the list of alert markers to be displayed
        alerts_markers = [dl.Marker(
            id="alert_marker_{}".format(alert_id),   # Setting a unique id for each alert marker
            position=(alert_lat, alert_lon),
            icon=icon,
            children=[dl.Popup(
                [
                    html.H2("Alerte détectée"),
                    html.P("Coordonées : {}, {} ".format(alert_lat, alert_lon)),

                    # Button allowing the user to check the detection data after clicking on an alert marker
                    html.Button("Afficher les données de détection",
                                id=("display_alert_frame_btn{}".format(alert_id)),  # Setting a unique btn id
                                n_clicks=0,
                                className="btn btn-danger"),

                    # Adding a separator between the button and the checkbow
                    dcc.Markdown("---"),

                    # Alert acknowledgement checkbox with default value False and value True once checked
                    html.Div(id='acknowledge_alert_div_{}'.format(alert_id),
                             children=[
                                dbc.FormGroup([dbc.Checkbox(id='acknowledge_alert_checkbox_{}'.format(alert_id),
                                                            className="form-check-input"),
                                               dbc.Label("Confirmer la prise en compte de l'alerte",
                                                         html_for='acknowledge_alert_checkbox_{}'.format(alert_id),
                                                         className="form-check-label")],
                                              check=True,
                                              inline=True)])
                ])])]

        # Wrapping all markers in the list into a dl.LayerGroup object
        alerts_markers_layer = dl.LayerGroup(children=alerts_markers, id='alerts_markers')

    else:
        alert_button = ""
        alerts_markers_layer = ""

    if map_style == 'risks':
        alerts_markers_layer = ''

    return img_url, alert_button, alerts_markers_layer


def define_map_zoom_center(n_clicks, alert_metadata):
    """
    This function has two purposes:

    - it first sets the default zoom and center parameters for the map;
    - it defines the parameters of the zoom triggered towards the alert marker
     when the user clicks on the alert button (banner above the map).

    To do so, it takes two arguments:
    - the number of clicks on the alert button;
    - the metadata dictionary linked to the corresponding alert.

    It returns coordinates around which to center the map and a zoom level.
    """

    # Fetching alert status and reusable metadata
    alert_lat = alert_metadata["lat"]
    alert_lon = alert_metadata["lon"]

    # Defining center and zoom parameters for the map object
    if n_clicks > 0:
        center = [alert_lat, alert_lon]
        zoom = 9
    else:
        center = [46.5, 2]
        zoom = 6

    return center, zoom


# ----------------------------------------------------------------------------------------------------------------------
# Map instantiation
# The last block gathers previously defined functions to output the "Alerts and Infrastructure" map.

def build_alerts_map():
    """
    The following function mobilises functions defined hereabove or in the utils module to
    instantiate and return a dl.Map object, corresponding to the "Alerts and Infrastructure" view.
    """
    map_object = dl.Map(center=[46.5, 2],     # Determines the point around which the map is initially centered
                        zoom=6,               # Determines the initial level of zoom around the center point
                        children=[
                            dl.TileLayer(id='tile_layer'),
                            build_departments_geojson(),
                            build_info_object(map_type='alerts'),
                            build_legend_box(map_type='alerts'),
                            build_sites_markers(),
                            html.Div(id="live_alerts_marker"),
                            html.Div(id='fire_markers_alerts')],  # Will contain the past fire markers of the alerts map
                        style=map_style,      # Reminder: map_style is imported from utils.py
                        id='map')

    return map_object
