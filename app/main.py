# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following is the main file and the script to run in order to launch the app locally.

It can be launched from the root of the repository by running in a Terminal window:

"python app/main.py"

It is built around 5 main sections:

- Imports

- App instantiation and overall layout, which creates the app and related attributes

- Callbacks, which gathers the functions that create interactivity for:
    - The whole app
    - The "Alerts and Infrastructure" view
    - The "Risk Score" view
    - The homepage
    - The alert screen page

- Running the web-app server, which allows to launch the app via the Terminal command.
"""

# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# --- General imports

# From the pyroclient package
from pyroclient import Client

# Main Dash imports, used to instantiate the web-app and create callbacks (ie. to generate interactivity)
import os
import dash
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate

# Flask caching import
from flask_caching import Cache

# Various modules provided by Dash and Dash Leaflet to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# Pandas to read the login correspondences file
import pandas as pd

# Import used to make the API call in the login callback
import requests

# Various utils
import numpy as np
import json
from datetime import datetime, timedelta

# --- Imports from other Python files

import config as cfg  # Cf. config.py file

# From alert_screen.py, we import the main layout instantiation function and some others needed for interactivity
from alert_screen import AlertScreen, build_no_alert_detected_screen, build_alert_detected_screen

# From homepage.py, we import the main layout instantiation function
from homepage import Homepage

# From dashboard_screen.py, we import the main layout instantiation function
from dashboard_screen import DashboardScreen, build_dashboard_table

# From other Python files, we import some functions needed for interactivity
from homepage import choose_map_style, display_alerts_frames
from risks import build_risks_geojson_and_colorbar
from alerts import build_alerts_elements, get_site_devices_data, build_individual_alert_components, \
    build_alert_overview, display_alert_selection_area, build_sites_markers, retrieve_site_from_device_id
from utils import choose_layer_style, build_filters_object, build_legend_box, is_hour_between

# Importing the pre-instantiated Pyro-API client
from services import api_client


# ----------------------------------------------------------------------------------------------------------------------
# APP INSTANTIATION & OVERALL LAYOUT

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# We define a few attributes of the app object
app.title = 'Pyronear - Monitoring platform'
app.config.suppress_callback_exceptions = True
server = app.server  # Gunicorn will be looking for the server attribute of this module

response = requests.get('https://api.pyronear.org/devices/', headers=api_client.headers)
# Check token expiration
if response.status_code == 401:
    api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
    response = requests.get('https://api.pyronear.org/devices/', headers=api_client.headers)

# We create a rough layout, filled with the content of the homepage/alert page
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content", style={"height": "100%"}),

        # Storage component which contains data relative devices
        dcc.Store(
            id="devices_data_storage",
            storage_type="session",
            data=response.json()
        ),

        # Main interval that fetches API alerts data
        dcc.Interval(id="main_api_fetch_interval", interval=25 * 1000),

        # Storage components which contains data relative to alerts
        dcc.Store(
            id="store_live_alerts_data",
            storage_type="session",
            data=json.dumps({'status': 'never_loaded_alerts_data'})
        ),
        dcc.Store(id="images_url_live_alerts", storage_type="session", data={}),

        dcc.Store(id="last_displayed_event_id", storage_type="session"),
        dcc.Store(id='images_to_display_on_big_screen', data={'frame_URLs': 'no_images'}, storage_type='session'),

        html.Div(id='alert_frame_update_new_event', style={'display': 'none'}),
        html.Div(id='alert_frame_update_interval', style={'display': 'none'}),

        # Session storage component to avoid re-opening the login modal at each refresh
        # [NOT SUCCESSFUL YET]
        dcc.Store(id='login_storage', storage_type='session', data={'login': 'no'}),

        # Session storage component which fetches sunrise and sunset times to filter night alerts
        dcc.Store(id='night_time',
                  storage_type='session',
                  data=requests.get('https://api.sunrise-sunset.org/json?lat=44.62112179704533 '
                                    '&lng=4.273138903528911&formatted=0&date=today').json()),

        # Interval that refreshes the night_time storage and API fetch every 24h
        dcc.Interval(id='refresh_night_time', interval=24 * 3600 * 1000),

        # Storage component which contains data relative to site devices
        dcc.Store(
            id="site_devices_data_storage",
            storage_type="session",
            data=get_site_devices_data(client=api_client)
        ),

        # Storing alerts data for each event separately
        html.Div(id='individual_alert_data_placeholder', style={'display': 'none'}),
        html.Div(id='individual_alert_frame_placeholder', style={'display': 'none'}),

        # Storage component saving the IDs of alerts whose frames have already been loaded
        dcc.Store(id='loaded_frames', storage_type='session'),

        # Placeholder that stores the names of the sites associated with a live alert displayed on the platform
        html.Div(id='sites_with_live_alerts', children=[], style={'display': 'none'})
    ]
)


# Cache configuration
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': '.cache',
    'CACHE_DEFAULT_TIMEOUT': 60
})

# ----------------------------------------------------------------------------------------------------------------------
# CALLBACKS

# ----------------------------------------------------------------------------------------------------------------------
# General callbacks


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def display_page(pathname):
    """
    This callback takes the url path as input and returns the corresponding page layout,
    thanks to the instantiation functions built in the various .py files.
    """
    if pathname == "/alert_screen":
        return AlertScreen()
    elif pathname == "/dashboard_screen":
        return DashboardScreen()
    else:
        return Homepage()


@app.callback(
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n, is_open):
    """
    This overall callback on the navigation bar allows to toggle the collapse on small screens.
    """
    if n:
        return not is_open
    return is_open


@app.callback(
    [Output('layer_style_button', 'children'),
     Output('tile_layer', 'url'),
     Output('tile_layer', 'attribution')],
    Input('layer_style_button', 'n_clicks')
)
def change_layer_style(n_clicks=None):
    """
    -- Moving between schematic and satellite layers --

    This callback detects clicks on the button used to change the layer style of the map.

    It returns:

    - the right topographic or satellite view, by changing the 'url' and 'attribution'
    attributes of the 'tile_layer' object in the alerts map;
    - and the appropriate content for the button allowing to change the layer style.

    To do so, it relies on the choose_layer_style function defined in the alerts Python file.
    """
    if n_clicks is None:
        n_clicks = 0

    return choose_layer_style(n_clicks)


@app.callback(Output('night_time', 'data'),
              Input('refresh_night_time', 'n_intervals'),)
def refresh_night_time(n_intervals):
    return requests.get('https://api.sunrise-sunset.org/json?lat=44.62112179704533 '
                        '&lng=4.273138903528911&formatted=0&date=today').json()


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks determining what alert data and alert frame URLs are store


@app.callback(
    [Output('store_live_alerts_data', 'data'),
     Output('images_url_live_alerts', 'data'),
     Output('loaded_frames', 'data'),
     Output('main_api_fetch_interval', 'interval'),
     Output('sites_with_live_alerts', 'children')],
    Input('main_api_fetch_interval', 'n_intervals'),
    [State('store_live_alerts_data', 'data'),
     State('images_url_live_alerts', 'data'),
     State('devices_data_storage', 'data'),
     State('loaded_frames', 'data'),
     State('site_devices_data_storage', 'data'),
     State('night_time', 'data')]
)
def update_live_alerts_data(
    n_intervals,
    ongoing_live_alerts, ongoing_frame_urls,
    devices_data,
    already_loaded_frames,
    site_devices_data,
    night_time_data
):
    """
    This is the key callback of the platform. Triggered by the interval component, it queries the database via the API
    client so as to identify live alerts, load the associated data and trigger their display on the platform. This doc-
    string should be completed but more details can be found in the comments below.
    """

    # Fetching live alerts where is_acknowledged is False
    response = api_client.get_ongoing_alerts()
    # Check token expiration
    if response.status_code == 401:
        api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
        response = api_client.get_ongoing_alerts()
    response = response.json()
    # Only for demo purposes, this should be deleted for dev and later in production
    # response = {}

    # If there is no alert, we prevent the callback from updating anything
    if len(response) == 0:
        raise PreventUpdate

    # We store all alerts in a DataFrame and we want to select "live alerts",
    # Ie. alerts that correspond to a not-yet-acknowledged event
    all_alerts = pd.DataFrame(response)

    # We now want to build the boolean indexing mask that indicates whether or not the event is unacknowledged
    # We start by making an API call to fetch all events
    url = cfg.API_URL + '/events/'
    response = requests.get(url, headers=api_client.headers)
    if response.status_code == 401:
        api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
        response = requests.get(url, headers=api_client.headers)
    all_events = response.json()

    # Then, we construct a dictionary whose keys are the event IDs (as integers) and values are the corresponding
    # "is_acknowledged" field in the events table (boolean)
    is_event_acknowledged = {}
    for event in all_events:
        is_event_acknowledged[event['id']] = event['is_acknowledged']

    # We map this dictionary upon the column and revert the booleans with ~ as we want unacknowledged events
    mask_acknowledgement = ~all_alerts['event_id'].map(is_event_acknowledged)

    # And we deduce the subset of alerts that we can deem to be "live"
    live_alerts = all_alerts[mask_acknowledgement].copy()

    # We then fetch sunrise and sunset times and add a safety margin of 30 min (converting from UTC) to cover night time
    sunrise = night_time_data['results']['sunrise'][:-6]
    sunrise = datetime.fromisoformat(str(sunrise)) + timedelta(hours=2.5)
    sunrise = sunrise.time()

    sunset = night_time_data['results']['sunset'][:-6]
    sunset = datetime.fromisoformat(str(sunset)) + timedelta(hours=1.5)
    sunset = sunset.time()

    # Are there some live alerts during night time ? If yes let's filter them out
    mask = live_alerts['created_at'].map(lambda x: is_hour_between(sunrise, sunset, x))
    live_alerts = live_alerts[mask].copy()

    # Is there any live alert to display?
    if live_alerts.empty:
        # If not, we do not update any of the callback's output
        return json.dumps({}), {}, {'loaded_frames': []}, 5 * 1000, []

    else:
        # If yes, there is a bit of work to do!

        # We load the data contained by the store_live_alerts_data dcc.Store component
        temp = json.loads(ongoing_live_alerts)

        # Has some alert data already been loaded so far?
        if isinstance(temp, dict) and 'status' in temp.keys() and temp['status'] == 'never_loaded_alerts_data':
            # If the dictionary loaded from the store_live_alerts_data dcc.Store component corresponds to the initial
            # data attribute of the component, it means that alert data have never been loaded so far

            # Fetching live_alerts frames urls and instantiating a dict of live_alerts urls having event_id keys
            dict_images_url_live_alerts = {}

            # This void list will store the names of the sites for which a live alert is being displayed,
            # Enabling us later on to hide the corresponding site marker and only display the alert one
            sites_with_live_alerts = []

            # We iterate over newly loaded live alerts
            for _, row in live_alerts.iterrows():
                try:
                    # For each live alert, we fetch the URL of the associated frame
                    response = api_client.get_media_url(row["media_id"])
                    if response.status_code == 401:
                        api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
                        response = api_client.get_media_url(row["media_id"])
                    img_url = response.json()['url']

                except Exception:
                    # This is just a security in case we cannot retrieve the URL of the detection frame
                    img_url = ''

                # We now want to fill-in the dictionary that will contain the URLs of the detection frames
                if str(row['event_id']) not in dict_images_url_live_alerts.keys():
                    # This is a new event, so we need to instantiate the key / value pair
                    dict_images_url_live_alerts[str(row['event_id'])] = [img_url]

                else:
                    # We already have some URLs for this event and we simply append the latest frame to the list of URLs
                    dict_images_url_live_alerts[str(row['event_id'])].append(img_url)

                try:
                    # We use the device ID to retrieve the name of the corresponding site
                    sites_with_live_alerts.append(
                        retrieve_site_from_device_id(
                            device_id=row['device_id'],
                            site_devices_data=site_devices_data
                        )
                    )
                except Exception:
                    pass

            # Merging yaw (azimuth) field from devices_data
            all_devices = pd.DataFrame(devices_data)

            # We restrict the DataFrame to useful information
            devices_yaw = all_devices[['id', 'yaw']].copy()

            # We merge it with the live_alerts DataFrame
            live_alerts = pd.merge(
                live_alerts, devices_yaw,
                how='left',
                left_on=['device_id'], right_on=['id']
            )

            # We drop the azimuth associated with the alert as we will focus on the yaw of the device
            live_alerts = live_alerts.drop(['azimuth'], axis=1)

            # We rename columns to avoid any ambibguity (id_y is the id of the device)
            live_alerts.rename(columns={'id_x': 'id', 'id_y': 'd_id'}, inplace=True)

            # We store the IDs of newly loaded alerts in a dedicated list
            # This will serve as the source of truth to know what frame URLs have already been fetched or not
            new_loaded_frames = list(live_alerts['id'].unique())

            # We convert the live_alerts DataFrame into a JSON that can be stored in a dcc.Store component
            live_alerts = live_alerts.to_json(orient='records')

            # Reminder: in this case, this is the first time that we load alert data

            # So we update all outputs:
            # - the storage component that contains alert data in JSON format;
            # - the storage component that contains the dictionary with detection frame URLs;
            # - the storage component that serves as source of truth for the list of already loaded alerts;
            # - the HTML div that stores the list of sites where an alert is live

            return [
                live_alerts,
                dict_images_url_live_alerts,
                {'loaded_frames': new_loaded_frames},
                5 * 1000,
                sites_with_live_alerts
            ]

        else:
            # In this case, we have already loaded some alert data

            # We create a DataFrame with the data for already loaded alerts
            ongoing_live_alerts = pd.read_json(ongoing_live_alerts)

            if ongoing_live_alerts.empty:
                loaded_alert_ids = np.array([])

            else:
                loaded_alert_ids = ongoing_live_alerts['id'].unique()

            # Are all live alerts already stored on the platform?
            condition = np.array_equal(
                live_alerts['id'].unique(),
                loaded_alert_ids
            )

            # If this condition is verified,
            if condition:
                # Then there is no new alert to display and we do not update any of the components
                raise PreventUpdate

            # If the condition is not verified,
            else:
                # Then, there are new alerts to display on the platform

                # To identify them, we use the list of already loaded alert IDs, stored in a dedicated dcc.Store
                new_alerts = live_alerts[~live_alerts['id'].isin(already_loaded_frames['loaded_frames'])].copy()

                # We want to update this list since new alerts have been fetched from the database
                new_loaded_frames = list(live_alerts['id'].unique())

                # Besides, we want to update the dictionary that contains alert frame URLs
                # We start from a copy of the existing one (which we got from the dedicated dcc.Store component)
                dict_images_url_live_alerts = ongoing_frame_urls.copy()

                # This void list will store the names of the sites for which a live alert is being displayed,
                # Enabling us later on to hide the corresponding site marker and only display the alert one
                sites_with_live_alerts = []

                # We iterate over new live alerts
                for _, row in new_alerts.iterrows():
                    try:
                        # For each new live alert, we fetch the URL of the associated frame
                        response = api_client.get_media_url(row["media_id"])
                        if response.status_code == 401:
                            api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
                            response = api_client.get_media_url(row["media_id"])
                        img_url = response.json()['url']

                    except Exception:
                        # This is just a security in case we cannot retrieve the URL of the detection frame
                        img_url = ''

                    # We update the detection frame URL dictionary with the same method as above
                    if str(row['event_id']) not in dict_images_url_live_alerts.keys():
                        dict_images_url_live_alerts[str(row['event_id'])] = [img_url]

                    else:
                        dict_images_url_live_alerts[str(row['event_id'])].append(img_url)

                    try:
                        # We use the device ID to retrieve the name of the corresponding site
                        sites_with_live_alerts.append(
                            retrieve_site_from_device_id(
                                device_id=row['device_id'],
                                site_devices_data=site_devices_data
                            )
                        )
                    except Exception:
                        pass

                # Is there any new event among these new alerts?
                if ongoing_live_alerts.empty:
                    condition = True
                else:
                    condition = (~new_alerts['event_id'].isin(ongoing_live_alerts['event_id'].unique())).sum()

                # If this condition is verified, this means that there is a new "alert" (in fact an event) to display
                # on the platform and we therefore need to update all components (the live_alert_header_btn, the user
                # selection area, etc)
                if condition:

                    # Merging yaw (azimuth) field from devices_data
                    all_devices = pd.DataFrame(devices_data)

                    # We follow the same process as above to replace the azimuth of the alert with the yaw of the device
                    devices_yaw = all_devices[['id', 'yaw']].copy()

                    live_alerts = pd.merge(
                        live_alerts, devices_yaw,
                        how='left',
                        left_on=['device_id'], right_on=['id']
                    )

                    live_alerts = live_alerts.drop(['azimuth'], axis=1)

                    live_alerts.rename(columns={'id_x': 'id', 'id_y': 'd_id'}, inplace=True)

                    live_alerts = live_alerts.to_json(orient='records')

                    # We update all outputs
                    return [
                        live_alerts,
                        dict_images_url_live_alerts,
                        {'loaded_frames': new_loaded_frames},
                        5 * 1000,
                        sites_with_live_alerts
                    ]

                # If the condition is not verified, we have no new "alert" / event to display on the platform but only
                # new detection frames for an existing alert; this means that we do not have to update all components
                else:

                    # We would like to only update the list of alert frames being displayed and not all the components
                    # To keep track of the frame URLs that have been loaded, we also update the list of loaded alert IDs
                    return [
                        dash.no_update,
                        dict_images_url_live_alerts,
                        {'loaded_frames': new_loaded_frames},
                        5 * 1000,
                        sites_with_live_alerts
                    ]


@app.callback(
    Output('sites_markers', 'children'),
    Input('sites_with_live_alerts', 'children')
)
def hide_or_show_site_markers(sites_with_live_alerts):
    """
    In reaction to changes in the list of site names associated with an alert being displayed, this callback creates
    site markers. The goal is to hide the markers of sites associated with an alert being displayed, so that only the
    alert marker can be seen on the map.
    """
    return build_sites_markers(sites_with_live_alerts=sites_with_live_alerts)


# ----------------------------------------------------------------------------------------------------------------------
# Login-related callbacks

@app.callback(
    [Output('login_modal', 'is_open'),
     Output('login_storage', 'data'),
     Output('form_feedback_area', 'children'),
     Output('login_zoom_and_center', 'data'),
     Output('hp_map', 'style')],
    Input('send_form_button', 'n_clicks'),
    [State('username_input', 'value'),
     State('password_input', 'value'),
     State('login_storage', 'data'),
     State('map', 'center'),
     State('map', 'zoom')]
)
def manage_login_modal(n_clicks, username, password, login_storage, current_center, current_zoom):
    """
    --- Managing the login modal ---

    This callback is triggered by clicks on the connection button in the login modal and also takes as input the user-
    name, as well as the password, entered by the user via the login form.

    It updates the following output:

    - the "is_open" attribute of the login modal, a boolean which indicates whether the modal is open or not;

    - the "children" attribute of the HTML Div that stores feedback associated with user's input in the login form;

    - the "data" attribute of the dcc.Store component which saves site devices data, fetched from the API once the user
    successfully logs in;

    - the "center" and "zoom" attributes of the map object, so that the user directly ends up on the map zoomed on his /
    her department after logging in (this relies on the center_lat, center_lon and zoom fields in the login_correspon-
    dences.csv file).

    The logic is the following:

    - the callback runs a series of checks on the username / password pair;

    - as soon as one check is not satisfied, True is returned for the "is_open" attribute of the login modal, such that
    it remains open and arbitrary values are returned for the other outputs;

    - if all checks are successful, the login modal is closed (by returning False for the "is_open" attribute of the lo-
    gin modal), site devices data is fetched from the API and the right outputs are returned
    """
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    # The modal is opened and other outputs are updated with arbitrary values if no click has been registered on the
    # connection button yet (the user arrives on the page)
    if n_clicks is None:
        return True, {'login': 'no'}, None, {'center': [10, 10], 'zoom': 3}, {'display': 'none'}

    # if login_storage['login'] == 'yes':
    #     return False, {'login': 'yes'}, None, {'center': current_center, 'zoom': current_zoom}, {}

    else:

        # We instantiate the form feedback output
        form_feedback = [dcc.Markdown('---')]

        # First check verifies whether both a username and a password have been provided
        if username is None or password is None or len(username) == 0 or len(password) == 0:
            # If either the username or the password is missing, the condition is verified

            # We add the appropriate feedback
            form_feedback.append(html.P("Il semble qu'il manque votre nom d'utilisateur et/ou votre mot de passe."))

            # The login modal remains open; other outputs are updated with arbitrary values
            return True, {'login': 'no'}, form_feedback, {'center': [10, 10], 'zoom': 3}, {'display': 'none'}

        else:
            # This is the route of the API that we are going to use for the credential check
            login_route_url = cfg.API_URL + '/login/access-token'

            # We create a mini-dictionary with the credentials passsed by the user
            data = {
                'username': username,
                'password': password
            }

            # We make the HTTP request to the login route of the API
            response = requests.post(login_route_url, data=data).json()

            # Boolean that indicates whether the authentication was successful or not
            check = ('access_token' in response.keys())

            if not check:
                # This if statement is verified if credentials are invalid
                form_feedback.append(html.P("Nom d'utilisateur et/ou mot de passe erroné."))

                # We make the HTTP request to the login route of the API
                response = requests.post(login_route_url, data=data).json()

                # The login modal remains open; other outputs are updated with arbitrary values
                return True, {'login': 'no'}, form_feedback, {'center': [10, 10], 'zoom': 3}, {'display': 'none'}

            else:
                # All checks are successful and we add the appropriate feedback
                # (although the login modal does not remain open long enough for it to be readable by the user)
                form_feedback.append(html.P("Vous êtes connecté, bienvenue sur la plateforme Pyronear !"))

                # For now the group_id is not fetched, we equalize it artificially to 1
                group_id = '1'

                # We load the group correspondences stored in a dedicated JSON file in the data folder
                path = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(path, 'data', 'group_correspondences.json')

                with open(path, 'r') as file:
                    group_correspondences = json.load(file)

                # We fetch the latitude and longitude of the point around which we want to center the map
                # To do so, we use the group_correspondences dictionary defined in "APP INSTANTIATION & OVERALL LAYOUT"
                lat = group_correspondences[group_id]['center_lat']
                lon = group_correspondences[group_id]['center_lon']

                # We fetch the zoom level for the map display
                zoom = group_correspondences[group_id]['zoom']

                # The login modal is closed and the appropriate outputs are returned
                return False, {'login': 'yes'}, form_feedback, {'center': [lat, lon], 'zoom': zoom}, {}


@app.callback(
    Output('login_background', 'children'),
    Output('main_navbar', 'style'),
    Input('login_modal', 'is_open')
)
def clean_login_background(is_modal_opened):
    """
    --- Erasing the login backrgound image when credentials are validated ---

    This callback is triggered by the login modal being closed, ie. indirectly by the user entering a valid username /
    password pair and removes the login background image from the homepage layout.
    """
    if is_modal_opened:
        raise PreventUpdate

    else:
        return '', {}


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the alert workflow


# @app.callback(
#     Output('fire_markers_alerts', 'children'),
#     [Input('geojson_departments', 'click_feature'),
#      Input('historic_fires_radio_button', 'value')]
# )
# def click_department_alerts(feature, radio_button_value):
#     """
#     -- Displaying past fires on the alerts map --

