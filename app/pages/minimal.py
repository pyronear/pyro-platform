# Copyright (C) 2020-2022, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

"""
The following Python file is dedicated to the alert screen of the web application.
The alert screen corresponds to a web page which will be displayed on a big screen in the CODIS room. There will be no
interaction with the user. The main use of this page is to display a "sober" screen when there are no alerts. When an
alert pops out, the screen will automatically change to display various information.
Most functions defined below are designed to be called in the main.py file.
"""

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

from utils.alerts import retrieve_site_from_device_id

# ----------------------------------------------------------------------------------------------------------------------
# CONTENT


def build_no_alert_detected_screen():
    """
    The following function builds the no alert screen.
    """
    # background image as style
    style = {
        "backgroundImage": 'url("/assets/images/pyro_alert_off.png")',
        "backgroundRepeat": "no-repeat",
        "backgroundPosition": "center",
        "backgroundSize": "cover",
        "position": "fixed",
        "height": "100%",
        "width": "100%",
    }

    return style


def build_alert_detected_screen(img_url, last_alert, site_devices_data):
    """
    This function is used in the main.py file to create the alert screen when its on, i.e. when there is an alert
    ongoing.
    It takes as arguments:
    - 'img_url': the URL address of the alert frame to be displayed on the left of the map;
    - 'alert_metadata': a dictionary containing metadata about the ongoing alert
    - 'last_alert': pd.DataFrame of the last alert
    All these inputs are instantiated in the main.py file via a call to the API.
    """
    # Get lat and lon from last_alert
    lat, lon = round(last_alert["lat"], 4), round(last_alert["lon"], 4)

    # Get device id for last_alert
    device_id = last_alert["device_id"]

    # Retrieve the name of the site from the device id
    try:
        site_name = retrieve_site_from_device_id(device_id, site_devices_data)
    except Exception:
        site_name = ""

    # Get azimuth from last_alert
    azimuth = round(last_alert["yaw"], 1)

    # Background image
    background_image = html.Img(
        id="alert_background",
        src="/assets/images/pyro_alert_on.png",
        style={
            "position": "fixed",
            "width": "100vw",
            "height": "100vh",
        },
    )

    # Fire icon
    fire_icon = html.Img(
        id="fire_icon",
        src="/assets/images/pyro_fire_logo.png",
        className="blink-image",
        style={"height": "100%"},
    )

    # Alert metadata div
    alert_metadata_div = html.Div(
        children=[
            html.P("Coordonnées de la tour : {}, {}".format(lat, lon)),
            html.P("ID de caméra : {}".format(device_id)),
            html.P("Azimuth : {}°".format(azimuth)),
        ]
    )

    # Fire text div (left part of screen)
    fire_text_div = html.Div(
        id="fire_text_div",
        children=[
            html.Div(
                html.P(
                    f"Tour : {site_name}",
                ),
                style={
                    "font-size": "3.5vw",
                    "color": "#054546",
                    "font-weight": "bold",
                },
            ),
            html.Div(
                alert_metadata_div,
                style={
                    "font-size": "2vw",
                    "color": "#054546",
                },
            ),
        ],
        style={
            "margin-top": "7.5%",
        },
    )

    # Final layout: one row containing 2 columns, and each column contains two rows
    layout_div = [
        background_image,
        dbc.Row(
            children=[
                dbc.Col(
                    id="col_fire_text",
                    children=[
                        dbc.Row(
                            id="fire_icon_rwo",
                            children=fire_icon,
                            style={
                                "display": "flex",
                                "justify-content": "center",
                                "height": "75%",
                            },
                        )
                    ],
                    style={
                        "width": "50%",
                        "margin": "2.5%",
                    },
                ),
                dbc.Col(
                    id="col_image_fire",
                    children=[
                        dbc.Row(
                            html.Div(
                                html.Div(
                                    html.P("DÉPART DE FEU"),
                                    style={
                                        "font-size": "6vw",
                                        "color": "#fd4848",
                                        "font-weight": "bold",
                                        "margin-top": "5%",
                                    },
                                    className="blink-image",
                                ),
                            ),
                            style={
                                "display": "flex",
                                "justify-content": "center",
                                "padding-bottom": "7%",
                            },
                        ),
                        dbc.Row(
                            id="fire_text_row",
                            children=fire_text_div,
                            style={
                                "display": "flex",
                                "justify-content": "center",
                                # "margin-right": "2.5%",
                            },
                        ),
                    ],
                    style={
                        "width": "50%",
                        "margin": "2.5%",
                    },
                ),
            ],
            style={
                "height": "100%",
            },
        ),
    ]

    style = {
        "height": "100%",
        "width": "100%",
        "position": "fixed",
    }

    return layout_div, style


# ----------------------------------------------------------------------------------------------------------------------
# App layout
# The following block gathers elements defined above and returns them via the alert_screen function
def AlertMinimal():
    """
    The following function is used in the main.py file to build the layout of the big screen page.
    """
    layout = html.Div(
        children=[
            dcc.Interval(id="interval-component-alert-screen", interval=10 * 1000),
            html.Div(id="core_layout_alert_screen", children=[]),
        ],
        style={
            "height": "100%",
            "width": "100%",
            "position": "fixed",
        },
    )
    return layout
