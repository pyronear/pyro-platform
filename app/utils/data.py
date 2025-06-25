# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
from collections import defaultdict
from datetime import datetime
from typing import List

import networkx as nx
import numpy as np
import pandas as pd
import pytz
from geopy.distance import geodesic
from pyproj import Transformer
from shapely.geometry import Polygon
from shapely.ops import transform as shapely_transform
from timezonefinder import TimezoneFinder

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


def get_projected_cone(row, R_km, r_min_km):
    poly = build_cone_polygon(row["lat"], row["lon"], row["cone_azimuth"], row["cone_angle"], R_km, r_min_km)
    return project_polygon(poly)


def build_cone_polygon(lat, lon, azimuth, opening_angle, dist_km, r_min_km, resolution=36):
    half_angle = opening_angle / 2
    angles = np.linspace(azimuth - half_angle, azimuth + half_angle, resolution)
    outer_arc = [geodesic(kilometers=dist_km).destination((lat, lon), az % 360) for az in angles]
    outer_points = [(p.longitude, p.latitude) for p in outer_arc]

    if r_min_km > 0:
        inner_arc = [geodesic(kilometers=r_min_km).destination((lat, lon), az % 360) for az in reversed(angles)]
        inner_points = [(p.longitude, p.latitude) for p in inner_arc]
        return Polygon(outer_points + inner_points, holes=[inner_points]).buffer(0)
    else:
        return Polygon([(lon, lat), *outer_points]).buffer(0)


def project_polygon(polygon):
    transformer = Transformer.from_crs("epsg:4326", "epsg:3857", always_xy=True)
    return shapely_transform(transformer.transform, polygon)


def sequences_have_changed(df1, df2):
    if df1.shape != df2.shape:
        return True

    cols_to_check = ["last_seen_at_local", "is_wildfire"]
    if not all(col in df1.columns and col in df2.columns for col in cols_to_check):
        return True

    df1_checked = df1[cols_to_check].copy()
    df2_checked = df2[cols_to_check].copy()

    df1_checked["last_seen_at_local"] = pd.to_datetime(df1_checked["last_seen_at_local"]).dt.round("s")
    df2_checked["last_seen_at_local"] = pd.to_datetime(df2_checked["last_seen_at_local"]).dt.round("s")

    df1_checked["is_wildfire"] = df1_checked["is_wildfire"].astype("boolean").fillna(False)
    df2_checked["is_wildfire"] = df2_checked["is_wildfire"].astype("boolean").fillna(False)

    # Sort by id if available, otherwise by index
    if "id" in df1.columns and "id" in df2.columns:
        df1_checked = df1_checked.set_index(df1["id"]).sort_index()
        df2_checked = df2_checked.set_index(df2["id"]).sort_index()
    else:
        df1_checked = df1_checked.sort_index()
        df2_checked = df2_checked.sort_index()

    return not df1_checked.equals(df2_checked)


def compute_overlap(api_sequences, R_km=30, r_min_km=0.5):
    """
    Compute mutually overlapping cone groups (cliques) between camera sequences.

    Each output group in the 'overlap' column contains only sequences that all overlap pairwise.

    Parameters:
        api_sequences (pd.DataFrame): Must contain:
            - 'id', 'lat', 'lon', 'cone_azimuth', 'cone_angle'
            - 'started_at', 'last_seen_at' (datetime-compatible)
        R_km (float): Maximum detection range of the cone.
        r_min_km (float): Inner radius of the cone.

    Returns:
        pd.DataFrame: Copy of input with new column 'overlap' containing list of cliques (or None).
    """
    df = api_sequences.copy()
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["last_seen_at"] = pd.to_datetime(df["last_seen_at"])

    projected_cones = {row["id"]: get_projected_cone(row, R_km, r_min_km) for _, row in df.iterrows()}

    overlapping_pairs = []
    ids = df["id"].tolist()

    for i, id1 in enumerate(ids):
        row1 = df[df["id"] == id1].iloc[0]
        for id2 in ids[i + 1:]:
            row2 = df[df["id"] == id2].iloc[0]
            if row1["started_at"] > row2["last_seen_at"] or row2["started_at"] > row1["last_seen_at"]:
                continue
            if projected_cones[id1].intersects(projected_cones[id2]):
                overlapping_pairs.append((id1, id2))

    G = nx.Graph()
    G.add_edges_from(overlapping_pairs)
    cliques = [tuple(sorted(clique)) for clique in nx.find_cliques(G) if len(clique) >= 2]

    id_to_groups = defaultdict(list)
    for group in cliques:
        for sid in group:
            id_to_groups[sid].append(group)

    df["overlap"] = df["id"].map(lambda x: id_to_groups.get(x, None))
    return df
