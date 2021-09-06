# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# Various modules provided by Dash to build the page layout
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd

# ----------------------------------------------------------------------------------------------------------------------
# CONTENT
# The following block builds the dashboard_table, adding a status column that indicates if devices are KO or OK


def build_dashboard_table(sdis_devices_data):

    sdis_devices = pd.DataFrame(sdis_devices_data)

    sdis_devices['id'] = sdis_devices.index
    dashboard = dash_table.DataTable(
        data=sdis_devices.to_dict('records'),
        sort_action='native',
        columns=[
            {'name': 'Device Id', 'id': 'login', 'type': 'text'},
            {'name': 'Azimuth', 'id': 'yaw', 'type': 'numeric'},
            {'name': 'Latitude', 'id': 'lat', 'type': 'numeric'},
            {'name': 'Longitude', 'id': 'lon', 'type': 'numeric'},
            {'name': 'Last Ping', 'id': 'last_ping', 'type': 'datetime'},
            {'name': 'Last Ping Diff', 'id': 'last_ping_hours_dif', 'type': 'numeric'},
            {'name': 'Status', 'id': 'status', 'type': 'text'},
        ],
        style_cell_conditional=[
            {'if': {
                'column_id': 'last_ping_hours_dif', },
                'display': 'None', },
            {'if': {
                'column_id': 'status', },
                'backgroundColor': 'rgb(51, 204, 51)', },
        ],
        style_data_conditional=[
            {'if': {
                'filter_query': '{last_ping_hours_dif} < -3',  # 3 hours here, can be adjusted
                'column_id': 'status'
            },
                'backgroundColor': 'tomato',
                'color': 'black'
            }, ],
        style_header={
            'backgroundColor': 'rgb(10, 82, 83)',
            'color': 'white',
            'textAlign': 'left'},
        style_cell={
            'textAlign': 'left'},
    )

    return dashboard


# ----------------------------------------------------------------------------------------------------------------------
# App layout
# The following block gathers elements defined above and returns them via the DashboardScreen function
def DashboardScreen():

    pyro_logo = "https://pyronear.org/img/logo_letters_orange.png"

    # Navbar Title
    user_item = html.Div(
        "Dashboard de monitoring des devices",
        id="title",
        className="mx-auto order-0",
        style={'color': 'white', 'align': 'center', 'justify': 'center'})

    # Navbar component
    navbar_dashboard = dbc.Navbar(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=pyro_logo, width="120px")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="#",
            ),
            dbc.Collapse([user_item], id="navbar-title", navbar=True),
        ],
        id="dashboard_navbar",
        color='#044448',
        dark=True,
    )

    return [
        html.Div(navbar_dashboard),
        dcc.Interval(id="interval-component-dashboard-screen", interval=60 * 1000),
        dcc.Markdown('---'),
        html.Div(id='dashboard_table'),
    ]
