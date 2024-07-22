# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_leaflet as dl
import pandas as pd
import requests
from dash import html
from geopy import Point
from geopy.distance import geodesic
from pyroclient import Client

import config as cfg

DEPARTMENTS = requests.get(cfg.GEOJSON_FILE, timeout=10).json()


def build_departments_geojson():
    """
    This function reads the departments.geojson file in the /data folder thanks to the json module
    and returns an interactive dl.GeoJSON object containing its information, to be displayed on the map.
    """
    # We plug departments in a Dash Leaflet GeoJSON object that will be added to the map
    geojson = dl.GeoJSON(
        data=DEPARTMENTS,
        id="geojson_departments",
        zoomToBoundsOnClick=False,
        hoverStyle={"weight": 3, "color": "#666", "dashArray": ""},
    )

    # We simply return the GeoJSON object for now
    return geojson


def calculate_new_polygon_parameters(azimuth, opening_angle, bboxes):
    """
    This function compute the vision polygon parameters based on bboxes
    """
    # Assuming bboxes is in the format [x0, y0, x1, y1, confidence]
    x0, _, width, _ = bboxes
    xc = (x0 + width / 2) / 100

    # New azimuth
    new_azimuth = azimuth - opening_angle * (0.5 - xc)

    # New opening angle
    new_opening_angle = opening_angle * width / 100 + 1  # avoid angle 0

    return int(new_azimuth) % 360, int(new_opening_angle)


def build_cameras_markers(token: str):
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
        "iconUrl": "../assets/images/pyro_site_icon.png",
        "iconSize": [50, 50],  # Size of the icon
        "iconAnchor": [25, 45],  # Point of the icon which will correspond to marker's location
        "popupAnchor": [0, -20],  # Point from which the popup should open relative to the iconAnchor
    }

    cameras = pd.DataFrame(Client(token, cfg.API_URL).fetch_cameras().json())

    markers = []

    for _, camera in cameras.iterrows():
        site_id = camera["id"]
        lat = round(camera["lat"], 4)
        lon = round(camera["lon"], 4)
        site_name = camera["name"].replace("_", " ").title()
        markers.append(
            dl.Marker(
                id=f"site_{site_id}",  # Necessary to set an id for each marker to receive callbacks
                position=(lat, lon),
                icon=icon,
                children=[
                    dl.Tooltip(site_name),
                    dl.Popup(
                        [
                            html.H2(f"Site {site_name}"),
                            html.P(f"Coordonnées : ({lat}, {lon})"),
                        ]
                    ),
                ],
            )
        )

    # We group all dl.Marker objects in a dl.MarkerClusterGroup object and return it
    return markers, cameras


def build_vision_polygon(site_lat, site_lon, azimuth, opening_angle, dist_km, bboxes=None):
    """
    Create a vision polygon using dl.Polygon. This polygon is placed on the map using alerts data.
    """
    if len(bboxes):
        azimuth, opening_angle = calculate_new_polygon_parameters(azimuth, opening_angle, bboxes[0])

    # The center corresponds the point from which the vision angle "starts"
    center = [site_lat, site_lon]

    points1 = []
    points2 = []

    for i in reversed(range(1, opening_angle + 1)):
        azimuth1 = (azimuth - i / 2) % 360
        azimuth2 = (azimuth + i / 2) % 360

        point = geodesic(kilometers=dist_km).destination(Point(site_lat, site_lon), azimuth1)
        points1.append([point.latitude, point.longitude])

        point = geodesic(kilometers=dist_km).destination(Point(site_lat, site_lon), azimuth2)
        points2.append([point.latitude, point.longitude])

    points = [center, *points1, *list(reversed(points2))]

    polygon = dl.Polygon(
        id="vision_polygon",
        color="#ff7800",
        opacity=0.5,
        positions=points,
    )

    return polygon, azimuth


def build_detections_map(client_token, id_suffix=""):
    """
    The following function mobilises functions defined hereabove or in the utils module to
    instantiate and return a dl.Map object, corresponding to the "Alerts and Infrastructure" view.
    """
    map_style = {
        "position": "absolute",
        "top": 0,
        "left": 0,
        "width": "100%",
        "height": "100%",
    }

    markers, cameras = build_cameras_markers(client_token)

    map_object = dl.Map(
        center=[
            cameras["lat"].median(),
            cameras["lon"].median(),
        ],  # Determines the point around which the map is centered
        zoom=10,  # Determines the initial level of zoom around the center point
        children=[
            dl.TileLayer(id=f"tile_layer{id_suffix}"),
            build_departments_geojson(),
            dl.LayerGroup(id=f"vision_polygons{id_suffix}"),
            dl.MarkerClusterGroup(children=markers, id="sites_markers"),
        ],  # Will contain the past fire markers of the alerts map
        style=map_style,  # Reminder: map_style is imported from utils.py
        id=f"map{id_suffix}",
    )

    return map_object


def create_wildfire_list_from_df(wildfires):
    """
    This function build the list of wildfires on the left based on wildfire data
    """
    if wildfires.empty:
        return []

    filtered_wildfires = wildfires.sort_values("created_at").drop_duplicates("id", keep="last")[::-1]

    return [
        html.Button(
            id={"type": "wildfire-button", "index": wildfire["id"]},
            children=[
                html.Div(
                    f"{wildfire['camera_name']}",
                    style={"fontWeight": "bold"},
                ),
                html.Div(wildfire["created_at"].strftime("%Y-%m-%d %H:%M")),
            ],
            n_clicks=0,
            style={
                "backgroundColor": "#FC816B",
                "margin": "10px",
                "padding": "10px",
                "borderRadius": "20px",
                "width": "100%",
            },
        )
        for _, wildfire in filtered_wildfires.iterrows()
    ]
