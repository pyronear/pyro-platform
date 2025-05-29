# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


from datetime import datetime, timedelta
from io import StringIO
from typing import List, Tuple

import dash_leaflet as dl
import pandas as pd
import pytz
import requests
from dash import html
from geopy import Point
from geopy.distance import geodesic
from timezonefinder import TimezoneFinder

import config as cfg

DEPARTMENTS = requests.get(cfg.GEOJSON_FILE, timeout=10).json()


tf = TimezoneFinder()


def convert_dt_to_local_tz(lat, lon, str_utc_timestamp):
    """
    Convert a UTC timestamp string to a local timezone string based on latitude and longitude.

    Parameters:
    lat (float): Latitude of the location.
    lon (float): Longitude of the location.
    str_utc_timestamp (str): UTC timestamp string in ISO 8601 format (e.g., "2023-10-01T12:34:56").

    Returns:
    str: Local timezone string in the format "%Y-%m-%d %H:%M" or None if the input timestamp is invalid.

    Example:
    >>> convert_dt_to_local_tz(48.8566, 2.3522, "2023-10-01T12:34:56")
    '2023-10-01 14:34'
    """
    lat = round(lat, 4)
    lon = round(lon, 4)

    # Convert str_utc_timestamp to a timezone-aware datetime object assuming it's in UTC
    try:
        ts_utc = datetime.fromisoformat(str(str_utc_timestamp)).replace(tzinfo=pytz.utc)
    except ValueError:
        return None  # Handle invalid datetime format

    # Find the local timezone
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    if timezone_str is None:  # If the timezone is not found, handle it appropriately
        timezone_str = "UTC"  # Fallback to UTC
    timezone = pytz.timezone(timezone_str)

    # Convert ts_utc to the local timezone
    return ts_utc.astimezone(timezone).strftime("%Y-%m-%d %H:%M")


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
    x0, _, width, _ = bboxes[:4]
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

    api_cameras = pd.read_json(StringIO(api_cameras), orient="split")

    client_sites = api_cameras.drop_duplicates(subset=["lat", "lon"], keep="first")  # Keeps the first occurrence
    markers = []

    for _, site in client_sites.iterrows():
        lat = round(site["lat"], 4)
        lon = round(site["lon"], 4)
        site_name = site["name"][:-3].replace("_", " ").lower()
        markers.append(
            dl.Marker(
                id={"type": "site-marker", "index": site_name.lower()},
                position=(lat, lon),
                icon=icon,
                n_clicks=0,  # ✅ allows click tracking
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
    if bboxes is not None:
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

    filtered_events = api_events.sort_values("started_at").drop_duplicates("id", keep="last")[::-1]

    return [
        html.Button(
            id={"type": "event-button", "index": event["id"]},
            children=[
                html.Div(
                    (
                        f"{cameras[cameras['id'] == event['camera_id']]['name'].values[0][:-3].replace('_', ' ')}"
                        f" : {int(event['azimuth'])}°"
                    ),
                    style={"fontWeight": "bold"},
                ),
                html.Div(
                    convert_dt_to_local_tz(
                        lat=cameras[cameras["id"] == event["camera_id"]]["lat"].values[0],
                        lon=cameras[cameras["id"] == event["camera_id"]]["lon"].values[0],
                        str_utc_timestamp=event["started_at"],
                    )
                ),
            ],
            n_clicks=0,
            className="pyronear-card alert-card",
        )
        for _, event in filtered_events.iterrows()
    ]


def bboxes_overlap(b1, b2, iou_threshold=0.1):
    """
    Compute IoU (Intersection over Union) between two bboxes and return True if they overlap.
    Each bbox is a list: [x_min, y_min, x_max, y_max, score]
    """
    xA = max(b1[0], b2[0])
    yA = max(b1[1], b2[1])
    xB = min(b1[2], b2[2])
    yB = min(b1[3], b2[3])

    inter_area = max(0, xB - xA) * max(0, yB - yA)
    if inter_area == 0:
        return False

    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    iou = inter_area / float(area1 + area2 - inter_area)
    return iou > iou_threshold


def filter_bboxes_dict(bboxes_dict):
    """
    Filters the input dict of {timestamp: bbox}:
    - Keeps only bboxes < 60 days old
    - Removes overlaps by keeping the most recent bbox
    """
    if not bboxes_dict:
        return {}

    now = datetime.now()
    max_age = timedelta(days=60)

    # Parse, filter old
    items = [
        (datetime.strptime(k, "%Y-%m-%d %H:%M:%S"), k, v)
        for k, v in bboxes_dict.items()
        if now - datetime.strptime(k, "%Y-%m-%d %H:%M:%S") <= max_age
    ]

    # Sort by timestamp descending (most recent first)
    items.sort(reverse=True)

    kept: List[Tuple[str, list[float]]] = []
    kept_dict = {}

    for _, k, bbox in items:
        if not any(bboxes_overlap(bbox, other_bbox) for _, other_bbox in kept):
            kept.append((k, bbox))
            kept_dict[k] = bbox

    return kept_dict
