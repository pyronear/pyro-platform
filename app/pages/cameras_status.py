# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
from dash import html
from translations import translate

import config as cfg


def display_cam_cards(cameras):
    no_cam_img_url = "assets/images/no-image.svg"

    cards = []
    print(cameras)
    for _, row in cameras.iterrows():
        clock_image_src_issue = "assets/images/clock-error.svg"
        last_active_at_style_issue = {"margin": "0", "color": "#f44336"}

        if not row["last_active_at_local"]:
            clock_image_src = clock_image_src_issue
            last_active_at_style = last_active_at_style_issue
        else:
            try:
                dt_local = datetime.strptime(row["last_active_at_local"], "%Y-%m-%d %H:%M")
                if datetime.now() - dt_local > timedelta(minutes=cfg.CAMERA_INACTIVITY_THRESHOLD_MINUTES):
                    clock_image_src = clock_image_src_issue
                    last_active_at_style = last_active_at_style_issue
                else:
                    clock_image_src = "assets/images/clock.svg"
                    last_active_at_style = {"margin": "0"}
            except Exception:
                # In case parsing fails
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
                                    html.P(
                                        f"{row['last_active_at_local']}",
                                        style=last_active_at_style,
                                    ),
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
