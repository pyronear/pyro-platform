# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import ast
from typing import List

import pandas as pd


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
