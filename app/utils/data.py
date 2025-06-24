# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
from collections import defaultdict
from typing import List

import numpy as np
import pandas as pd
from geopy.distance import geodesic
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import transform as shapely_transform


def process_bbox(input_str):
    """
    Processes the bounding box information from a xyxy string input to a xywh list of integer coordinates.

    Args:
        input_str (str): A string representing the bounding box coordinates.

    Returns:
        List[List[int]]: A list of bounding box coordinates in integer format.
    """
    new_boxes: List[List[int]] = []

    # Check if input_str is not None and is a valid string
    if not isinstance(input_str, str) or not input_str:
        return new_boxes

    try:
        boxes = ast.literal_eval(input_str)
    except (ValueError, SyntaxError):
        # Return an empty list if there's a parsing error
        return new_boxes

    for x0, y0, x1, y1, _ in boxes:
        width = x1 - x0
        height = y1 - y0

        new_boxes.append([x0 * 100, y0 * 100, width * 100, height * 100])

    return new_boxes


def past_ndays_api_events(api_events, n_days=0):
    """
    Filters the given live events to retain only those within the past n days.

    Args:
        api_events (pd.Dataframe): DataFrame containing live events data. It must have a "created_at" column
                                    indicating the datetime of the event.
        n_days (int, optional): Specifies the number of days into the past to retain events. Defaults to 0.

    Returns:
        pd.DataFrame: A filtered DataFrame containing only events from the past n_days.
    """
    # Ensure the column is in datetime format
    api_events["created_at"] = pd.to_datetime(api_events["created_at"])

    # Define the end date (now) for the filter
    end_date = pd.Timestamp.now()

    if n_days == 0:
        # When n_days is 0, adjust start_date to the beginning of today to include today's events
        start_date = end_date.normalize()
    else:
        # For n_days > 0
        start_date = end_date - pd.Timedelta(days=n_days)

    # Filter events from the past n days, including all events from today when n_days is 0
    api_events = api_events[(api_events["created_at"] > start_date) | (api_events["created_at"] == start_date)]

    return api_events


def assign_event_ids(df, time_threshold=30 * 60):
    """
    Assigns event IDs to detections in a DataFrame based on the same camera_id
    and a time threshold between consecutive detections.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'camera_id' and 'created_at' columns.
        time_threshold (int): The time difference in seconds to group detections into the same event.

    Returns:
        pd.DataFrame: A DataFrame with an additional 'event_id' column.
    """
    # Ensure 'created_at' is in datetime format
    df["created_at"] = pd.to_datetime(df["created_at"])

    # Sort by camera_id and created_at
    df = df.sort_values(by=["camera_id", "created_at"]).reset_index(drop=True)

    # Initialize variables
    event_id = 0
    event_ids = []  # To store the assigned event IDs

    # Iterate through rows to assign event IDs
    for i, row in df.iterrows():
        if i == 0:
            # First detection starts a new event
            event_ids.append(event_id)
        else:
            # Compare with the previous row
            prev_row = df.iloc[i - 1]
            time_diff = (row["created_at"] - prev_row["created_at"]).total_seconds()

            if row["camera_id"] != prev_row["camera_id"] or time_diff > time_threshold:
                # Start a new event
                event_id += 1

            event_ids.append(event_id)

    # Add the event_id column to the DataFrame
    df["event_id"] = event_ids
    return df


def compute_overlap(api_sequences, R_km=30, r_min_km=0.5):
    """
    Compute overlapping field-of-view cones between camera sequences.

    Each camera's field of view is modeled as a geodesic cone (a sector of a circle with inner and outer radius)
    projected onto a map using Web Mercator (EPSG:3857). This function:

    1. Builds a polygon representing each cone based on latitude, longitude, azimuth, and opening angle.
    2. Projects each polygon to a planar coordinate system for geometric comparison.
    3. Checks which polygons intersect (i.e., their cones overlap on the ground).
    4. Constructs a graph of overlapping cones and extracts connected components.
    5. Maps each sequence ID to the list of overlapping groups it belongs to.

    Parameters:
        api_sequences (pd.DataFrame): DataFrame containing at least the following columns:
            - 'id': unique identifier for each sequence
            - 'lat': latitude of the camera
            - 'lon': longitude of the camera
            - 'cone_azimuth': direction the camera is facing (in degrees)
            - 'cone_angle': opening angle of the field of view (in degrees)
        R_km (float): Maximum viewing distance in kilometers for the cone.
        r_min_km (float): Minimum distance from the origin to start the cone.

    Returns:
        pd.DataFrame: A copy of `api_sequences` with a new column 'overlap' that contains a list of overlapping group tuples (or None).
    """

    def build_cone_polygon(lat, lon, azimuth, opening_angle, dist_km, r_min_km, resolution=36):
        """Builds a 2D polygon representing the geodesic cone."""
        half_angle = opening_angle / 2
        angles = np.linspace(azimuth - half_angle, azimuth + half_angle, resolution)

        outer_arc = [geodesic(kilometers=dist_km).destination((lat, lon), az % 360) for az in angles]
        outer_points = [(p.longitude, p.latitude) for p in outer_arc]

        if r_min_km > 0:
            inner_arc = [geodesic(kilometers=r_min_km).destination((lat, lon), az % 360) for az in reversed(angles)]
            inner_points = [(p.longitude, p.latitude) for p in inner_arc]

            if len(outer_points + inner_points) >= 4 and len(inner_points) >= 4:
                return Polygon(outer_points + inner_points, holes=[inner_points]).buffer(0)
            else:
                return Polygon(outer_points).buffer(0)
        else:
            if len(outer_points) >= 3:
                return Polygon([(lon, lat)] + outer_points).buffer(0)
            else:
                raise ValueError("Not enough points to form a polygon.")

    def project_polygon(polygon):
        """Projects a geographic polygon to EPSG:3857 (Web Mercator)."""
        transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
        return shapely_transform(transformer.transform, polygon)

    def get_projected_cone(row):
        """Build and project cone polygon from a DataFrame row."""
        poly = build_cone_polygon(row["lat"], row["lon"], row["cone_azimuth"], row["cone_angle"], R_km, r_min_km)
        return project_polygon(poly)

    # Step 1: Build and store all projected cones
    projected_cones = {row["id"]: get_projected_cone(row) for _, row in api_sequences.iterrows()}

    # Step 2: Build adjacency graph based on intersection
    adjacency = defaultdict(set)
    ids = api_sequences["id"].tolist()

    for i, id1 in enumerate(ids):
        for id2 in ids[i + 1:]:
            if projected_cones[id1].intersects(projected_cones[id2]):
                adjacency[id1].add(id2)
                adjacency[id2].add(id1)

    # Step 3: Find connected components of overlapping cones
    def find_connected_components(adj):
        visited = set()
        components = []

        def dfs(node, comp):
            visited.add(node)
            comp.add(node)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    dfs(neighbor, comp)

        for node in adj:
            if node not in visited:
                comp = set()
                dfs(node, comp)
                components.append(tuple(sorted(comp)))

        return components

    overlap_groups = find_connected_components(adjacency)

    # Step 4: Map each ID to the groups it belongs to
    id_to_overlaps = defaultdict(list)
    for group in overlap_groups:
        for seq_id in group:
            id_to_overlaps[seq_id].append(group)

    # Step 5: Update the DataFrame with overlap information
    api_sequences = api_sequences.copy()
    api_sequences["overlap"] = api_sequences["id"].map(lambda x: id_to_overlaps.get(x, None))

    return api_sequences
