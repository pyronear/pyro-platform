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
    """
    This function, called in main.py, builds the site overview which provides the user with an overview of the con-
    nectivity status of the relevant sites. Building upon data gathered in main.py (which corresponds to the
    "sdis_devices_data" argument), we create one Div per site with the following font and border columns:

    - red if no device is active on the site;
    - orange if at least one device is KO and at least one device is active on the site;
    - green if all devices are active on the site.
    """

    # Adding a boolean column indicating whether the device is active or not (last ping was less than 3 hours ago)
    sdis_devices_data['is_active'] = sdis_devices_data['last_ping_hours_dif'] >= -3

    # Getting the number of unique devices and the number of active devices for each site in the table
    per_site_summary = sdis_devices_data.groupby('site').agg(
        {
            'login': 'nunique',
            'is_active': 'sum'
        }
    ).reset_index()

    # The ratio of active devices allows determines what color will be used for the site
    per_site_summary['ratio'] = per_site_summary['is_active'] / per_site_summary['login']

    # Color is mapped as indicated above, using the ratio of active devices
    per_site_summary['color'] = per_site_summary['ratio'].map(
        lambda ratio: {0: '#FD5252', 1: '#5BBD8C'}.get(ratio, '#F6B52A')
    )

    # We create one Div per site with basic information on the connectivity of the corresponding devices
    div_list = []

    for _, row in per_site_summary.iterrows():
        div_list.append(
            html.Div(
                children=[
                    # Site name written in the color corresponding to the connectivity status of the site
                    html.H4(
                        f'{row["site"].replace("_", " ").title()}',
                        style={'color': row['color'], 'margin-top': '10px'}
                    ),
                    # Number of active devices vs. number of unique devices on the site
                    html.P(f'{row["is_active"]} caméra(s) active(s) sur {row["login"]}')
                ],
                style={
                    'border-style': 'solid',
                    'border-width': '2px',
                    'border-color': row['color'],  # Setting the relevant color for the border of the Div
                    'width': '50%',
                    'margin-top': '20px'
                },
            )
        )

    # How many rows do we need to display the different site summaries?
    nb_rows = per_site_summary['site'].nunique() / 2 + per_site_summary['site'].nunique() % 2

    output = [
        # Normal case: we add a row with two columns, each corresponding to two consecutive site summary Divs
        dbc.Row(
            children=[
                dbc.Col(div_list[2 * i], width=6),
                dbc.Col(div_list[2 * i + 1], width=6)
            ],
        )
        if 2 * i + 1 < len(div_list)
        # If the last row needs to only contain one Div due to the number of unique sites to display
        else dbc.Row(
            children=[
                dbc.Col(div_list[2 * i], width=6),
                dbc.Col(html.Div(''), width=6)
            ],
        )
        for i in range(int(nb_rows))
    ]

    return output


def build_dashboard_table(sdis_devices_data):
    """
    This function, called in main.py, builds the dashboard table which provides the user with an overview of the con-
    nectivity status of the relevant devices. Building upon data gathered in main.py (which corresponds to the
    "sdis_devices_data" argument), a column is added to indicate the status of the device. The "Last Ping Diff" column
    is hidden on the other hand.
    """

    sdis_devices = pd.DataFrame(sdis_devices_data)

    # Site column is useful for the site overview but not for this per-device table
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
        # Navigation bar
        html.Div(navbar_dashboard),
        dcc.Markdown('---'),

        # Interval component used to update the information displayed on the dashboard every minute
        dcc.Interval(id="interval-component-dashboard-screen", interval=60 * 1000),

        # Site connectivity overview
        html.H3(
            'Statut des sites de détection',
            style={'margin-left': '75px'}
        ),
        html.Center(id='dashboard_per_site_summary'),
        dcc.Markdown('---'),

        # Main table with the per-device detail
        html.H3(
            'Détail par caméra',
            style={'margin-left': '75px'}
        ),
        html.Center(
            html.Div(
                id='dashboard_table',
                style={
                    'width': '90%',
                    'margin-top': '20px'
                }
            )
        )
    ]
