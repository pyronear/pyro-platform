"""The following is dedicated to the "Niveaux de Risque" dashboard.

The main item is the RisksApp function that returns the corresponding page layout.
"""


# ------------------------------------------------------------------------------
# Imports

### NumPy to generate the random scores from 0 to 1 that we are using so far
import numpy as np

### Useful import to read the GeoJSON file
import json

### Various modules provided by Dash to build the page layout
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx

### From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

### Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_info_object


# ------------------------------------------------------------------------------
# Before moving to app layout

# Preparing the choropleth map, fetching the departments GeoJSON and building the related map attribute
def build_risks_geojson_and_colorbar():

    ## First step is to prepare the choropleth map by building the color scale corresponding to score risks
    ### To define 8 risk levels between 0 and 1, we need to choose 9 floats that will serve as borders
    classes = np.linspace(0, 1, 9)

    ### We choose 8 shades of yellow and red to define our color scale
    colorscale = ['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026', '#800026']

    ### We create a 'categories' object of the right format, then plug it into the Dash Leaflet function instantiating the colorbar
    ctg = ["{}+".format(round(cls, 2)) for i, cls in enumerate(classes[:-1])]
    colorbar = dlx.categorical_colorbar(categories = ctg, colorscale = colorscale, width = 500, height = 30, position = "bottomleft")

    ### We define the style of department delimitations on the map (opacity and color of borders, opacity of color backgrounds...)
    scale_style = dict(weight = 2, opacity = 0.9, color = 'white', dashArray = '3', fillOpacity = 0.7)


    ## We fetch the json file online and store it in the departments variable
    with open('data/departements.geojson') as response:
        departments = json.load(response)

    ## We add to each department in the geojson a new property called "score" that corresponds to the random risk level
    for department in departments['features']:
        department['properties']['score'] = np.random.rand()


    ## We finally instantiate the dl.GeoJSON object that will be attributed to the "Niveaux de Risque" map
    geojson = dl.GeoJSON(
                         data = departments,
                         id = 'geojson_risks',
                         zoomToBoundsOnClick = True,
                         hoverStyle = dict(
                                           weight = 3,
                                           color = '#666',
                                           dashArray = ''
                                           ),
                         hideout = dict(
                                        colorscale = colorscale,
                                        classes = classes,
                                        style = scale_style,
                                        color_prop = 'score'
                                        ),
                         options = dict(style = dlx.choropleth.style)
                         )

    return geojson, colorbar


# And we define one last function to gather all previous elements in a single map object
def build_risks_map():

    geojson, colorbar = build_risks_geojson_and_colorbar()

    map_object = dl.Map(
                        center = [46.5, 2],          # Determines the point around which the map is initially centered
                        zoom = 6,                    # Determines the initial level of zoom around the center point
                        children = [
                                    dl.TileLayer(),
                                    geojson,
                                    colorbar,
                                    build_info_object(app_page = 'risks')
                                    ],
                        style = map_style,           # Reminder: map_style is imported from utils.py
                        id = 'map'
                        )

    return map_object

# ------------------------------------------------------------------------------
# App layout

# Instantiating the navigation bar
nav = Navbar()

# Instantiating the map object
map_object = build_risks_map()

# Gathering all these elements in a HTML Div and having it returned by the RisksApp function
def RisksApp():
    layout = [
              nav,
              map_object
              ]

    return html.Div(layout)



