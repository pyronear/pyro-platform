import dash_bootstrap_components as dbc
from dash import dcc, html
from datetime import date
from dateutil.relativedelta import relativedelta

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
                    # DatePicker Button
                    # Replace the existing datepicker button with this:
                    dbc.Button(
                        id="open-datepicker-modal",
                        children="📅",  # Will be updated with the selected date
                        color="light",
                        style={"fontSize": "16px"},
                    ),

                    # Camera Status Button
                    dbc.Button(
                        html.Div(
                            [
                                html.Img(
                                    src="assets/images/camera.svg",
                                    style={"width": "20px", "height": "20px", "marginRight": "5px"},
                                ),
                                html.P(children=[], style={"margin": "0"}, id="camera_status_button_text"),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        href="/cameras-status",
                        outline=True,
                        className="navbar-button",
                    ),
                    # Blinking Alarm Button
                    dbc.Button(
                        html.Div(
                            [
                                html.Img(
                                    src="assets/images/alarm.svg",
                                    style={"width": "20px", "height": "20px", "marginRight": "5px"},
                                ),
                                html.P(children=[], style={"margin": "0"}, id="blinking_alarm_button_text"),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        href="/blinking-alarm",
                        outline=True,
                        className="navbar-button",
                    ),
                    # Language Buttons
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

    # Modal that contains the DatePicker
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
