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

def build_dashboard_sites_overview(sdis_devices_data):

    sdis_devices_data['is_active'] = sdis_devices_data['last_ping_hours_dif'] >= -3

    per_site_summary = sdis_devices_data.groupby('site').agg(
        {
            'login': 'nunique',
            'is_active': 'sum'
        }
    ).reset_index()

    per_site_summary['ratio'] = per_site_summary['is_active'] / per_site_summary['login']

    per_site_summary['color'] = per_site_summary['ratio'].map(
        lambda ratio: {0: '#FD5252', 1: '#5BBD8C'}.get(ratio, '#F6B52A')
    )

    div_list = []

    for _, row in per_site_summary.iterrows():
        div_list.append(
            html.Div(
                children=[
                    html.H4(
                        f'{row["site"].replace("_", " ").title()}',
                        style={'color': row['color'], 'margin-top': '10px'}
                    ),
                    html.P(f'{row["is_active"]} caméra(s) active(s) sur {row["login"]}')
                ],
                style={
                    'border-style': 'solid',
                    'border-width': '2px',
                    'border-color': row['color'],
                    'width': '50%',
                    'margin-top': '20px'
                },
            )
        )

    return html.Center(div_list)


# The following block builds the dashboard_table, adding a status column that indicates if devices are KO or OK


def build_dashboard_table(sdis_devices_data):

    sdis_devices = pd.DataFrame(sdis_devices_data)

    sdis_devices.drop(columns=['site'], inplace=True)

    sdis_devices['id'] = sdis_devices.index
    dashboard = dash_table.DataTable(
        data=sdis_devices.to_dict('records'),
        sort_action='native',
        columns=[
            {'name': 'ID de la caméra', 'id': 'login', 'type': 'text'},
            {'name': 'Azimuth', 'id': 'yaw', 'type': 'numeric'},
            {'name': 'Latitude', 'id': 'lat', 'type': 'numeric'},
            {'name': 'Longitude', 'id': 'lon', 'type': 'numeric'},
            {'name': 'Dernier ping', 'id': 'last_ping', 'type': 'datetime'},
            {'name': 'Last Ping Diff', 'id': 'last_ping_hours_dif', 'type': 'numeric'},
            {'name': 'Statut', 'id': 'status', 'type': 'text'},
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
        dcc.Markdown('---'),
        dcc.Interval(id="interval-component-dashboard-screen", interval=60 * 1000),
        html.H2(
            'Statut des sites de détection',
            style={'margin-left': '75px'}
        ),
        html.Div(id='dashboard_per_site_summary'),
        dcc.Markdown('---'),
        html.H2(
            'Détail par caméra',
            style={'margin-left': '75px'}
        ),
        html.Center(
            html.Div(
                id='dashboard_table',
                style={'width': '90%'}
            )
        )
    ]