#     This callback detects what department the user is clicking on.
#     It returns the position of past fires in this department as markers on the map.

#     It relies on the get_old_fire_positions function, imported from utils.

#     It also takes as input the value of the radio button dedicated to past fires:

#     - if the user has selected "Non", the container of historic fire markers is left empty;
#     - if the user has selected "Yes", we fill it in with the relevant information.
#     """
#     if feature is not None:
#         if radio_button_value == 1:
#             return build_historic_markers(dpt_code=feature['properties']['code'])
#         else:
#             return None


@app.callback(
    [Output('user_selection_column', 'md'),
     Output('map_column', 'md'),
     Output("live_alert_header_btn", "style"),
     Output('new_alerts_selection_list', 'style')],
    Input("alert_button_alerts", "n_clicks"),
    [State('map_style_button', 'children')]
)
@cache.memoize()
def click_new_alerts_button(n_clicks, map_style_button_label):
    """
    -- Initiating the whole alert flow  --

    This callback is triggered by the number of clicks on the new alert button.

    - If the number of clicks is strictly above 0 it triggers the creation of the user_alerts_selection_area with
    the alerts list, as well as of the vision angle polygons and the alert modals. To do so, it relies on the
    build_individual_alert_components, imported from the alerts.py file.

    - If we are viewing the "risks" map, a PreventUpdate is raised and clicks on the banner will have no effect.
    """

    # Deducing the style of the map in place from the map style button label
    if 'risques' in map_style_button_label.lower():
        map_style = 'alerts'

    elif 'alertes' in map_style_button_label.lower():
        map_style = 'risks'

    if n_clicks is None:
        n_clicks = 0

    if map_style == 'alerts':
        return display_alert_selection_area(n_clicks)

    elif map_style == 'risks':
        raise PreventUpdate


