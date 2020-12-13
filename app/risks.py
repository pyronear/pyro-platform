"""The following is dedicated to the "Niveaux de Risque" dashboard.

The main item is the RisksApp function that returns the corresponding page layout.
"""


# ------------------------------------------------------------------------------
# Imports

# NumPy to generate the random scores from 0 to 1 that we are using so far, as well as the classes
import numpy as np

# Useful imports to open and read the GeoJSON file, and to get risk data from the API
from pathlib import Path
import json
import requests

# Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx

# From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

# Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_info_object, build_legend_box


# ------------------------------------------------------------------------------
# Departments and color scale section (before moving to app layout)

# We fetch the json file online and store it in the departments variable
with open(Path(__file__).parent.joinpath('data', 'departements.geojson'), 'rb') as response:
    departments = json.load(response)

# We fetch the deparment risk score json and store it in the risk_json variable
# When FG finishes his PR, we'll be able to retrieve data from the API
# response = requests.get("http://pyro-risks.herokuapp.com/risk/fr/2020-09-01")
# risk_json = response.json()
with open(Path(__file__).parent.joinpath('data', 'risk.json'), 'rb') as risk:
    risk_json = json.load(risk)

# We add to each department in the geojson a new property called "score" that corresponds to the risk level
for department in departments['features']:
    dpt_name = department['properties']['nom']
    geocode_list = [dpt['geocode'] for dpt in risk_json]
    if dpt_name in geocode_list:
        risk_json_index = geocode_list.index(dpt_name) # We retrieve the index of the corresponding department in the risk_json object
        department['properties']['score'] = risk_json[risk_json_index]['score']
    else:
        department['properties']['score'] = 1


# Preparing the choropleth map, fetching the departments GeoJSON and building the related map attribute
def build_risks_geojson_and_colorbar(opacity_level=0.75):

    # First step is to prepare the choropleth map by building the color scale corresponding to score risks
    # To define 8 risk levels between 0 and 1, we need to choose 9 floats that will serve as borders
    classes = np.linspace(0, 1, 9)

    # We choose 8 shades of yellow and red to define our color scale
    colorscale = ['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026', '#800026']

    # We create a 'categories' object of the right format, then plug it into the Dash Leaflet
    # function instantiating the colorbar
    ctg = ["{}+".format(round(cls, 2)) for i, cls in enumerate(classes[:-1])]
    colorbar = dlx.categorical_colorbar(categories=ctg, colorscale=colorscale, width=500, height=30,
                                        position="bottomleft")

    # We define the style of department delimitations on the map
    # (opacity and color of borders, opacity of color backgrounds...)
    scale_style = dict(weight=2, opacity=0.9, color='white', dashArray='3', fillOpacity=opacity_level)

    # We finally instantiate the dl.GeoJSON object that will be attributed to the "Niveaux de Risque" map
    geojson = dl.GeoJSON(data=departments,
                         id='geojson_risks',
                         zoomToBoundsOnClick=True,
                         hoverStyle=dict(weight=3,
                                         color='#666',
                                         dashArray=''),
                         hideout=dict(colorscale=colorscale,
                                      classes=classes,
                                      style=scale_style,
                                      color_prop='score'),
                         options=dict(style=dlx.choropleth.style))

    return geojson, colorbar


# Building the slider that determines the color opacity level when displaying each department's level of risk
def build_opacity_slider():

    slider_title = dcc.Markdown("Choisissez le niveau d'opacité des aplats de couleurs :")

    slider = dcc.Slider(id='opacity_slider_risks',
                        min=0, max=1,
                        step=0.01,
                        marks={0: '0%', 0.25: '25%', 0.5: '50%', 0.75: '75%', 1: '100%'},
                        value=0.75)

    slider_div = html.Div(style=dict(width=330),
                          children=[slider_title, slider])

    return html.Center(slider_div)


# And we define one last function to gather all previous elements in a single map object
def build_risks_map():

    geojson, colorbar = build_risks_geojson_and_colorbar()

    map_object = dl.Map(center=[46.5, 2],          # Determines the point around which the map is initially centered
                        zoom=6,                    # Determines the initial level of zoom around the center point
                        children=[dl.TileLayer(id='tile_layer'),
                                  geojson,
                                  colorbar,
                                  build_info_object(app_page='risks'),
                                  build_legend_box(app_page='risks'),
                                  html.Div(id='fire_markers_risks')  # Will contain past fire markers of the risks map
                                  ],
                        style=map_style,           # Reminder: map_style is imported from utils.py
                        id='map')

    return map_object


# ------------------------------------------------------------------------------
# Page layout

def RisksApp():
    layout = [
        Navbar(),                   # Instantiating the navigation bar
        dcc.Markdown('---'),        # Adding a first separator between the navigation bar and the slider
        build_opacity_slider(),     # Instantiating the slider
        dcc.Markdown('---'),        # Adding a second separator between the navigation slider and the map
        build_risks_map()           # Instantiating the map object
    ]

    return html.Div(layout)
