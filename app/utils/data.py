# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import List

import pandas as pd
import pytz
from timezonefinder import TimezoneFinder

from utils.sites import get_sites

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


# Sites


def retrieve_site_from_device_id(api_client, user_credentials, device_id):
    """
    Retrieves the site name associated with a given device ID by looking up in the site devices data.

    Args:
        api_client: API client to interact with the remote server.
        user_credentials (tuple): User credentials (username, password).
        device_id: Device ID for which the site name is to be retrieved.

    Returns:
        str: The name of the site associated with the given device ID.
    """
    site_devices_data = load_site_data_file(api_client, user_credentials)
    device_id = str(int(device_id))

    if device_id in site_devices_data.keys():
        return site_devices_data[device_id]
    else:
        site_devices_data = load_site_data_file(api_client, user_credentials, force_dl=True)

        return site_devices_data[device_id]


def load_site_data_file(api_client, user_credentials, site_devices_file="site_devices.json", force_dl=False):
    """
    Loads site device data from a file or fetches it from the API if the file does not exist or if forced to download.

    Args:
        api_client: API client to interact with the remote server.
        user_credentials (tuple): User credentials (username, password).
        site_devices_file (str): Path to the file where site device data is stored. Defaults to 'site_devices.json'.
        force_dl (bool): If True, forces downloading the data from the API. Defaults to False.

    Returns:
        A dictionary mapping site names to device IDs.
    """
    site_devices_path = Path(site_devices_file)

    if site_devices_path.is_file() and not force_dl:
        with site_devices_path.open() as json_file:
            return json.load(json_file)

    client_sites = get_sites(user_credentials)
    site_devices_dict = {}
    for _, site in client_sites.iterrows():
        site_ids = set(api_client.get_site_devices(site["id"]).json())
        for site_id in site_ids:
            site_devices_dict[str(site_id)] = site["name"].replace("_", " ")
    with site_devices_path.open("w") as fp:
        json.dump(site_devices_dict, fp)

    return site_devices_dict