@app.callback(
    [Output('alert_zoom_and_center', 'data'),
     Output('alert_overview_area', 'children'),
     Output('alert_overview_style_zoom', 'children')],
    Input({'type': 'alert_selection_btn', 'index': ALL}, 'n_clicks'),
    [State('store_live_alerts_data', 'data'),
     State('images_url_live_alerts', 'data')]
)
def zoom_on_alert(n_clicks, live_alerts, frame_urls):
    """
    --- Zooming on the alert marker and displaying the alert overview ---

    This callback is triggered by the user's click on any alert selection button and does two things:

    - it updates the center and zoom components of the map to show where the alert has been raised in details;

    - it makes an overview of the considered alert appear on the left-hand side of the map. To do so, it relies on the
    build_alert_overview function, defined in the alerts.py file.
    """
    ctx = dash.callback_context

    if not ctx.triggered or all(elt is None for elt in n_clicks):
        raise PreventUpdate

    else:
        # From the context of the callback, we determine the event_id associated with the last alert selection button on
        # which the user has clicked
        text = ctx.triggered[0]['prop_id'].split(':')[1]
        event_id = text[:text.find(',')]
        event_id = event_id.strip('"')

        # We make an API call to check whether the event has already been acknowledged or not
        # Depending on the response, an acknowledgement button will be displayed or not in the alert overview
        url = cfg.API_URL + f"/events/{event_id}/"
        response = requests.get(url, headers=api_client.headers)
        if response.status_code == 401:
            api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
            response = requests.get(url, headers=api_client.headers)
        acknowledged = response.json()['is_acknowledged']

        # We fetch the latitude and longitude of the device that has raised the alert and we build the alert overview
        lat, lon, div = build_alert_overview(
            live_alerts=live_alerts,
            frame_urls=frame_urls,
            event_id=event_id,
            acknowledged=acknowledged
        )

        return {'center': [lat, lon], 'zoom': 14}, div, ''


