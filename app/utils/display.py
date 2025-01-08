# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_leaflet as dl
import requests
from dash import html
from geopy import Point
from geopy.distance import geodesic

import config as cfg
from utils.data import read_stored_DataFrame

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


def build_sites_markers(api_cameras):
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

    api_cameras, _ = read_stored_DataFrame(api_cameras)

    client_sites = api_cameras.drop_duplicates(subset=["lat", "lon"], keep="first")  # Keeps the first occurrence
    markers = []

    for _, site in client_sites.iterrows():
        site_id = site["id"]
        lat = round(site["lat"], 4)
        lon = round(site["lon"], 4)
        site_name = site["name"][:-3].replace("_", " ").title()
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
    return markers, client_sites


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


def build_alerts_map(api_cameras, id_suffix=""):
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

    markers, client_sites = build_sites_markers(api_cameras)

    map_object = dl.Map(
        center=[
            client_sites["lat"].median(),
            client_sites["lon"].median(),
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


def create_event_list_from_alerts(api_events, cameras):
    """
    This function build the list of events on the left based on event data
    """
    if api_events.empty:
        return []
    filtered_events = api_events.sort_values("created_at").drop_duplicates("event_id", keep="last")[::-1]

    return [
        html.Button(
            id={"type": "event-button", "index": event["event_id"]},
            children=[
                html.Div(
                    f"{cameras[cameras["id"] == event["camera_id"]]['name'].values[0][:-3].replace('_', ' ')} : {int(event['azimuth'])}°",
                    style={"fontWeight": "bold"},
                ),
                html.Div(event["created_at"].strftime("%Y-%m-%d %H:%M")),
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
        for _, event in filtered_events.iterrows()
    ]
