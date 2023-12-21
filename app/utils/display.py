# Copyright (C) 2020-2023, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_leaflet as dl
import pandas as pd
import requests
from dash import html
from geopy import Point
from geopy.distance import geodesic

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


def calculate_new_polygon_parameters(azimuth, opening_angle, localization):
    # Assuming localization is in the format [x0, y0, x1, y1, confidence]
    x0, _, width, _ = localization
    xc = (x0 + width / 2) / 100

    # New azimuth
    new_azimuth = azimuth - opening_angle * (0.5 - xc)

    # New opening angle
    new_opening_angle = opening_angle * width / 100 + 1  # avoid angle 0

    return int(new_azimuth), int(new_opening_angle)


def build_vision_polygon(site_lat, site_lon, azimuth, opening_angle, dist_km, localization=None):
    if len(localization):
        azimuth, opening_angle = calculate_new_polygon_parameters(azimuth, opening_angle, localization[0])

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

    return polygon


def build_alerts_map(id_suffix=""):
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

    map_object = dl.Map(
        center=[44.73, 4.27],  # Determines the point around which the map is centered
        zoom=10,  # Determines the initial level of zoom around the center point
        children=[
            dl.TileLayer(id=f"tile_layer{id_suffix}"),
            build_departments_geojson(),
            dl.LayerGroup(id=f"vision_polygons{id_suffix}"),
        ],  # Will contain the past fire markers of the alerts map
        style=map_style,  # Reminder: map_style is imported from utils.py
        id=f"map{id_suffix}",
    )

    return map_object


def create_event_list_from_df(api_events):
    api_events["created_at"] = pd.to_datetime(api_events["created_at"])
    filtered_events = api_events.sort_values("created_at").drop_duplicates("id", keep="last")[::-1]

    return [
        html.Button(
            id={"type": "event-button", "index": event["id"]},
            children=[
                html.Div(
                    f"{event['device_name']}",
                    style={"fontWeight": "bold"},
                ),
                html.Div(event["created_at"].strftime("%Y-%m-%d %H:%M")),
            ],
            n_clicks=0,
            style={
                "backgroundColor": "#FC816B",
                "margin": "10px 15px 10px 10px",  # Adjust the right margin as needed
                "padding": "10px",
                "borderRadius": "5px",
                "width": "calc(100% - 25px)",  # Adjust the total width calculation if needed
                "border": "1px solid #ddd",
                "box-sizing": "border-box",  # Include padding and border in the width
                "textAlign": "left",
            },
        )
        for _, event in filtered_events.iterrows()
    ]