@app.callback(
    [Output('map', 'center'),
     Output('map', 'zoom')],
    [Input('login_zoom_and_center', 'data'),
     Input('alert_zoom_and_center', 'data')],
    State('login_modal', 'is_open')
)
def change_map_zoom_and_center(login_zoom_and_center, alert_zoom_and_center, login_modal_is_open):
    """
    --- Main callback for updating the zoom and center attributes of the map ---

    This callback determines the center and zoom attributes of the map based on two different inputs, that are the
    login_zoom_and_center and alert_zoom_and_center placeholders. The latter correspond to the recentering of the map
    that takes place respectively after the user logs in and when the user clicks on one of the alert selection buttons.
    """

    ctx = dash.callback_context

    # If none of the input has triggered the callback, we raise a PreventUpdate
    if not ctx.triggered:
        raise PreventUpdate

    else:
        # We determine what input has triggered the callback
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # If it is the login that has triggered the change in the center and zoom attributes of the map
        if input_id == 'login_zoom_and_center':

            if login_zoom_and_center is None:
                raise PreventUpdate

            return login_zoom_and_center['center'], login_zoom_and_center['zoom']

        # If it is a click on an alert selection button that has triggered the change
        elif input_id == 'alert_zoom_and_center':

            if alert_zoom_and_center is None:
                raise PreventUpdate

            return alert_zoom_and_center['center'], alert_zoom_and_center['zoom']

        else:
            print('Weird result to be investigated with the change_map_zoom_and_center callback.')
            raise PreventUpdate


