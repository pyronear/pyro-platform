# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html
from dateutil.relativedelta import relativedelta  # type: ignore

pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"


def Navbar(lang="fr"):
    navbar = dbc.Navbar(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.A(
                            html.Img(src=pyro_logo, height="30px"),
                            href="/",
                        ),
                        width=3,
                    ),
                ],
                align="center",
            ),
            html.Div(
                className="ml-auto",
                style={"display": "flex", "flexDirection": "row", "gap": "10px", "marginRight": "10px"},
                children=[
                    # 📅 Date Picker Button
                    dbc.Button(
                        id="open-datepicker-modal",
                        children=["📅 ", html.Span(id="datepicker_button_text")],
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 📷 Camera Status Button
                    dbc.Button(
                        id="camera-status-button",
                        children=["📷 ", html.Span(id="camera_status_button_text")],
                        href="/cameras-status",
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 🚨 Alarm Button
                    dbc.Button(
                        id="alarm-status-button",
                        children=["🚨 ", html.Span(id="blinking_alarm_button_text")],
                        href="/blinking-alarm",
                        color="light",
                        style={"fontSize": "16px"},
                    ),
                    # 🌐 Language Buttons
                    dbc.Button(["🇫🇷", " FR"], id="btn-fr", color="light", className="mr-2"),
                    dbc.Button(["🇪🇸", " ES"], id="btn-es", color="light"),
                ],
            ),
        ],
        id="main_navbar",
        color="#044448",
        dark=True,
        style={"display": "flex", "justify-content": "space-between"},
    )

    # Modal with DatePicker
    datepicker_modal = dbc.Modal(
        [
            dbc.ModalHeader("Sélectionnez une date" if lang == "fr" else "Select a date"),
            dbc.ModalBody(
                dcc.DatePickerSingle(
                    id="my-date-picker-single",
                    min_date_allowed=date.today() - relativedelta(months=3),
                    max_date_allowed=date.today(),
                    initial_visible_month=date.today(),
                )
            ),
            dbc.ModalFooter(
                dbc.Button("Fermer" if lang == "fr" else "Close", id="close-datepicker-modal", className="ml-auto")
            ),
        ],
        id="datepicker-modal",
        is_open=False,
        centered=True,
    )

    return html.Div([navbar, datepicker_modal])
