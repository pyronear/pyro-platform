# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import itertools
from collections import defaultdict
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import List

import logging_config
import networkx as nx  # type: ignore
import numpy as np
import pandas as pd
import pyproj
import pytz
from geopy.distance import geodesic
from pyproj import Transformer
from shapely.geometry import Polygon  # type: ignore
from shapely.ops import transform as shapely_transform  # type: ignore
from timezonefinder import TimezoneFinder

import config as cfg

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


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


def sequences_have_changed(df1, df2, cols_to_check=None):
    import pandas as pd

    # Default to new schema
    if cols_to_check is None:
        cols_to_check = ["last_seen_at_local", "label"]

    # Shape change means changed
    if df1.shape != df2.shape:
        return True

    # Required columns missing means changed
    if not all(col in df1.columns and col in df2.columns for col in cols_to_check):
        return True

    df1_checked = df1[cols_to_check].copy()
    df2_checked = df2[cols_to_check].copy()

    for col in cols_to_check:
        # Normalize datetimes to seconds
        if "datetime" in str(df1_checked[col].dtype) or "date" in col or "time" in col:
            df1_checked[col] = pd.to_datetime(df1_checked[col], errors="coerce").dt.round("s")
            df2_checked[col] = pd.to_datetime(df2_checked[col], errors="coerce").dt.round("s")

        # Legacy support when comparing a boolean column
        elif col == "is_wildfire":
            # Keep NA to detect changes, cast only if boolean like
            if df1_checked[col].dtype == bool or df2_checked[col].dtype == bool:
                df1_checked[col] = df1_checked[col].astype("boolean")
                df2_checked[col] = df2_checked[col].astype("boolean")

        # New schema label, keep strings and NA as is
        elif col == "label":
            # Ensure object dtype, do not fillna so NA stays comparable
            df1_checked[col] = df1_checked[col].astype("object")
            df2_checked[col] = df2_checked[col].astype("object")

    # Stable index for comparison
    if "id" in df1.columns and "id" in df2.columns:
        df1_checked.index = df1["id"]
        df2_checked.index = df2["id"]
    else:
        df1_checked.index = df1.index
        df2_checked.index = df2.index

    df1_checked = df1_checked.sort_index()
    df2_checked = df2_checked.sort_index()

    # pandas.DataFrame.equals treats NaN as equal, which is desired here
    return not df1_checked.equals(df2_checked)


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Compute the great-circle distance between two points on the Earth's surface using the Haversine formula.

    Parameters:
        lat1 (float): Latitude of point 1 in decimal degrees.
        lon1 (float): Longitude of point 1 in decimal degrees.
        lat2 (float): Latitude of point 2 in decimal degrees.
        lon2 (float): Longitude of point 2 in decimal degrees.

    Returns:
        float: Distance between the two points in kilometers.
    """
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def get_centroid_latlon(geom):
    """
    Compute the geographic coordinates (latitude, longitude) of the centroid of a given geometry.

    Parameters:
        geom (shapely.geometry): Geometry in EPSG:3857 (Web Mercator projection).

    Returns:
        tuple: (latitude, longitude) of the centroid in EPSG:4326.
    """
    centroid = geom.centroid
    transformer = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(centroid.x, centroid.y)
    return lat, lon


def compute_smoke_location(seq, projected_cones):
    """
    Estimate the smoke location for a group of sequences.

    Rules:
        - If the sequence contains only 1 ID, returns None.
        - If 2 sequences: returns the centroid of their cone intersection.
        - If >2: returns the centroid of all pairwise intersection centroids.

    Parameters:
        seq (list): List of sequence IDs.
        projected_cones (dict): Mapping from sequence ID to cone geometry (shapely object).

    Returns:
        tuple or None: (latitude, longitude) if estimated, otherwise None.
    """
    if len(seq) == 1:
        return None

    barycenters = []

    for id1, id2 in itertools.combinations(seq, 2):
        if id1 not in projected_cones or id2 not in projected_cones:
            continue
        inter = projected_cones[id1].intersection(projected_cones[id2])
        if not inter.is_empty and inter.area > 0:
            lat, lon = get_centroid_latlon(inter)
            barycenters.append((lat, lon))

    if not barycenters:
        return None
    elif len(barycenters) == 1:
        return barycenters[0]
    else:
        # Compute second-level centroid: barycenter of barycenters
        avg_lat = sum(lat for lat, _ in barycenters) / len(barycenters)
        avg_lon = sum(lon for _, lon in barycenters) / len(barycenters)
        return (avg_lat, avg_lon)


def filter_localized_events(event_id_table, df_valid, R_km=30, r_min_km=0.5, max_dist_km=2.0):
    """
    Identify events with 3 or more sequences that have consistent intersection barycenters.

    For each group:
        - Compute all pairwise intersections.
        - Keep if max distance between barycenters is below threshold.

    Parameters:
        event_id_table (pd.DataFrame): Table with 'event_id' and 'sequences'.
        df_valid (pd.DataFrame): Subset of sequences with is_wildfire != 0.0.
        R_km (float): Maximum detection range of the cone in kilometers.
        r_min_km (float): Minimum (inner) radius of the cone in kilometers.
        max_dist_km (float): Maximum allowed distance between barycenters.

    Returns:
        set: Set of valid event IDs (str) with spatially localized detections.
    """
    df_valid = df_valid[df_valid["is_wildfire"] != 0.0]
    projected_cones = {row["id"]: get_projected_cone(row, R_km, r_min_km) for _, row in df_valid.iterrows()}

    valid_event_ids = set()

    for _, row in event_id_table.iterrows():
        seq = row["sequences"]
        if len(seq) < 3:
            continue

        bary_dict = {}
        for id1, id2 in itertools.combinations(seq, 2):
            inter = projected_cones[id1].intersection(projected_cones[id2])
            if not inter.is_empty and inter.area > 0:
                lat, lon = get_centroid_latlon(inter)
                bary_dict[id1, id2] = (lat, lon)

        if len(bary_dict) < 2:
            continue

        bary_coords = list(bary_dict.values())
        distances = [
            haversine_km(lat1, lon1, lat2, lon2)
            for (lat1, lon1), (lat2, lon2) in itertools.combinations(bary_coords, 2)
        ]

        if max(distances) <= max_dist_km:
            valid_event_ids.add(row["event_id"])

    return valid_event_ids


def compute_overlap(api_sequences, R_km=35, r_min_km=0.5, max_dist_km=2.0, unmatched_event_table=None):
    """
    Identify groups of overlapping camera sequences and consolidate them into events.

    Steps:
        1. Compute intersection graph of cone projections.
        2. Extract maximal cliques of sequences (overlapping in space and time).
        3. Filter valid (localized) events using barycenter consistency.
        4. Decompose non-localized events with >2 sequences into 2-by-2 pairs.
        5. Estimate smoke location for each final event.

    Parameters:
        api_sequences (pd.DataFrame): Input with fields:
            - 'id', 'lat', 'lon', 'cone_azimuth', 'cone_angle', 'is_wildfire'
            - 'started_at', 'last_seen_at', 'started_at_local' (datetime-compatible)
        R_km (float): Outer radius of the camera detection cone (in km).
        r_min_km (float): Inner radius of the camera detection cone (in km).
        max_dist_km (float): Maximum allowed distance between intersection barycenters for validation.
        unmatched_event_table: Events id that can't match

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - Updated DataFrame with 'overlap' column.
            - Final event table with 'event_id', 'sequences', 'time', and 'smoke_location'.
    """
    df = api_sequences.copy()
    df["id"] = df["id"].astype(int)
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["last_seen_at"] = pd.to_datetime(df["last_seen_at"])

    df_valid = df[df["is_wildfire"].isin([None, "wildfire_smoke"])]

    projected_cones = {row["id"]: get_projected_cone(row, R_km, r_min_km) for _, row in df_valid.iterrows()}

    overlapping_pairs = []
    ids = df_valid["id"].tolist()

    # Prepare the exclusion set from unmatched_event_table
    unmatched_exclusions = set()
    if unmatched_event_table is not None and isinstance(unmatched_event_table, list):
        try:
            for source_seq, group_seqs in unmatched_event_table:
                source_seq = int(source_seq)
                group_seqs = [int(s) for s in group_seqs]
                for seq in group_seqs:
                    if seq != source_seq:
                        unmatched_exclusions.add((source_seq, seq))
                        unmatched_exclusions.add((seq, source_seq))  # make it symmetric
        except Exception as e:
            logger.warning(f"Failed to parse unmatched_event_table: {e}")

    for i, id1 in enumerate(ids):
        row1 = df_valid[df_valid["id"] == id1].iloc[0]
        for id2 in ids[i + 1 :]:
            row2 = df_valid[df_valid["id"] == id2].iloc[0]

            # Skip if time windows do not overlap
            if row1["started_at"] > row2["last_seen_at"] or row2["started_at"] > row1["last_seen_at"]:
                continue

            # Skip forbidden matches
            if (id1, id2) in unmatched_exclusions:
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

    # Phase 1 : raw event groups
    raw_event_records = []
    event_counter = 0
    added_ids = set()

    for group in cliques:
        group_ids = sorted(int(sid) for sid in group)
        group_df = df[df["id"].isin(group_ids)]
        group_time = group_df["started_at_local"].min()
        raw_event_records.append({"event_id": f"event_{event_counter}", "sequences": group_ids, "time": group_time})
        added_ids.update(group_ids)
        event_counter += 1

    all_ids = set(df["id"])
    for sid in sorted(all_ids - added_ids):
        row = df[df["id"] == sid].iloc[0]
        raw_event_records.append({
            "event_id": f"event_{event_counter}",
            "sequences": [int(sid)],
            "time": row["started_at_local"],
        })
        event_counter += 1

    raw_event_table = pd.DataFrame(raw_event_records)

    # Phase 2 : filter localized
    valid_ids = filter_localized_events(raw_event_table, df, R_km, r_min_km, max_dist_km)

    final_event_records = []
    new_event_counter = 0

    for _, row in raw_event_table.iterrows():
        seq = row["sequences"]
        if len(seq) < 2 or row["event_id"] in valid_ids:
            final_event_records.append({
                "event_id": f"event_{new_event_counter}",
                "sequences": seq,
                "time": row["time"],
            })
            new_event_counter += 1
        else:
            for id1, id2 in itertools.combinations(seq, 2):
                time = df[df["id"].isin([id1, id2])]["started_at_local"].min()
                final_event_records.append({
                    "event_id": f"event_{new_event_counter}",
                    "sequences": [id1, id2],
                    "time": time,
                })
                new_event_counter += 1

    event_id_table = pd.DataFrame(final_event_records)

    # Add smoke_location
    event_id_table["smoke_location"] = event_id_table["sequences"].apply(
        lambda seq: compute_smoke_location(seq, projected_cones)
    )

    event_id_table = event_id_table.copy()
    event_id_table["sequence_tuple"] = event_id_table["sequences"].apply(lambda seq: tuple(sorted(seq)))

    # Remove exact duplicates
    event_id_table = event_id_table.drop_duplicates(subset="sequence_tuple").reset_index(drop=True)

    sequence_tuples = event_id_table["sequence_tuple"].tolist()
    to_drop = set()

    for i, seq1 in enumerate(sequence_tuples):
        for j, seq2 in enumerate(sequence_tuples):
            if i != j and set(seq1).issubset(set(seq2)):
                to_drop.add(i)
                break  # no need to check further if already a subset

    event_id_table = event_id_table.drop(index=to_drop).reset_index(drop=True)
    event_id_table = event_id_table.drop(columns="sequence_tuple")

    return df, event_id_table
