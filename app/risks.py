# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following file is dedicated to the "Risk Score" view of the dashboard.

Following a first section dedicated to imports, the content section is made of 3 blocks:

- the departments and risk score acquisition block, used to fetch the scores of each department;
- the choropleth map attributes block, which constructs the dl.GeoJSON object, as well as the color scale;
- a final block mobilising previously defined functions to instantiate the "Risk Score" map.

Most functions defined below are called in the main.py file, in the risks callbacks.
"""


# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# NumPy to generate the score classes in the color scale
import numpy as np

# Useful imports to open and read the GeoJSON file and get risk data from the API
import requests
import config as cfg

# Various modules provided by Dash to build app components
from dash import dcc
import dash_html_components as html
import dash_leaflet as dl
import dash_leaflet.express as dlx

# Various imports from utils.py, useful for both Alerts and Risks dashboards
from utils import map_style, build_filters_object, build_legend_box


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT

# ----------------------------------------------------------------------------------------------------------------------
# Departments and risk score acquisition
# The following block fetches risk scores from the data science team and adds them up to the departments geojson.
# NB: for now, scores are acquired from a static json file on GitHub; the API call is still to be implemented.

# We read the GeoJSON file from the Pyro-Risk release (URL in config.py) and store it in the departments variable
departments = requests.get(cfg.GEOJSON_FILE).json()

# We fetch the department risk score json and store it in the risk_json variable
# When everything is validated, we'll request the data directly from the API
risk_json = requests.get(cfg.PYRORISK_FALLBACK).json()

# We add to each department in the geojson a new property called "score" that corresponds to the risk level
for department in departments['features']:
    dpt_name = department['properties']['nom']
    geocode_list = [dpt['geocode'] for dpt in risk_json]

    if dpt_name in geocode_list:
        risk_json_index = geocode_list.index(dpt_name)
        department['properties']['score'] = risk_json[risk_json_index]['score']

    else:
        department['properties']['score'] = 0


# ----------------------------------------------------------------------------------------------------------------------
# Choropleth map attributes
# The following block is used to instantiate the various Dash Leaflet objects needed to build the choropleth map.

def build_risks_geojson_and_colorbar(opacity_level=0.75):
    """
    This function creates the main attributes specific to the choropleth map.

    It simply takes as input an opacity level, which defaults to 0.75, for coloring the departments.

    It returns:

    - a dl.GeoJSON object that allows to displays the departments' boundaries and respective risk score categories;
    - a colorbar object that distinguishes, as shades of yellow and red, 8 categories of risk score from 0 to 1.
    """

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


def build_opacity_slider():
    """
    This function instantiates the slider located in the blank space on the left of the map,
    that allows the user to choose the most appropriate color opacity level when displaying
    the risk score associated with the various departments.
    """

    slider_title = dcc.Markdown("Choisissez le niveau d'opacité des aplats de couleurs :")

    slider = dcc.Slider(id='opacity_slider_risks',
                        min=0, max=1,
                        step=0.01,
                        marks={0: '0%', 0.25: '25%', 0.5: '50%', 0.75: '75%', 1: '100%'},
                        value=0.75)

    slider_div = html.Div(style=dict(width=330),
                          children=[slider_title, slider])

    return html.Center(slider_div)


# ----------------------------------------------------------------------------------------------------------------------
# Map instantiation
# The last block gathers previously defined functions to output the "Risk Score" map.

def build_risks_map():
    """
    This function mobilises functions defined hereabove or in the utils module to
    instantiate and return a dl.Map object, corresponding to the "Risk Score" view.
    """

    geojson, colorbar = build_risks_geojson_and_colorbar()

    map_object = dl.Map(center=[46.5, 2],          # Determines the point around which the map is initially centered
                        zoom=6,                    # Determines the initial level of zoom around the center point
                        children=[dl.TileLayer(id='tile_layer'),
                                  geojson,
                                  colorbar,
                                  build_filters_object(map_type='risks'),
                                  build_legend_box(map_type='risks'),
                                  html.Div(id='fire_markers_risks'),  # Will contain past fire markers of the risks map
                                  html.Div(id='live_alerts_marker')
                                  ],
                        style=map_style,           # Reminder: map_style is imported from utils.py
                        id='map')

    return map_object
