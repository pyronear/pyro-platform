# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import json
import os
import shutil
from datetime import datetime, timedelta
from io import StringIO
from typing import List, Tuple

import cv2
import dash_leaflet as dl
import numpy as np
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


def calculate_new_polygon_parameters(azimuth, opening_angle, bbox):
    """
    Computes the new azimuth and opening angle based on the bounding box.

    Parameters:
    - azimuth: float, center azimuth of the camera (in degrees)
    - opening_angle: float, horizontal field of view of the camera (in degrees)
    - bbox: list or tuple [x0, y0, x1, y1, confidence], normalized coordinates (0 to 1)

    Returns:
    - new_azimuth: int, estimated azimuth of the detection (in degrees)
    - new_opening_angle: int, estimated angular width (in degrees)
    """
    x0, _, x1, _, _ = bbox

    # Center x in normalized coordinates
    xc = (x0 + x1) / 2

    # Width of bbox in normalized coords
    width = x1 - x0

    # Compute new azimuth (relative offset from center)
    new_azimuth = azimuth - opening_angle * (0.5 - xc)

    # Compute angular width of the bbox
    new_opening_angle = opening_angle * width + 1  # +1 to avoid zero angle

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
                    dl.Popup([
                        html.H2(f"Site {site_name}"),
                        html.P(f"Coordonnées : ({lat}, {lon})"),
                    ]),
                ],
            )
        )

    # We group all dl.Marker objects in a dl.MarkerClusterGroup object and return it
    return markers, client_sites


def build_vision_polygon(site_lat, site_lon, azimuth, opening_angle, dist_km):
    """
    Create a vision polygon using dl.Polygon. This polygon is placed on the map using alerts data.

    Parameters:
        site_lat (float): Latitude of the camera.
        site_lon (float): Longitude of the camera.
        azimuth (float): Central direction of the camera in degrees.
        opening_angle (float): Field of view in degrees.
        dist_km (float): Distance to project the polygon edges.

    Returns:
        polygon (dl.Polygon): The vision cone polygon.
        azimuth (float): The original azimuth value (unchanged).
    """
    center = [site_lat, site_lon]

    # Convert float angle to an integer for iteration
    n_steps = max(1, round(opening_angle))  # avoid range(1,1)

    points1 = []
    points2 = []

    for i in reversed(range(1, n_steps + 1)):
        azimuth1 = (azimuth - i / 2) % 360
        azimuth2 = (azimuth + i / 2) % 360

        point1 = geodesic(kilometers=dist_km).destination(Point(site_lat, site_lon), azimuth1)
        point2 = geodesic(kilometers=dist_km).destination(Point(site_lat, site_lon), azimuth2)

        points1.append([point1.latitude, point1.longitude])
        points2.append([point2.latitude, point2.longitude])

    points = [center, *points1, *reversed(points2)]

    polygon = dl.Polygon(
        id="vision_polygon",
        color="#ff7800",
        opacity=0.5,
        positions=points,
    )

    return polygon


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


def create_sequence_list(api_sequences, cameras):
    """
    Create a list of cards, one per sequence, with overlap info listed below if applicable.
    Uses a Dash button wrapper with sequence ID as component ID.
    """
    if api_sequences.empty:
        return []

    api_sequences = api_sequences.copy()

    def get_annotation_emoji(value):
        if value == 1.0:
            return "🔥"
        elif value == 0.0:
            return "🚫"
        return ""

    def get_camera_info(cam_id):
        cam = cameras[cameras["id"] == cam_id]
        if cam.empty:
            return "Unknown", 0.0, 0.0
        cam_name = cam["name"].values[0][:-3].replace("_", " ")
        return cam_name, cam["lat"].values[0], cam["lon"].values[0]

    api_sequences = api_sequences.sort_values("started_at", ascending=False)

    cards = []
    for _, row in api_sequences.iterrows():
        cam_name, _, _ = get_camera_info(row["camera_id"])
        azimuth = int(row["cone_azimuth"]) % 360
        emoji = get_annotation_emoji(row.get("is_wildfire"))

        date_str, time_str = row["started_at_local"].split(" ")
        time_str = time_str[:5]

        header = html.Div(
            f"📅 {date_str} ⏱ {time_str} {emoji}",
            style={"fontWeight": "bold", "textAlign": "left", "marginBottom": "3px"},
        )
        main_detection = html.Div(
            f"📷 {cam_name} ({azimuth}°)",
            style={
                "display": "block",
                "textAlign": "left",
                "fontWeight": "bold",
            },
        )

        overlaps = []
        if isinstance(row.get("overlap"), list):
            for group in row["overlap"]:
                for sid in group:
                    if sid == row["id"]:
                        continue
                    match = api_sequences[api_sequences["id"] == sid]
                    if not match.empty:
                        m = match.iloc[0]
                        match_name, _, _ = get_camera_info(m["camera_id"])
                        match_azimuth = int(m["cone_azimuth"]) % 360
                        match_time = m["started_at_local"].split(" ")[1]
                        overlaps.append(
                            html.Div(
                                f"↳ {match_name} ({match_azimuth}°) • {match_time}",
                                style={
                                    "fontSize": "12px",
                                    "paddingLeft": "8px",
                                    "color": "#555",
                                    "display": "block",
                                    "textAlign": "left",
                                    "verticalAlign": "bottom",
                                },
                            )
                        )

        card = html.Button(
            id={"type": "event-button", "index": row["id"]},
            children=[header, main_detection, *overlaps],
            className="pyronear-card alert-card",
            style={"marginBottom": "10px"},
            n_clicks=0,
        )
        cards.append(card)

    return cards


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


def prepare_archive(sequence_data, api_sequences, folder_name, camera_value):
    # Clean old
    if os.path.isdir("zips"):
        shutil.rmtree("zips")

    # Define directories
    base_dir = os.path.join("zips", folder_name)
    image_dir = os.path.join(base_dir, "images")
    pred_dir = os.path.join(base_dir, "predictions")
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(pred_dir, exist_ok=True)

    # Get metadata
    sequence_id = sequence_data.get("sequence_id")[0]
    sequence_metadata = api_sequences[api_sequences["id"] == sequence_id]
    metadata_dict = sequence_metadata.iloc[0].to_dict()
    metadata_dict["camera"] = camera_value.replace("°", "")
    metadata_dict = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in metadata_dict.items()}

    with open(os.path.join(base_dir, "sequence_metadata.json"), "w") as f:
        json.dump(metadata_dict, f, indent=2)

    for _, row in sequence_data.iterrows():
        url = row["url"]
        fname = row["bucket_key"]
        original_path = os.path.join(image_dir, fname)
        pred_path = os.path.join(pred_dir, fname)

        # Download image
        if not os.path.exists(original_path):
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(original_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)

        # Load image and draw bbox
        img = cv2.imread(original_path)
        img_np = np.array(img)
        h, w = img_np.shape[:2]

        if isinstance(row["processed_bboxes"], list) and row["processed_bboxes"]:
            for bbox in row["processed_bboxes"]:
                bbox = [b / 100 for b in bbox]
                x, y, w_box, h_box = bbox
                x1 = int(x * w)
                y1 = int(y * h)
                x2 = int((x + w_box) * w)
                y2 = int((y + h_box) * h)
                cv2.rectangle(img_np, (x1, y1), (x2, y2), (255, 0, 0), 2)

        # Save prediction image
        cv2.imwrite(pred_path, img_np)

    # Create zip
    shutil.make_archive(os.path.join("zips", folder_name), "zip", base_dir)