@app.callback(
    Output('alert_overview_style_closing_buttons', 'children'),
    Input({'type': 'close_alert_overview_button', 'index': ALL}, 'n_clicks')
)
def close_alert_overview_intermediary(n_clicks):
    """
    --- Closing the alert overview from the dedicated button ---

    For each alert, the overview contains a button allowing to close the overview.

    This callback is triggered by a click on any of these alert-specific buttons and closes the alert overview.

    Because the "style" attribute of the alert overview can be modified by three different inputs (the click on any of
    the alert selection buttons, a click on any of the overview closing buttons and a click on any of the alert erasing
    buttons), we cannot directly have it as an Output for this callback. Instead, we modify an HTML placeholder created
    on the home page (see homepage.py).
    """
    ctx = dash.callback_context

    if not ctx.triggered or all(elt is None for elt in n_clicks):
        raise PreventUpdate

    else:
        return 'hidden'


@app.callback(
    Output('alert_overview_style_acknowledgement', 'children'),
    Input({'type': 'acknowledgement_confirmation_button', 'index': ALL}, 'n_clicks')
)
def close_alert_overview_following_acknowledgement(n_clicks):
    """
    --- Closing the alert overview / Alert acknowledgement ---

    In reaction to the acknowledgement of any alert / event by the user, this callback closes the alert overview. To do
    so, it first updates the "children" attribute of a placeholder HTML div, which will then trigger a multi-input call-
    back centralising all the interactions that can open or close the alert overview.
    """
    ctx = dash.callback_context

    if not ctx.triggered or all(elt is None for elt in n_clicks):
        raise PreventUpdate

    else:
        return 'hidden'


@app.callback(
    Output('alert_overview_area', 'style'),
    [Input('alert_overview_style_zoom', 'children'),
     Input('alert_overview_style_closing_buttons', 'children'),
     Input('alert_overview_style_acknowledgement', 'children')]
)
def close_alert_overview_main(
    alert_overview_style_zoom,
    alert_overview_style_closing_buttons,
    alert_overview_style_acknowledgement
):
    """
    --- Closing the alert overview / Main callback ---

    This callback centralises the three inputs that can modify the "style" attribute of the alert overview area:

    - a click on any of the alert selection buttons;
    - a click on any of the overview closing buttons;
    - a click on any of the alert erasing buttons.

    These interactions are relayed to HTML placeholders instantiated in homepage.py and a change in any of these objects
    triggers this callback that determines whether the alert overview must be displayed or not.
    """
    ctx = dash.callback_context

    # If none of the input has triggered the callback, we raise a PreventUpdate
    if not ctx.triggered:
        raise PreventUpdate

    else:
        # We determine what input has triggered the callback
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # If it is a click on any of the alert selection buttons that has triggered the callback
        if input_id == 'alert_overview_style_zoom':
            # Then we return None, ie. we display the alert overview
            return None

        # If it is a click on any of the overview closing buttons that has triggered the callback
        elif input_id == 'alert_overview_style_closing_buttons':
            # Then we hide the alert overview
            return {'display': 'none'}

        # If it is a click on any of the alert erasing buttons that has triggered the callback
        elif input_id == 'alert_overview_style_acknowledgement':
            # Then we hide the alert overview
            return {'display': 'none'}


@app.callback(
    Output(
        {
            'type': 'manage_confirmation_modal_acknowlegdment_button',
            'index': MATCH
        },
        'children'
    ),
    Input({'type': 'acknowledge_alert_button', 'index': MATCH}, 'n_clicks')
)
def acknowledge_alert(n_clicks):
    """
    --- Open acknowledgement confirmation modal ---

    This callback, triggered by the user's click on any alert acknowledgement button, opens the corresponding alert
    acknowledgement confirmation modal. It does so indirectly, by updating the "children" attribute of the dedicated
    HTML Div placeholder.
    """
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    else:
        return 'open'


