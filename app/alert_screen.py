# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following Python file is dedicated to the alert screen of the web application.
The alert screen corresponds to a web page which will be displayed on a big screen in the CODIS room. There will be no
interaction with the user. The main use of this page is to display a "sober" screen when there are no alerts. When an
alert pops out, the screen will automatically change to display various information.
Most functions defined below are designed to be called in the main.py file.
"""

# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# Various modules provided by Dash to build the page layout
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT
def build_no_alert_detected_screen():
    """
    The following function builds the no alert screen.
    """
    # background image as style
    style = {
        "backgroundImage": 'url("/assets/pyro_alert_off.png")',
        "backgroundRepeat": "no-repeat",
        "backgroundPosition": "center",
        "backgroundSize": "cover",
        "position": "fixed",
        "height": "100%",
        "width": "100%",
    }

    return style


def build_alert_detected_screen(img_url, last_alert):
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

    # Get azimuth from last_alert
    azimuth = round(last_alert["azimuth"], 1)

    # Background image
    background_image = html.Img(
        id="alert_background",
        src="/assets/pyro_alert_on.png",
        style={
            "position": "fixed",
            "width": "100vw",
            "height": "100vh",
        },
    )

    # Fire icon
    fire_icon = html.Img(
        id="fire_icon",
        src="/assets/pyro_fire_logo.png",
        className="blink-image",
        style={"height": "100%"},
    )

    # Detection frames
    alert_frame = html.Img(
        id="alert_frame",
        src=img_url,
        style={
            "position": "relative",
            "width": "100%",
            "height": "100%",
            "object-fit": "contain",
        },
    )

    # Fire alert image div (right of the screen)
    # Multiple frames are rendered here (to make it look like a GIF)
    fire_images_div = html.Div(
        id="fire_alert_div",
        children=[
            alert_frame,
            dcc.Interval(id="interval-component-img-refresh", interval=3 * 1000),
        ],
        style={"display": "flex", "height": "100%", "width": "100%"},
    )

    # Alert metadata div
    alert_metadata_div = html.Div(
        children=[
            html.P("Tour: Serre en Don"),
            html.P("Coordonnées de la tour: {}, {}".format(lat, lon)),
            html.P("Id de caméra: {}".format(device_id)),
            html.P("Azimuth: {}".format(azimuth)),
        ]
    )

    # Fire text div (left part of screen)
    fire_text_div = html.Div(
        id="fire_text_div",
        children=[
            html.Div(
                html.P(
                    "DFCI: KD62D6.5",
                ),
                style={
                    "font-size": "2vw",
                    "color": "#054546",
                    "font-weight": "bold",
                },
            ),
            html.Div(
                alert_metadata_div,
                style={
                    "font-size": "1.75vw",
                    "color": "#054546",
                },
            ),
        ],
        style={
            "margin-top": "5%",
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
                                "height": "30%",
                            },
                        ),
                        dbc.Row(
                            id="fire_text_row",
                            children=fire_text_div,
                            style={
                                "display": "flex",
                                "justify-content": "center",
                                "margin-right": "2.5%",
                            },
                        ),
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
                                        "font-size": "4vw",
                                        "color": "#fd4848",
                                        "font-weight": "bold",
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
                            id="fire_images_row",
                            children=fire_images_div,
                            style={
                                "display": "flex",
                                "justify-content": "center",
                                "margin-right": "2.5%",
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
def AlertScreen():
    """
    The following function is used in the main.py file to build the layout of the big screen page.
    """
    layout = html.Div(
        children=[
            dcc.Interval(id="interval-component-alert-screen", interval=3 * 1000),
            html.Div(id="core_layout_alert_screen", children=[]),
        ],
        style={
            "height": "100%",
            "width": "100%",
            "position": "fixed",
        },
    )
    return layout
