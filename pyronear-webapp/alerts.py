'''
This file is dedicated to the "Alertes et Infrastructures" dashboard.
The main item is the AlertsApp function that returns the corresponding page layout.
'''


# ------------------------------------------------------------------------------
# Imports

### Pandas, to read the csv file with positions of  cameras on the field
import pandas as pd

### Useful imports to fetch the departments GeoJSON online and read it
from urllib.request import urlopen
import json

### Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx

### From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

### Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_info_object


# ------------------------------------------------------------------------------
# Before moving to app layout

# The following block is used to determine what layer we use for the map and enable the user to change it
## This function creates the button that allows users to change the map layer (satellite or topographic)
def build_layer_style_button():

    button = html.Button(
                         children = 'Activer la vue satellite',
                         id = 'layer_style_button'
                         )

    return html.Center(button)

## This function takes as input the number of clicks on the button defined above and returns the layer style to use
def choose_layer_style(n_clicks):

    ### Because we start with the topographic view, if the number of clicks is even, this means that
    ### we are still using the topographic view and we may want to activate the satellite one
    if n_clicks % 2 == 0:
        button_content = 'Activer la vue satellite'
        layer_url = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        layer_attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

    ### If the number of clicks is odd, this means we are using the satellite view and may want to come back to the topographic one
    else:
        button_content = 'Revenir à la vue schématique'
        layer_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
        layer_attribution = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'

    return button_content, layer_url, layer_attribution


# Fetching the departments GeoJSON and building the related map attribute
def build_alerts_geojson():

    ### We fetch the json file online and store it in the departments variable
    with urlopen('https://france-geojson.gregoiredavid.fr/repo/departements.geojson') as response:
        departments = json.load(response)

    ### We plug departments in a Dash Leaflet GeoJSON object that will be added to the map
    geojson = dl.GeoJSON(
                         data = departments,
                         id = 'geojson_alerts',
                         zoomToBoundsOnClick = True,
                         hoverStyle = dict(
                                           weight = 3,
                                           color = '#666',
                                           dashArray = ''
                                           )
                         )

    ### We simply return the GeoJSON object for now
    return geojson


# Fetching the positions of cameras on the field and building the related map attribute
## Fetching the positions of detection units in a given department
def get_camera_positions(dpt_code = None):

    ### As long as the user does not click on a department, dpt_code is None and we return no device
    if not dpt_code:
        return None

    ### We read the csv file that locates the cameras and filter for the department of interest
    camera_positions = pd.read_csv('data/cameras.csv', ';')
    camera_positions = camera_positions[camera_positions['Département'] == int(dpt_code)].copy()

    ### We build a list of dictionaries containing the coordinates of each camera
    markers = []
    for idx, row in camera_positions.iterrows():
        lat = row['Latitude']
        lon = row['Longitude']
        markers.append(dict(lat = lat, lon = lon))

    ### We convert it into geojson format (not a dl.GeoJSON object yet) and return it
    markers = dlx.dicts_to_geojson(markers)

    return markers

## Once we have the positions of cameras, we output another GeoJSON object gathering these locations
def build_alerts_markers():
    markers = dl.GeoJSON(
                         data = get_camera_positions(),
                         id = 'markers'
                         )

    return markers


# And we define one last function to gather all previous elements in a single map object
def build_alerts_map():

    map_object = dl.Map(
                        center = [46.5, 2],     # Determines the point around which the map is initially centered
                        zoom = 6,               # Determines the initial level of zoom around the center point
                        children = [
                                    dl.TileLayer(
                                                 id = 'alerts_tile_layer'
                                                 ),
                                    build_alerts_geojson(),
                                    build_info_object(app_page = 'alerts'),
                                    build_alerts_markers()
                                    ],
                        style = map_style,      # Reminder: map_style is imported from utils.py
                        id = 'map'
                        )

    return map_object


# ------------------------------------------------------------------------------
# App layout (finally!)

# Instantiating the navigation bar
nav = Navbar()

# Adding a first separator between the navigation bar and the button
space = dcc.Markdown('---')

# Instantiating the button to change the map layer style
layer_style_button = build_layer_style_button()

# Adding a second separator between the button and the map
separator = dcc.Markdown('---')

# Finally instantiating the map object
map_object = build_alerts_map()

# Gathering all these elements in a HTML Div and having it returned by the AlertsApp function
def AlertsApp():
    layout = [
              nav,
              space,
              layer_style_button,
              separator,
              map_object
              ]

    return html.Div(layout)