@app.callback(
    Output(
        {
            'type': 'acknowledgement_confirmation_modal',
            'index': MATCH
        },
        'is_open'
    ),
    [
        Input(
            {
                'type': 'manage_confirmation_modal_acknowlegdment_button',
                'index': MATCH
            },
            'children'
        ),
        Input(
            {
                'type': 'manage_confirmation_modal_close_button',
                'index': MATCH
            },
            'children'
        ),
        Input(
            {
                'type': 'manage_confirmation_modal_confirmation_button',
                'index': MATCH
            },
            'children'
        )
    ]
)
def manage_confirmation_modal(acknowlegdment_button_input, close_button_input, confirmation_button_input):
    """
    --- Managing the acknowledgement confirmation modal / Main callback ---

    This callback centralises all the interactions that can open or close the alert acknowledgement confirmation modal.
    It takes the "children" attribute of the dedicated HTML Div placeholders as inputs and eventually determines the
    "is_open" attribute of the corresponding acknowledgement confirmation modal.
    """
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    text = ctx.triggered[0]['prop_id'].split(':')[2]
    input_type = text[:text.find('}')]
    input_type = input_type.strip('"')

    if input_type == 'manage_confirmation_modal_acknowlegdment_button':
        return True

    else:
        return False


@app.callback(
    Output(
        {
            'type': 'manage_confirmation_modal_close_button',
            'index': MATCH
        },
        'children'
    ),
    Input({'type': 'close_confirmation_modal_button', 'index': MATCH}, 'n_clicks')
)
def close_confirmation_modal(n_clicks):
    """
    --- Closing the acknowledgement confirmation modal ---

    Triggered by the user's click on the button that allows to close the alert acknowledgement confirmation modal (the
    one that displays "Non" in the acknowledgement confirmation modal), this callback closes the modal. It does so indi-
    rectly by updating the "children" attribute of the dedicated HTML Div placeholder.
    """
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    else:
        return 'close'


@app.callback(
    [
        Output(
            {
                'type': 'manage_confirmation_modal_confirmation_button',
                'index': MATCH
            },
            'children'
        ),
        Output({'type': 'acknowledge_alert_space', 'index': MATCH}, 'children')
    ],
    Input({'type': 'acknowledgement_confirmation_button', 'index': MATCH}, 'n_clicks')
)
def confirm_alert_acknowledgement(n_clicks):
    """
    --- Confirming alert acknowledgement ---

    Once the user has clicked on an alert acknowledgement button, the corresponding confirmation modal is opened.

    This callback is triggered by the user's click on the confirmation button (the one that displays "Oui").

    It then does two things:

    - it indirectly closes the acknowledgement confirmation modal through an HTML Div placeholder;

    - it updates the content of the alert acknowledgement space to erase the acknowledgement button and replace it with
    a text saying that the alert / event has already been acknowledged.
    """
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    else:
        ctx = dash.callback_context

        # We retrieve the ID of the event
        text = ctx.triggered[0]['prop_id'].split(':')[1]
        event_id = text[:text.find(',')]
        event_id = event_id.strip('"')

        # The event is actually acknowledged thanks to the acknowledge_event method of the API client
        response = api_client.acknowledge_event(event_id=int(event_id))

        if response.status_code == 401:
            api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
            api_client.acknowledge_event(event_id=int(event_id))

        return ['close', html.P('Alerte acquittée.')]


@app.callback(
    Output({'type': 'alert_modal', 'index': MATCH}, 'is_open'),
    Input({'type': 'alert_frame_small', 'index': MATCH}, 'n_clicks')
)
def display_alert_modal(n_clicks):
    """
    --- Displaying an alert modal ---

    When the user has selected an alert in the column on the left-hand side of the page, he or she can click on the
    image that appears to get more details about the alert. This callback is triggered by the user's click on any
    alert_frame_small component and opens the corresponding alert modal.
    """
    if n_clicks is None or n_clicks == 0:
        raise PreventUpdate

    else:
        return True


@app.callback(
    Output({'type': 'alert_frame', 'index': MATCH}, 'src'),
    Input({'type': 'alert_slider', 'index': MATCH}, 'value'),
    State({'type': 'individual_alert_frame_storage', 'index': MATCH}, 'children')
)
def select_alert_frame_to_display(slider_value, urls):
    """
    --- Choosing the alert frame to be displayed in an alert modal ---

    When the user has opened an alert modal, he or she can choose the alert frame to view thanks to the slider. This
    callback is triggered by a change in value of the slider and return the URL address of the frame to be displayed.
    Like there is one alert modal per event, there is one alert slider per event, which allows to use MATCH here.
    """

    if slider_value is None:
        raise PreventUpdate

    return urls[slider_value - 1]   # Slider value starts at 1 and not 0


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "Risk Score" page

@app.callback(
    Output('map', 'children'),
    Input('opacity_slider_risks', 'value')
)
def change_color_opacity(opacity_level):
    """
    -- Managing color opacity in the choropleth map --

    This callback takes as input the opacity level chosen by the user on the slider.
    It then reinstantiates the colorbar and geojson objects accordingly.
    These new objects are finally returned into the risks map's children attribute.
    """
    colorbar, geojson = build_risks_geojson_and_colorbar(opacity_level=opacity_level)

    return [dl.TileLayer(id='tile_layer'),
            geojson,
            colorbar,
            build_filters_object(map_type='risks'),
            build_legend_box(map_type='risks'),
            html.Div(id='fire_markers_risks'),  # Will contain the past fire markers of the risks map
            html.Div(id='live_alerts_marker')
            ]


@app.callback(
    Output('alert_btn_switch_view', 'children'),
    Input('alert_button_risks', 'n_clicks'),
    [State('map_style_button', 'children'),
     State('current_map_style', 'children')]
)
@cache.memoize()
def change_map_style_alert_button(n_clicks, map_style_button_label, current_map_style):
    """
    -- Moving between alerts and risks views (1/3) --

    This callback detects clicks on the alert banner associated with the risks view of the map and updates the
    "alert_btn_switch_view" object (an HTML placeholder built by via the Homepage function which is defined in
    homepage.py). This update will itself trigger the "change_map_style" callback defined below.

    It also takes as a "State" input the map style currently in use, so as to prevent this callback for having any
    effect when the map being viewed is the alerts one. This avoids certain non-desirable behaviors.
    """
    if n_clicks is None:
        raise PreventUpdate

    if current_map_style == 'risks':
        return 'switch map style'

    elif current_map_style == 'alerts':
        raise PreventUpdate


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the homepage

