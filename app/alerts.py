"""The following is dedicated to the "Alertes et Infrastructures" dashboard.

The main item is the AlertsApp function that returns the corresponding page layout.
"""


# ------------------------------------------------------------------------------
# Imports

# Useful import to open local files (positions of cameras and department GeoJSON)
from pathlib import Path

# Pandas, to read the csv file with the positions of cameras on the field
import pandas as pd

# Useful import to read the GeoJSON file
import json

# Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx

# From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

# Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_info_object


# ------------------------------------------------------------------------------
# Map layer
# The following block is used to determine what layer we use for the map and enable the user to change it

# This function creates the button that allows users to change the map layer (satellite or topographic)
def build_layer_style_button():

    button = html.Button(children='Activer la vue satellite',
                         id='layer_style_button')

    return html.Center(button)


# This function takes as input the number of clicks on the button defined above and returns the layer style to use
def choose_layer_style(n_clicks):

    # Because we start with the topographic view, if the number of clicks is even, this means that
    # we are still using the topographic view and we may want to activate the satellite one
    if n_clicks % 2 == 0:
        button_content = 'Activer la vue satellite'
        layer_url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        layer_attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

    # If the number of clicks is odd, this means we are using the satellite view and may
    # want to come back to the topographic one
    else:
        button_content = 'Revenir à la vue schématique'
        layer_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        layer_attribution = ("Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, "
                             "Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community")

    return button_content, layer_url, layer_attribution


# ------------------------------------------------------------------------------
# Departments
# The following block is used to display the borders of the departments on the map

# Fetching the departments GeoJSON and building the related map attribute
def build_alerts_geojson():

    # We fetch the json file online and store it in the departments variable
    with open(Path(__file__).parent.joinpath('data', 'departements.geojson'), 'rb') as response:
        departments = json.load(response)

    # We plug departments in a Dash Leaflet GeoJSON object that will be added to the map
    geojson = dl.GeoJSON(data=departments,
                         id='geojson_alerts',
                         zoomToBoundsOnClick=True,
                         hoverStyle=dict(weight=3,
                                         color='#666',
                                         dashArray='')
                         )

    # We simply return the GeoJSON object for now
    return geojson


# ------------------------------------------------------------------------------
# Cameras
# The following block is dedicated to fetching information about cameras and displaying them on the map

# Fetching the positions of detection units in a given department
def get_camera_positions(dpt_code=None):

    # As long as the user does not click on a department, dpt_code is None and we return no device
    if not dpt_code:
        return None

    # We read the csv file that locates the cameras and filter for the department of interest
    camera_positions = pd.read_csv(Path(__file__).parent.joinpath('data', 'cameras.csv'), ';')
    camera_positions = camera_positions[camera_positions['Département'] == int(dpt_code)].copy()

    # We build a list of dictionaries containing the info of each camera
    markers = []
    for _, row in camera_positions.iterrows():
        lat = row['Latitude']
        lon = row['Longitude']
        area = row['Tours']
        alert_codis = row['Connexion Alerte CODIS']
        nb_device = row['Nombres Devices']
        popup = ["Ville: {} <br>\
                 Connexion Alerte CODIS: {} <br>\
                 Nombres Devices: {}".format(area, alert_codis, nb_device)]
        markers.append(dict(lat=lat,
                            lon=lon,
                            area=area,
                            alert_codis=alert_codis,
                            nb_device=nb_device,
                            popup=popup))

    # We convert it into geojson format (not a dl.GeoJSON object yet) and return it
    markers = dlx.dicts_to_geojson(markers)

    return markers


# Once we have the positions of cameras, we output another GeoJSON object gathering these locations
def build_alerts_markers():
    markers = dl.GeoJSON(data=get_camera_positions(),
                         id='markers')

    return markers


# ------------------------------------------------------------------------------
# Page layout
# The last block gathers previously defined functions to output the layout of the alerts dashboard

# The following function gathers all previous elements in a single map object
def build_alerts_map():

    map_object = dl.Map(center=[46.5, 2],     # Determines the point around which the map is initially centered
                        zoom=6,               # Determines the initial level of zoom around the center point
                        children=[
                            dl.TileLayer(id='tile_layer'),
                            build_alerts_geojson(),
                            build_info_object(app_page='alerts'),
                            build_alerts_markers()],
                        style=map_style,      # Reminder: map_style is imported from utils.py
                        id='map')

    return map_object


# This function will be used in the main.py file to instantiate the layout of the alerts dashboard
def AlertsApp():
    layout = [Navbar(),                     # Instantiating the navigation bar
              dcc.Markdown('---'),          # Adding a first separator between the navigation bar and the button
              build_layer_style_button(),   # Instantiating the button to change the map layer style
              dcc.Markdown('---'),          # Adding a second separator between the button and the map
              build_alerts_map()]           # Finally instantiating the map object

    return html.Div(layout)
