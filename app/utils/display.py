# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json
from datetime import datetime
from io import StringIO

import dash
import dash_leaflet as dl
import pandas as pd
import pytz
import requests
from dash import html
from dash.exceptions import PreventUpdate
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

    api_cameras = pd.read_json(StringIO(api_cameras), orient="split")

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


def create_event_list_from_alerts(api_events, cameras, id_suffix=""):
    """
    This function build the list of events on the left based on event data
    """
    if api_events.empty:
        return []

    filtered_events = api_events.sort_values("started_at").drop_duplicates("id", keep="last")[::-1]

    return [
        html.Button(
            id={"type": f"event-button{id_suffix}", "index": event["id"]},
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


def select_event_with_button(n_clicks, button_ids, api_sequences, sequence_id_on_display, logger):
    """
    Handles event selection through button clicks.

    Parameters:
    - n_clicks (list): List of click counts for each event button.
    - button_ids (list): List of button IDs corresponding to events.
    - local_alerts (json): JSON formatted data containing current alert information.
    - sequence_id_on_display (int): Currently displayed event ID.

    Returns:
    - list: List of styles for event buttons.
    - int: ID of the event to display.
    - int: Number of clicks for the auto-move button reset.
    """
    logger.info("select_event_with_button")
    ctx = dash.callback_context

    api_sequences = pd.read_json(StringIO(api_sequences), orient="split")
    if api_sequences.empty:
        return [[], 0, 1, "reset_zoom"]

    # Extracting the index of the clicked button
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id:
        button_index = json.loads(button_id)["index"]
    else:
        if len(button_ids):
            button_index = button_ids[0]["index"]
        else:
            button_index = 0

    # Highlight the button
    styles = []
    for button in button_ids:
        if button["index"] == button_index:
            styles.append(
                {
                    "backgroundColor": "#feba6a",
                },
            )  # Highlight style
        else:
            styles.append(
                {},
            )  # Default style

    return [styles, button_index, 1, "reset_zoom"]


def toggle_bbox_visibility(n_clicks, button_style, logger):
    """
    Toggles the visibility of the bounding box and updates the button style accordingly.

    Parameters:
    - n_clicks (int): Number of clicks on the hide/show button.
    - button_style (dict): Current style of the hide/show button.

    Returns:
    - dict: Updated style for the bounding box.
    - dict: Updated style for the hide/show button.
    """
    logger.info("toggle_bbox_visibility")
    if n_clicks % 2 == 0:
        bbox_style = {"display": "block"}  # Show the bounding box
        button_style["background-color"] = "#054546"  # Original button color
    else:
        bbox_style = {"display": "none"}  # Hide the bounding box
        button_style["background-color"] = "#098386"  # Darker color for the button

    return bbox_style, button_style


def toggle_auto_move(n_clicks, data, button_style, logger):
    """
    Toggles the automatic movement of the image slider based on button clicks.

    Parameters:
    - n_clicks (int): Number of clicks on the auto-move button.
    - data (dict): Data about the current auto-move state.

    Returns:
    - dict: Updated auto-move state data.
    """
    if n_clicks % 2 == 0:  # Toggle between on and off states
        data["active"] = False
        button_style["background-color"] = "#098386"  # Darker color for the button

    else:
        data["active"] = True
        button_style["background-color"] = "#054546"  # Original button color
    return data, button_style


def auto_move_slider(n_intervals, current_value, max_value, auto_move_clicks, sequence_list):
    """
    Automatically moves the image slider based on a regular interval and the current auto-move state.

    Parameters:
    - n_intervals (int): Number of intervals passed since the start of the auto-move.
    - current_value (int): Current value of the image slider.
    - max_value (int): Maximum value of the image slider.
    - auto_move_clicks (int): Number of clicks on the auto-move button.
    - sequence_list (list): List of ongoing alerts.

    Returns:
    - int: Updated value for the image slider.
    """
    if auto_move_clicks % 2 != 0 and len(sequence_list):  # Auto-move is active and there is ongoing alerts
        return (current_value + 1) % (max_value + 1)
    else:
        raise PreventUpdate


def update_download_link(slider_value, sequence_on_display, logger):
    """
    Updates the download link for the currently displayed image.

    Parameters:
    - slider_value (int): Current value of the image slider.
    - alert_data (json): JSON formatted data for the selected event.

    Returns:
    - str: URL for downloading the current image.
    """
    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")
    if len(sequence_on_display):
        try:
            return sequence_on_display["url"].values[slider_value]
        except Exception as e:
            logger.info(e)
            logger.info(f"Size of the alert_data dataframe: {sequence_on_display.size}")

    return ""  # Return empty string if no image URL is available


def update_map_and_alert_info(sequence_on_display, cameras, logger):
    """
    Updates the map's vision polygons, center, and alert information based on the current alert data.

    Parameters:
    - alert_data (json): JSON formatted data for the selected event.

    Returns:
    - list: List of vision polygon elements to be displayed on the map.
    - list: New center coordinates for the map.
    - list: List of vision polygon elements to be displayed on the modal map.
    - list: New center coordinates for the modal map.
    - str: Camera information for the alert.
    - str: Camera location for the alert.
    - str: Detection angle for the alert.
    - str: Date of the alert.
    - dict: Style settings for alert information.
    - dict: Style settings for the slider container.
    """
    logger.info("update_map_and_alert_info")
    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")
    cameras = pd.read_json(StringIO(cameras), orient="split")

    if not sequence_on_display.empty:
        # Convert the 'bboxes' column to a list (empty lists if the original value was '[]').
        sequence_on_display["bboxes"] = sequence_on_display["bboxes"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() != "[]" else []
        )

        # Filter out rows where 'bboxes' is not empty and get the last one.
        # If all are empty, then simply get the last row of the DataFrame.
        row_with_bboxes = (
            sequence_on_display[sequence_on_display["bboxes"].astype(bool)].iloc[-1]
            if not sequence_on_display[sequence_on_display["bboxes"].astype(bool)].empty
            else sequence_on_display.iloc[-1]
        )

        row_cam = cameras[cameras["id"] == row_with_bboxes["camera_id"]]
        lat, lon = row_cam[["lat"]].values.item(), row_cam[["lon"]].values.item()

        polygon, detection_azimuth = build_vision_polygon(
            site_lat=lat,
            site_lon=lon,
            azimuth=row_with_bboxes["azimuth"],
            opening_angle=cfg.CAM_OPENING_ANGLE,
            dist_km=cfg.CAM_RANGE_KM,
            bboxes=row_with_bboxes["processed_bboxes"],
        )

        date_val = convert_dt_to_local_tz(lat, lon, row_with_bboxes["created_at"])
        cam_name = f"{row_cam['name'].values.item()[:-3].replace('_', ' ')} : {int(row_with_bboxes['azimuth'])}°"

        camera_info = f"{cam_name}"
        location_info = f"{lat:.4f}, {lon:.4f}"
        angle_info = f"{detection_azimuth}°"
        date_info = f"{date_val}"

        return (
            polygon,
            [lat, lon],
            polygon,
            [lat, lon],
            camera_info,
            location_info,
            angle_info,
            date_info,
            {"display": "block"},
            {"display": "block"},
        )

    return (
        [],
        dash.no_update,
        [],
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        {"display": "none"},
        {"display": "none"},
    )


def update_image_and_bbox(slider_value, sequence_on_display, sequence_list, lang, id_suffix=""):
    """
    Updates the image and bounding box display based on the slider value.
    """
    img_src = ""
    no_alert_image_src = "./assets/images/no-alert-default.png"
    if lang == "es":
        no_alert_image_src = "./assets/images/no-alert-default-es.png"

    sequence_on_display = pd.read_json(StringIO(sequence_on_display), orient="split")

    if sequence_on_display.empty:
        raise PreventUpdate

    if len(sequence_list) == 0:
        return no_alert_image_src, {"display": "none"}, {"display": "none"}, {"display": "none"}, 0

    # Filter images with non-empty URLs
    images, boxes = zip(
        *((alert["url"], alert["processed_bboxes"]) for _, alert in sequence_on_display.iterrows() if alert["url"])
    )

    if not images:
        return no_alert_image_src, {"display": "none"}, {"display": "none"}, {"display": "none"}, 0

    # Ensure slider_value is within the range of available images
    slider_value = slider_value % len(images)
    img_src = images[slider_value]
    images_bbox_list = boxes[slider_value]

    # Create styles for each bbox (default hidden)
    bbox_styles = [{"display": "none"} for _ in range(3)]

    # Update styles for available bounding boxes
    for i, (x0, y0, width, height) in enumerate(images_bbox_list[:3]):  # Limit to 3 bboxes
        bbox_styles[i] = {
            "position": "absolute",
            "left": f"{x0}%",
            "top": f"{y0}%",
            "width": f"{width}%",
            "height": f"{height}%",
            "border": "2px solid red",
            "box-sizing": "border-box",
            "zIndex": "10",
            "display": "block",
        }

    return [img_src, *bbox_styles, len(images) - 1]