@app.callback(
    Output('map_style_btn_switch_view', 'children'),
    Input('map_style_button', 'n_clicks')
)
def change_map_style_usual_button(n_clicks):
    """
    -- Moving between alerts and risks views (2/3) --

    This callback detects clicks on the button used to change the style of the map, ie.
    to switch from the "Alerts and Infrastructure" to the "Risk Scores" view and vice-versa.

    If a click is detected, it updates the "map_style_btn_switch_view" object (an HTML placeholder built by via the
    Homepage function which is defined in homepage.py) and this update will itself trigger the "change_map_style"
    callback defined below.

    NB: because two buttons (the one considered here and the alert banner in risks mode) can lead to a change of the map
    view, the number of clicks on the map style button is not a reliable indicator of the map being viewed by the user.
    """
    if n_clicks is None:
        raise PreventUpdate

    return n_clicks


@app.callback(
    [Output('map_style_button', 'children'),
     Output('hp_map', 'children'),
     Output('hp_slider', 'children'),
     Output('current_map_style', 'children')],
    [Input('map_style_btn_switch_view', 'children'),
     Input('alert_btn_switch_view', 'children')],
    [State('map_style_button', 'children'),
     State('current_map_style', 'children')]
)
def change_map_style_main(map_style_button_input, alert_button_input, map_style_button_label, current_map_style):
    """
    -- Moving between alerts and risks views --

    This callback is the one that actually updates the map view based on user's choice.

    It can be triggered:
    - either by a click on the main map style button in the user selection area on the left of the page;
    - or by a click on the alert banner under risks mode.

    This determines the two Inputs of this callback (see the two callbacks above).

    This callback also takes as a State argument the map style currently being viewed.

    It relies on the choose_map_style function, imported from homepage.

    It returns:

    - the appropriate for the button on which the user has just clicked;
    - the right map object;
    - the slider object if relevant.
    """

    # Deducing from the map style button label, the argument that we should pass to the choose_map_style function
    if current_map_style == 'alerts':
        arg = 1

    elif current_map_style == 'risks':
        arg = 0

    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    else:
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'map_style_btn_switch_view':
        return choose_map_style(arg)

    elif input_id == 'alert_btn_switch_view':
        return choose_map_style(0)


@app.callback(
    [Output('live_alert_header_btn', 'children'),
     Output('live_alerts_marker', 'children'),
     Output("main_navbar", "color"),
     Output("user-div", "children"),
     Output("new_alerts_selection_list", "children"),
     Output('vision_polygons', 'children'),
     Output('alert_modals', 'children')],
    Input("store_live_alerts_data", "data"),
    [State('map_style_button', 'children'),
     State('images_url_live_alerts', 'data'),
     State('site_devices_data_storage', 'data')]
)
def update_live_alerts_components(
    live_alerts, map_style_button_label, images_url_live_alerts, site_devices_data
):
    """
    -- Updating style components with corresponding alerts data --

    This callback takes as input "live_alerts", a json object containing live_alerts data. It is triggered each time a
    new alert is fetched and then stored in store_live_alerts_data.

    It also takes as states the images_url_live_alerts and the label of the button that allows users to change the
    style of the map , in order to deduce the style of the map that the user is currently looking at.

    Each time it is triggered, the callback uses the data of all ongoing alerts which are stored in
    "store_live_alerts_data" and returns several elements:

    - it stores the URL address of the frame associated with the last alert;

    - it creates the elements (alert notifications button, alerts lists within alert selection area);

    - it changes the navabar color and title into alert mode;

    - it instantiates the alert markers on the map;

    - and it creates an individual storage component, specific to each alert/event being displayed, that contains the
    URL addresses of the corresponding frames.

    To build these elements, it relies on the build_alerts_elements imported from alerts.
    """

    # Deducing the style of the map in place from the map style button label
    if "risques" in map_style_button_label.lower():
        map_style = "alerts"

    elif "alertes" in map_style_button_label.lower():
        map_style = "risks"

    if map_style == 'alerts':
        output = build_alerts_elements(images_url_live_alerts, live_alerts, map_style)

        output += build_individual_alert_components(
            live_alerts, images_url_live_alerts, site_devices_data
        )

        return output

    elif map_style == 'risks':
        raise PreventUpdate


@app.callback(
    Output('individual_alert_frame_placeholder', 'children'),
    Input('images_url_live_alerts', 'data')
)
def update_individual_frame_components(images_url_live_alerts):
    individual_alert_frame_placeholder_children = []

    for event_id, frame_url_list in images_url_live_alerts.items():

        images_to_display = frame_url_list[-15:]

        individual_alert_frame_placeholder_children.append(
            html.Div(
                id={
                    'type': 'individual_alert_frame_storage',
                    'index': str(event_id)
                },
                children=images_to_display,
                style={'display': 'none'}
            )
        )

    return individual_alert_frame_placeholder_children


@app.callback(
    [Output({'type': 'alert_slider', 'index': MATCH}, 'max'),
     Output({'type': 'alert_slider', 'index': MATCH}, 'marks')],
    Input({'type': 'individual_alert_frame_storage', 'index': MATCH}, 'children')
)
def modify_alert_slider_length(individual_alert_frame_storage):
    number_of_images = len(individual_alert_frame_storage)

    return number_of_images, {i + 1: str(i + 1) for i in range(number_of_images)}


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to alert_screen page

