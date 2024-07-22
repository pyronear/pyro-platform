# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from dash import html


def create_wildfire_list():
    """
    Creates a container for the detection list with a fixed height and scrollable content.

    This function generates a Dash HTML Div element containing a header and an empty container.
    The empty container ('wildfire-list-container') is meant to be populated with detection buttons
    dynamically via a callback. The container has a fixed height and is scrollable, allowing
    users to browse through a potentially long list of detections.

    Returns:
    - dash.html.Div: A Div element containing the header and the empty container for detection buttons.
    """
    # Set a fixed height for the detection list container and enable scrolling
    wildfire_list_style = {
        "height": "calc(100vh - 120px)",  # Adjust the height as required
        "overflowY": "scroll",  # Enable vertical scrolling
        "padding": "10px",
    }

    return html.Div(
        [
            html.H1("Detections en cours", style={"textAlign": "center", "fontSize": "30px"}),
            html.Div(id="wildfire-list-container", style=wildfire_list_style, children=[]),  # Empty container
        ]
    )
