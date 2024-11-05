# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from dash import html


def create_event_list():
    """
    Creates a container for the alert list with a fixed height and scrollable content.

    This function generates a Dash HTML Div element containing a header and an empty container.
    The empty container ('alert-list-container') is meant to be populated with alert buttons
    dynamically via a callback. The container has a fixed height and is scrollable, allowing
    users to browse through a potentially long list of alerts.

    Returns:
    - dash.html.Div: A Div element containing the header and the empty container for alert buttons.
    """
    # Set a fixed height for the alert list container and enable scrolling
    event_list_style = {
        "height": "calc(100vh - 120px)",  # Adjust the height as required
        "overflowY": "scroll",  # Enable vertical scrolling
        "padding": "10px",
    }

    return html.Div(
        [
            html.Div(
                id="alert-list-container", 
                className="alert-list-container", 
                style=event_list_style, 
                children=[]),  # Empty container
        ]
    )