@app.callback(
    [
        Output("core_layout_alert_screen", "children"),
        Output("core_layout_alert_screen", "style"),
        Output('images_to_display_on_big_screen', 'data')
    ],
    Input("interval-component-alert-screen", "n_intervals"),
    [State('devices_data_storage', 'data'),
     State('site_devices_data_storage', 'data'),
     State('night_time', 'data')],
)
def update_alert_screen(n_intervals, devices_data, site_devices_data, night_time_data):

    response = api_client.get_ongoing_alerts()
    # Check token expiration
    if response.status_code == 401:
        api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
        response = api_client.get_ongoing_alerts()
    response = response.json()
    # Only for demo purposes, this should be deleted for dev and later in production
    # response = {}

    # If there is no alert, we build the no alert screen
    if len(response) == 0:
        style_to_display = build_no_alert_detected_screen()

        images_to_display = {'frame_URLs': 'no_images'}

        return (
            [{}],
            style_to_display,
            images_to_display
        )

    else:
        # We store all alerts in a DataFrame and we want to select "live alerts",
        # Ie. alerts that correspond to a not-yet-acknowledged event
        all_alerts = pd.DataFrame(response)

        # We now want to build the boolean indexing mask that indicates whether or not the event is unacknowledged
        # We start by making an API call to fetch all events
        url = cfg.API_URL + '/events/'
        response = requests.get(url, headers=api_client.headers)
        if response.status_code == 401:
            api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
            response = requests.get(url, headers=api_client.headers)
        all_events = response.json()

        # Then, we construct a dictionary whose keys are the event IDs (as integers) and values are the corresponding
        # "is_acknowledged" field in the events table (boolean)
        is_event_acknowledged = {}
        for event in all_events:
            is_event_acknowledged[event['id']] = event['is_acknowledged']

        # We map this dictionary upon the column and revert the booleans with ~ as we want unacknowledged events
        mask_acknowledgement = ~all_alerts['event_id'].map(is_event_acknowledged)

        # And we deduce the subset of alerts that we can deem to be "live"
        live_alerts = all_alerts[mask_acknowledgement].copy()

        # We then fetch sunrise and sunset times and add a safety margin of 30 min (converting from UTC) to cover night
        sunrise = night_time_data['results']['sunrise'][:-6]
        sunrise = datetime.fromisoformat(str(sunrise)) + timedelta(hours=2.5)
        sunrise = sunrise.time()

        sunset = night_time_data['results']['sunset'][:-6]
        sunset = datetime.fromisoformat(str(sunset)) + timedelta(hours=1.5)
        sunset = sunset.time()

        # Are there some live alerts during night time ? If yes let's filter them out
        mask = live_alerts['created_at'].map(lambda x: is_hour_between(sunrise, sunset, x))
        live_alerts = live_alerts[mask].copy()

        # Is there any live alert to display?
        if live_alerts.empty:
            style_to_display = build_no_alert_detected_screen()

            images_to_display = {'frame_URLs': 'no_images'}

            return (
                [{}],
                style_to_display,
                images_to_display
            )

        else:
            # Merging yaw (azimuth) field from devices_data
            all_devices = pd.DataFrame(devices_data)

            # We restrict the DataFrame to useful information
            devices_yaw = all_devices[['id', 'yaw']].copy()

            # We merge it with the live_alerts DataFrame
            live_alerts = pd.merge(
                live_alerts, devices_yaw,
                how='left',
                left_on=['device_id'], right_on=['id']
            )

            # We drop the azimuth associated with the alert as we will focus on the yaw of the device
            live_alerts = live_alerts.drop(['azimuth'], axis=1)

            # We rename columns to avoid any ambibguity (id_y is the id of the device)
            live_alerts.rename(columns={'id_x': 'id', 'id_y': 'd_id'}, inplace=True)

            last_alert = live_alerts.loc[live_alerts["id"].idxmax()]
            last_event_id = str(last_alert["event_id"])

            focus_on_event = live_alerts[live_alerts['event_id'] == int(last_event_id)].copy()
            focus_on_event = focus_on_event.sort_values(by='id').tail(3).copy()

            images_to_display = {last_event_id: []}

            for _, row in focus_on_event.iterrows():
                img_url = ""

                try:
                    response = api_client.get_media_url(row["media_id"])
                    if response.status_code == 401:
                        api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
                        response = api_client.get_media_url(row["media_id"])
                    img_url = response.json()['url']

                except Exception:
                    pass

                images_to_display[last_event_id].append(img_url)

            layout_div, style_to_display = build_alert_detected_screen(
                images_to_display[last_event_id], last_alert, site_devices_data
            )

            return layout_div, style_to_display, images_to_display


@app.callback(
    [Output('alert_frame_update_new_event', 'children'),
     Output('last_displayed_event_id', 'data')],
    Input('images_to_display_on_big_screen', 'data'),
    State('last_displayed_event_id', 'data')
)
def update_alert_frame_due_to_new_event(images_to_display, last_event_id):

    if 'frame_URLs' in images_to_display.keys() and images_to_display['frame_URLs'] == 'no_images':
        raise PreventUpdate

    elif list(images_to_display.keys())[0] == last_event_id:
        return list(images_to_display.values())[0][-1], dash.no_update

    else:
        return list(images_to_display.values())[0][-1], list(images_to_display.keys())[0]


# @app.callback(
#     Output("alert_frame_update_interval", "children"),
#     Input("interval-component-img-refresh", "n_intervals"),
#     State("images_to_display_on_big_screen", "data")
# )
# def update_alert_frame_from_interval(n_intervals, images_to_display):
#     """
#     -- Create a pseudo GIF --

#     Created from the x frames we received each time there is an alert related to the same event.
#     The urls of these images are stored in a dictionary "images_url_live_alerts".
#     """
#     if n_intervals is None:
#         raise PreventUpdate

#     list_url_images = list(images_to_display.values())[0]

#     return list_url_images[n_intervals % len(list_url_images)]


@app.callback(
    [Output('alert_frame', 'src'),
     Output("interval-component-img-refresh", "n_intervals")],
    [Input('alert_frame_update_new_event', 'children'),
     Input("alert_frame_update_interval", "children")]
)
def update_alert_frame_main(alert_frame_update_new_event, alert_frame_update_interval):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    if alert_frame_update_new_event is None and alert_frame_update_interval is None:
        raise PreventUpdate

    # We determine what input has triggered the callback
    input_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if input_id == 'alert_frame_update_new_event':

        return alert_frame_update_new_event, 0

    elif input_id == 'alert_frame_update_interval':

        return alert_frame_update_interval, dash.no_updates


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "dashboard_screen" page

@app.callback(
    Output('dashboard_table', 'children'),
    Input('interval-component-dashboard-screen', 'n_intervals'), )
def update_dashboard_table(n_intervals):
    """
    This builds and refreshes the dashboard table to monitor devices status every minute
    Had to fetch devices data again for freshness purposes
    """
    response = requests.get('https://api.pyronear.org/devices/', headers=api_client.headers)
    # Check token expiration
    if response.status_code == 401:
        api_client.refresh_token(cfg.API_LOGIN, cfg.API_PWD)
        response = requests.get('https://api.pyronear.org/devices/', headers=api_client.headers)

    # We filters devices_data to only display devices belonging to the sdis and then make the comparison between
    # last_ping and datetime.now()
    all_devices = pd.DataFrame(response.json())

    sdis_devices = all_devices[all_devices['id'].isin(range(2, 18))].sort_values(by='login')[
        ['yaw', 'lat', 'lon', 'login', 'last_ping']].copy()

    sdis_devices['last_ping_hours_dif'] = sdis_devices['last_ping'].apply(
        lambda x: (pd.to_datetime(x) - pd.to_datetime(datetime.utcnow().isoformat())).total_seconds() // 3600)

    sdis_devices['last_ping'] = pd.to_datetime(sdis_devices['last_ping']) + timedelta(hours=2)

    return build_dashboard_table(sdis_devices_data=sdis_devices)


# ----------------------------------------------------------------------------------------------------------------------
# RUNNING THE WEB-APP SERVER

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Pyronear web-app',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host of the server')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the server on')
    args = parser.parse_args()

    app.run_server(host=args.host, port=args.port, debug=cfg.DEBUG, dev_tools_hot_reload=cfg.DEBUG)
