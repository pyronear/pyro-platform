# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json
from datetime import datetime
from io import StringIO
from typing import List

import pandas as pd
import pytz
from timezonefinder import TimezoneFinder

tf = TimezoneFinder()


def convert_time(df):
    df_ts_local = []
    for _, row in df.iterrows():
        lat = round(row["lat"], 4)
        lon = round(row["lon"], 4)

        # Convert created_at to a timezone-aware datetime object assuming it's in UTC
        alert_ts_utc = datetime.fromisoformat(str(row["created_at"])).replace(tzinfo=pytz.utc)

        # Find the timezone for the alert location
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if timezone_str is None:  # If the timezone is not found, handle it appropriately
            timezone_str = "UTC"  # Fallback to UTC or some default
        alert_timezone = pytz.timezone(timezone_str)

        # Convert alert_ts_utc to the local timezone of the alert
        df_ts_local.append(alert_ts_utc.astimezone(alert_timezone).strftime("%Y-%m-%dT%H:%M:%S"))

    return df_ts_local


def read_stored_DataFrame(data):
    """
    Reads a JSON-formatted string representing a pandas DataFrame stored in a dcc.Store.

    Args:
        data (str): A JSON-formatted string representing the stored DataFrame.

    Returns:
        tuple: A tuple containing the DataFrame and a boolean indicating whether data has been loaded.
    """
    # if "false" in data:
    #     return pd.DataFrame().to_json(orient="split"), False
    data_dict = json.loads(data)

    # Check if 'data' is empty or if 'columns' is empty
    if not len(data_dict["data"]):
        # If either is empty, create an empty DataFrame
        return pd.DataFrame().to_json(orient="split"), data_dict["data_loaded"]
    else:
        # Otherwise, read the JSON data into a DataFrame
        return (
            pd.read_json(StringIO(data_dict["data"]), orient="split"),
            data_dict["data_loaded"],
        )


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
