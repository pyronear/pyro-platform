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


def _compute_localized_groups_from_cliques(
    df: pd.DataFrame,
    cliques: list[tuple[int, ...]],
    projected_cones: dict[int, Polygon],
    max_dist_km: float,
) -> list[tuple[int, ...]]:
    """
    From maximal cliques, split each clique into localized groups.
    Rule: for groups with size at least 3, keep the whole group if the maximum distance
    among all pair intersection barycenters is within max_dist_km, otherwise split into all pairs.
    Returns unique groups as sorted tuples, with strict subsets removed.
    """
    base = [tuple(sorted(g)) for g in cliques]
    ids_in_cliques = set(x for g in base for x in g)
    all_ids = set(df["id"].astype(int).tolist())
    work = base + [(sid,) for sid in sorted(all_ids - ids_in_cliques)]

    def split_one_group(group: tuple[int, ...]) -> list[tuple[int, ...]]:
        group = tuple(sorted(group))
        if len(group) <= 1:
            return [group]

        pair_barys: list[tuple[float, float]] = []
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

        max_d = 0.0
        for (lat1, lon1), (lat2, lon2) in itertools.combinations(pair_barys, 2):
            d = haversine_km(lat1, lon1, lat2, lon2)
            if d > max_d:
                max_d = d

        if max_d <= max_dist_km:
            return [group]
        return [tuple(sorted(p)) for p in itertools.combinations(group, 2)]

    candidates: list[tuple[int, ...]] = []
    for clique in sorted(set(work)):
        candidates.extend(split_one_group(clique))

    candidates = sorted(set(tuple(sorted(g)) for g in candidates))

    keep: list[tuple[int, ...]] = []
    as_sets = [set(g) for g in candidates]
    for i, gi in enumerate(as_sets):
        if any(i != j and gi.issubset(as_sets[j]) for j in range(len(as_sets))):
            continue
        keep.append(candidates[i])

    return keep


def compute_overlap(api_sequences, R_km=35, r_min_km=0.5, max_dist_km=2.0):
    """
    Build localized event groups and attach them to the input DataFrame.
    Adds two columns per row:
      event_groups, list of tuples of sequence ids
      event_smoke_locations, list of (lat, lon) per group aligned with event_groups
    """
    df = api_sequences.copy()
    df["id"] = df["id"].astype(int)
    df["started_at"] = pd.to_datetime(df["started_at"])
    df["last_seen_at"] = pd.to_datetime(df["last_seen_at"])

    df_valid = df[df["is_wildfire"].isin([None, "wildfire_smoke"])]

    if df_valid.empty:
        df["event_groups"] = df["id"].astype(int).map(lambda sid: [(sid,)])
        df["event_smoke_locations"] = [[] for _ in range(len(df))]
        return df

    projected_cones = {
        int(row["id"]): get_projected_cone(row, R_km, r_min_km)
        for _, row in df_valid.iterrows()
    }

    ids = df_valid["id"].astype(int).tolist()
    rows_by_id = df_valid.set_index("id")[["started_at", "last_seen_at"]].to_dict("index")

    overlapping_pairs: list[tuple[int, int]] = []
    for i, id1 in enumerate(ids):
        row1 = rows_by_id[id1]
        for id2 in ids[i + 1:]:
            row2 = rows_by_id[id2]
            if row1["started_at"] > row2["last_seen_at"] or row2["started_at"] > row1["last_seen_at"]:
                continue
            if projected_cones[id1].intersects(projected_cones[id2]):
                overlapping_pairs.append((id1, id2))

    G = nx.Graph()
    G.add_edges_from(overlapping_pairs)
    cliques = [tuple(sorted(c)) for c in nx.find_cliques(G) if len(c) >= 2]

    localized_groups = _compute_localized_groups_from_cliques(df, cliques, projected_cones, max_dist_km)

    # per group localization, median of pair barycenters for robustness
    def group_smoke_location(seq_tuple: tuple[int, ...]) -> tuple[float, float] | None:
        if len(seq_tuple) < 2:
            return None
        pts: list[tuple[float, float]] = []
        for i, j in itertools.combinations(seq_tuple, 2):
            inter = projected_cones[i].intersection(projected_cones[j])
            if inter.is_empty or inter.area <= 0:
                continue
            pts.append(get_centroid_latlon(inter))
        if not pts:
            return None
        lats, lons = zip(*pts)
        return float(np.median(lats)), float(np.median(lons))

    group_to_smoke = {g: group_smoke_location(g) for g in localized_groups}

    seq_to_groups = defaultdict(list)
    seq_to_smokes = defaultdict(list)
    for g in localized_groups:
        smo = group_to_smoke[g]
        for sid in g:
            seq_to_groups[sid].append(g)
            seq_to_smokes[sid].append(smo)

    df["event_groups"] = df["id"].astype(int).map(lambda sid: seq_to_groups.get(sid, [(sid,)]))
    df["event_smoke_locations"] = df["id"].astype(int).map(lambda sid: seq_to_smokes.get(sid, []))

    return df
