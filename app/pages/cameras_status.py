# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
import pytz
from dash import html
from timezonefinder import TimezoneFinder
from translations import translate

import config as cfg

tf = TimezoneFinder()


def display_cam_cards(cameras):
    no_cam_img_url = "assets/images/no-image.svg"
    cards = []

    for _, row in cameras.iterrows():
        clock_image_src_issue = "assets/images/clock-error.svg"
        last_active_at_style_issue = {"margin": "0", "color": "#f44336"}

        try:
            # Step 1: Parse original UTC timestamp
            ts_utc = datetime.fromisoformat(str(row["last_active_at"])).replace(tzinfo=pytz.utc)

            # Step 2: Get local timezone from lat/lon
            timezone_str = tf.timezone_at(lat=round(row["lat"], 4), lng=round(row["lon"], 4))
            timezone_str = timezone_str or "UTC"
            local_tz = pytz.timezone(timezone_str)

            # Step 3: Convert timestamp to local time
            dt_local = ts_utc.astimezone(local_tz)

            # Step 4: Get current time in same local timezone
            now_local = datetime.now(local_tz)

            # Step 5: Inactivity check
            if now_local - dt_local > timedelta(minutes=cfg.CAMERA_INACTIVITY_THRESHOLD_MINUTES):
                clock_image_src = clock_image_src_issue
                last_active_at_style = last_active_at_style_issue
            else:
                clock_image_src = "assets/images/clock.svg"
                last_active_at_style = {"margin": "0"}

            formatted_last_active = dt_local.strftime("%Y-%m-%d %H:%M")
        except Exception:
            formatted_last_active = None
            clock_image_src = clock_image_src_issue
            last_active_at_style = last_active_at_style_issue

        card = dbc.Col(
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.H4(row["name"], className="card-title"),
                            html.Div(
                                [
                                    html.Img(
                                        src=clock_image_src,
                                        style={"width": "20px", "height": "20px", "marginRight": "5px"},
                                    ),
                                    html.P(formatted_last_active or "N/A", style=last_active_at_style),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                        ],
                        style={"padding": "10px"},
                    ),
                    dbc.CardImg(
                        src=row["last_image_url"] if row["last_image_url"] is not None else no_cam_img_url,
                        top=False,
                        style={"width": "100%", "borderRadius": "0"},
                    ),
                ],
                className="pyronear-card",
            ),
            width=6,
            md=3,
            xxl=2,
            style={"marginTop": "1.5rem"},
        )
        cards.append(card)

    return dbc.Row(cards)


def cameras_status_layout(user_token, api_cameras, lang="fr"):
    return dbc.Container(
        [
            dbc.Breadcrumb(
                items=[
                    {"label": "Homepage", "href": "/", "external_link": False},
                    {"label": translate("breadcrumb", lang), "active": True},
                ],
            ),
            html.H1(translate("page_title", lang), style={"font-size": "2rem"}),
            html.Div(id="camera-cards-container", children=[]),
        ],
        fluid=True,
    )
