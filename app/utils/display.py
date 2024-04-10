# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from datetime import datetime

import dash_leaflet as dl
import pytz
import requests
from dash import html
from geopy import Point
from geopy.distance import geodesic
from timezonefinder import TimezoneFinder

import config as cfg
from services import api_client
from utils.sites import get_sites

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
    """
    This function compute the vision polygon parameters based on localization
    """
    # Assuming localization is in the format [x0, y0, x1, y1, confidence]
    x0, _, width, _ = localization
    xc = (x0 + width / 2) / 100

    # New azimuth
    new_azimuth = azimuth - opening_angle * (0.5 - xc)

    # New opening angle
    new_opening_angle = opening_angle * width / 100 + 1  # avoid angle 0

    return int(new_azimuth), int(new_opening_angle)


def build_sites_markers(user_headers, user_credentials):
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

    user_token = user_headers["Authorization"].split(" ")[1]
    api_client.token = user_token

    client_sites = get_sites(user_credentials)
    markers = []

    for _, site in client_sites.iterrows():
        site_id = site["id"]
        lat = round(site["lat"], 4)
        lon = round(site["lon"], 4)
        site_name = site["name"].replace("_", " ").title()
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
    return markers


def build_vision_polygon(site_lat, site_lon, azimuth, opening_angle, dist_km, localization=None):
    """
    Create a vision polygon using dl.Polygon. This polygon is placed on the map using alerts data.
    """
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


def build_alerts_map(user_headers, user_credentials, id_suffix=""):
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
            dl.MarkerClusterGroup(children=build_sites_markers(user_headers, user_credentials), id="sites_markers"),
        ],  # Will contain the past fire markers of the alerts map
        style=map_style,  # Reminder: map_style is imported from utils.py
        id=f"map{id_suffix}",
    )

    return map_object


def create_event_list_from_df(api_events):
    """
    This function build the list of events on the left based on event data
    """
    if api_events.empty:
        return []
    tf = TimezoneFinder()
    alert_ts_local = []
    for _, row in api_events.iterrows():
        alert_lat = round(row["lat"], 4)
        alert_lon = round(row["lon"], 4)

        # Convert created_at to a timezone-aware datetime object assuming it's in UTC
        alert_ts_utc = datetime.fromisoformat(str(row["created_at"])).replace(tzinfo=pytz.utc)

        # Find the timezone for the alert location
        timezone_str = tf.timezone_at(lat=alert_lat, lng=alert_lon)
        if timezone_str is None:  # If the timezone is not found, handle it appropriately
            timezone_str = "UTC"  # Fallback to UTC or some default
        alert_timezone = pytz.timezone(timezone_str)

        # Convert alert_ts_utc to the local timezone of the alert
        alert_ts_local.append(alert_ts_utc.astimezone(alert_timezone))

    api_events["created_at"] = alert_ts_local
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
                "margin": "10px",
                "padding": "10px",
                "borderRadius": "20px",
                "width": "100%",
            },
        )
        for _, event in filtered_events.iterrows()
    ]
