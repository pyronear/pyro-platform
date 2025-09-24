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

def _compute_localized_groups_from_cliques(
    df: pd.DataFrame,
    cliques: list[tuple[int, ...]],
    projected_cones: dict[int, "Polygon"],
    max_dist_km: float,
) -> list[tuple[int, ...]]:
    """
    From maximal cliques, split each clique into localized groups.
    Rule: for groups with size >= 3, keep the whole group if the maximum distance
    among all pair intersection barycenters is <= max_dist_km, otherwise split into all 2 by 2 pairs.
    Returns a list of unique groups as sorted tuples, with subset groups removed.
    """
    # Build a local working list
    base = [tuple(sorted(g)) for g in cliques]
    ids_in_cliques = set(x for g in base for x in g)
    all_ids = set(df["id"].astype(int).tolist())
    singletons = [(sid,) for sid in sorted(all_ids - ids_in_cliques)]
    work = base + singletons

    def split_one_group(group: tuple[int, ...]) -> list[tuple[int, ...]]:
        group = tuple(sorted(group))
        if len(group) <= 1:
            return [group]

        # gather pair barycenters
        pair_barys = []
        for i, j in itertools.combinations(group, 2):
            gi = projected_cones.get(i)
            gj = projected_cones.get(j)
            if gi is None or gj is None:
                continue
            inter = gi.intersection(gj)
            if inter.is_empty or inter.area <= 0:
                continue
            pair_barys.append(get_centroid_latlon(inter))

        if len(group) == 2:
            return [group]

        if len(pair_barys) < 2:
            return [tuple(sorted(p)) for p in itertools.combinations(group, 2)]

        # diameter of barycenters
        max_d = 0.0
        for (lat1, lon1), (lat2, lon2) in itertools.combinations(pair_barys, 2):
            d = haversine_km(lat1, lon1, lat2, lon2)
            if d > max_d:
                max_d = d

        if max_d <= max_dist_km:
            return [group]
        else:
            return [tuple(sorted(p)) for p in itertools.combinations(group, 2)]

    # Split, dedupe, and drop strict subsets
    candidates = []
    for clique in sorted(set(work)):
        candidates.extend(split_one_group(clique))

    candidates = sorted(set(tuple(sorted(g)) for g in candidates))

    keep = []
    as_sets = [set(g) for g in candidates]
    for i, gi in enumerate(as_sets):
        if any(i != j and gi.issubset(as_sets[j]) for j in range(len(as_sets))):
            continue
        keep.append(candidates[i])

    return keep


def compute_overlap(api_sequences, R_km=50, r_min_km=0.5, max_dist_km=5.0, unmatched_event_table=None):
    """
    Identify groups of overlapping camera sequences and consolidate them into localized events.
    Phase 1 fills df['overlap'] with maximal cliques, Phase 2 derives df['localized_groups']
    by enforcing a spatial consistency threshold on pair intersection barycenters.
    Returns df and a compact event_id_table built from localized groups.
    """
    df = api_sequences.copy()
    df["id"] = df["id"].astype(int)
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["last_seen_at"] = pd.to_datetime(df["last_seen_at"])

    # keep positives and unknowns, as agreed
    df_valid = df[df["is_wildfire"].isin([None, "wildfire_smoke"])]

    # short circuit if nothing valid
    if df_valid.empty:
        df["overlap"] = [[] for _ in range(len(df))]
        df["localized_groups"] = df["id"].astype(int).map(lambda i: [(i,)])
        # build a minimal event table for downstream
        time_col = "started_at_local" if "started_at_local" in df.columns else "started_at"
        event_id_table = pd.DataFrame({
            "event_id": [f"event_{i}" for i in range(len(df))],
            "sequences": df["id"].astype(int).map(lambda i: [i]).tolist(),
            "time": df[time_col].tolist(),
            "smoke_location": [None] * len(df),
        })
        return df, event_id_table

    # precompute cones
    projected_cones = {int(row["id"]): get_projected_cone(row, R_km, r_min_km) for _, row in df_valid.iterrows()}

    # exclusions
    unmatched_exclusions = set()
    if unmatched_event_table is not None and isinstance(unmatched_event_table, list):
        try:
            for source_seq, group_seqs in unmatched_event_table:
                s = int(source_seq)
                for t in (int(x) for x in group_seqs):
                    if t != s:
                        unmatched_exclusions.add((s, t))
                        unmatched_exclusions.add((t, s))
        except Exception as e:
            logger.warning(f"Failed to parse unmatched_event_table: {e}")

    # Phase 1, build overlap graph with time window check
    ids = df_valid["id"].astype(int).tolist()
    rows_by_id = df_valid.set_index("id")[["started_at", "last_seen_at"]].to_dict("index")

    overlapping_pairs: list[tuple[int, int]] = []
    for i, id1 in enumerate(ids):
        row1 = rows_by_id[id1]
        for id2 in ids[i + 1:]:
            row2 = rows_by_id[id2]
            # time windows must overlap
            if row1["started_at"] > row2["last_seen_at"] or row2["started_at"] > row1["last_seen_at"]:
                continue
            # forbidden matches
            if (id1, id2) in unmatched_exclusions:
                continue
            # spatial test
            if projected_cones[id1].intersects(projected_cones[id2]):
                overlapping_pairs.append((id1, id2))

    G = nx.Graph()
    G.add_edges_from(overlapping_pairs)
    cliques = [tuple(sorted(c)) for c in nx.find_cliques(G) if len(c) >= 2]

    # map id to cliques
    id_to_groups = defaultdict(list)
    for group in cliques:
        for sid in group:
            id_to_groups[sid].append(group)

    df["overlap"] = df["id"].map(lambda x: id_to_groups.get(int(x), []))

    # Phase 2, localized groups from cliques
    localized_groups = _compute_localized_groups_from_cliques(df, cliques, projected_cones, max_dist_km)

    # attach to df, as list of tuples for each id
    id_to_local = defaultdict(list)
    for g in localized_groups:
        for sid in g:
            id_to_local[sid].append(g)
    df["localized_groups"] = df["id"].astype(int).map(lambda sid: id_to_local.get(sid, []))

    # Build a tidy event table for downstream use
    time_col = "started_at_local" if "started_at_local" in df.columns else "started_at"
    records = []
    for k, seq_tuple in enumerate(localized_groups):
        seq = list(seq_tuple)
        time_val = df[df["id"].astype(int).isin(seq)][time_col].min()
        records.append({
            "event_id": f"event_{k}",
            "sequences": seq,
            "time": time_val,
        })

    event_id_table = pd.DataFrame(records)

    # smoke location per event, median of pair barycenters for robustness
    def _smoke_from_pairs(seq: list[int]) -> tuple[float, float] | None:
        pts = []
        for i, j in itertools.combinations(sorted(seq), 2):
            inter = projected_cones[i].intersection(projected_cones[j])
            if inter.is_empty or inter.area <= 0:
                continue
            pts.append(get_centroid_latlon(inter))
        if not pts:
            return None
        lats, lons = zip(*pts)
        return float(np.median(lats)), float(np.median(lons))

    event_id_table["smoke_location"] = event_id_table["sequences"].apply(_smoke_from_pairs)

    return df, event_id_table
