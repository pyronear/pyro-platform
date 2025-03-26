# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html
from dateutil.relativedelta import relativedelta

import config as cfg
from components.alerts import alert_layout


def history_layout(api_cameras, lang="fr"):
    translate = cfg.TRANSLATION["alert_default"]
    translate["fr"]["no_alert_default_image"] = cfg.TRANSLATION["history"]["fr"]["no_alert_history_image"]
    translate["es"]["no_alert_default_image"] = cfg.TRANSLATION["history"]["es"]["no_alert_history_image"]

    return dbc.Container(
        [
            dbc.Breadcrumb(
                items=[
                    {"label": "Homepage", "href": "/", "external_link": False},
                    {"label": cfg.TRANSLATION["history"][lang]["breadcrumb"], "active": True},
                ],
            ),
            dbc.Row(
                [
                    html.H1(cfg.TRANSLATION["history"][lang]["page_title"], style={"font-size": "2rem"}),
                    html.Div(
                        [
                            dcc.DatePickerSingle(
                                id="my-date-picker-single",
                                min_date_allowed=date.today()
                                - relativedelta(months=cfg.ALERTS_HISTORICAL_DEPTH_MONTHS),
                                max_date_allowed=date.today(),
                                initial_visible_month=date.today(),
                            )
                        ]
                    ),
                ],
            ),
            html.Div(id="date-picker-is-empty-info", style={"margin-bottom": "5px"}),
            alert_layout(api_cameras, translate, lang, id_suffix="-history"),
        ],
        fluid=True,
    )
