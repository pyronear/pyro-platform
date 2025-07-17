# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash_bootstrap_components as dbc
from dash import dcc, html
from translations import translate


def export_layout(lang="fr"):
    return html.Div(
        [
            html.H2(translate("export_title", lang), id="export-title"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(translate("start_date", lang), id="export-start-date-label"),
                            html.Div(
                                dcc.DatePickerSingle(
                                    id="export-start-date",
                                    display_format="YYYY-MM-DD",
                                ),
                                style={"marginTop": "5px", "marginBottom": "10px"},
                            ),
                        ],
                        style={"marginRight": "20px"},
                    ),
                    html.Div([
                        html.Label(translate("end_date", lang), id="export-end-date-label"),
                        html.Div(
                            dcc.DatePickerSingle(
                                id="export-end-date",
                                display_format="YYYY-MM-DD",
                            ),
                            style={"marginTop": "5px", "marginBottom": "10px"},
                        ),
                    ]),
                ],
                style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"},
            ),
            dbc.Button(
                id="export-button",
                children=translate("download", lang),
                color="primary",
                className="mb-1",
                style={"marginBottom": "15px"},
                n_clicks=0,
            ),
            html.Div(id="export-status-text", style={"marginBottom": "10px", "fontStyle": "italic"}),
            html.Div(id="export-status-text-done", style={"marginBottom": "10px", "fontStyle": "italic"}),
            dcc.Download(id="export-download"),
            dcc.Store(id="export-trigger", data=False),
        ],
        style={"textAlign": "center"},
    )
