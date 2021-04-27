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

# Main Dash imports, used to instantiate the web-app and create callbacks (ie. to generate interactivity)
import os
import dash
from dash.dependencies import Input, Output, State, MATCH
from dash.exceptions import PreventUpdate

# Flask caching import
from flask_caching import Cache

# Various modules provided by Dash and Dash Leaflet to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl

from dash_extensions.websockets import SocketPool, run_server
from dash_extensions import WebSocket

# Pandas to read the login correspondences file
import pandas as pd

# Import used to make the API call in the login callback
import requests

# Various utils
import json

# --- Imports from other Python files

import config as cfg  # Cf. config.py file

# From alert_screen.py, we import the main layout instantiation function and some others needed for interactivity
from alert_screen import AlertScreen, build_no_alert_detected_screen, build_alert_detected_screen

# From homepage.py, we import the main layout instantiation function
from homepage import Homepage

# From other Python files, we import some functions needed for interactivity
from homepage import choose_map_style, display_alerts_frames
from risks import build_risks_geojson_and_colorbar
from alerts import build_alerts_elements, get_site_devices_data,\
    build_user_alerts_selection_area
from utils import choose_layer_style, build_filters_object,\
    build_historic_markers, build_legend_box

# Importing the pre-instantiated Pyro-API client
from services import api_client


# ----------------------------------------------------------------------------------------------------------------------
# APP INSTANTIATION & OVERALL LAYOUT

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])
socket_pool = SocketPool(app)

# We define a few attributes of the app object
app.title = 'Pyronear - Monitoring platform'
app.config.suppress_callback_exceptions = True
server = app.server  # Gunicorn will be looking for the server attribute of this module

# We create a rough layout, filled with the content of the homepage/alert page
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content", style={"height": "100%"}),

        # Storage components which contains data relative to alerts
        dcc.Store(id="store_live_alerts_data", storage_type="session"),
        dcc.Store(id="last_displayed_event_id", storage_type="session"),
        dcc.Store(id="images_url_live_alerts", storage_type="session", data={}),
        # Storage component which contains data relative to site devices
        dcc.Store(id="site_devices_data_storage", storage_type="session", data=get_site_devices_data(client=api_client))
    ]
)


# Cache configuration
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': '.cache',
    'CACHE_DEFAULT_TIMEOUT': 60
})


# End point ping by the API for each alert being recorded. Then broadcasting message to ALL sessions
@app.server.route("/alert/<message>")
def broadcast_message(message):
    socket_pool.broadcast(message)
    return f"Message {message} broadcast."

# ----------------------------------------------------------------------------------------------------------------------
# CALLBACKS

# ----------------------------------------------------------------------------------------------------------------------
# General callbacks


# First API relay once an alert is sent to the platform, passing msg.data into msg hidden div
"""app.clientside_callback("function(msg){if(msg == null) {return;} else {return msg.data;}}",
                        Output("msg", "children"), [Input("ws", "message")])"""

# First API relay once an alert is sent to the platform, passing msg.data into msg hidden div
@app.callback(
    Output('msg', 'children'),
    Input('ws', 'message')
)
def trigger(message):
    return "hello"


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


@app.callback(
    Output('store_live_alerts_data', 'data'),
    Output('images_url_live_alerts', 'data'),
    Input('msg', 'children')
)
def update_live_alerts_data(alert):
    """
    The following function is used to update the store containing live_alerts data from API and
    the dictionary of images of ongoing alerts.

    It returns :

    - a json containing live_alerts data where is_acknowledged is False.
    - a dict where keys are event id and value lists of all urls related to the same event.

    These url come from the API calls, triggered by the websocket message stroed in msg hidden div.
    """

    # Fetching live alerts where is_acknowledged is False
    response = api_client.get_ongoing_alerts().json()
    all_alerts = pd.DataFrame(response)
    if all_alerts.empty:
        raise PreventUpdate
    live_alerts = all_alerts.loc[~all_alerts["is_acknowledged"]]

    # Fetching live_alerts frames urls and instantiating a dict of live_alerts urls having event_id keys
    dict_images_url_live_alerts = {}
    for _, row in live_alerts.iterrows():
        img_url = ""
        try:
            img_url = api_client.get_media_url(row["media_id"]).json()["url"]
        except Exception:
            pass
        if row['event_id'] not in dict_images_url_live_alerts.keys():
            dict_images_url_live_alerts[row['event_id']] = []
            dict_images_url_live_alerts[row['event_id']].append(img_url)
        else:
            dict_images_url_live_alerts[row['event_id']].append(img_url)

    return live_alerts.to_json(orient='records'), dict_images_url_live_alerts


@app.callback(
    [Output('login_modal', 'is_open'),
     Output('form_feedback_area', 'children'),
     Output('map', 'center'),
     Output('map', 'zoom')],
    Input('send_form_button', 'n_clicks'),
    [State('username_input', 'value'),
     State('password_input', 'value')]
)
def manage_login_modal(n_clicks, username, password):
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
    # The modal is opened and other outputs are updated with arbitray values if no click has been registered on the con-
    # nection button yet (the user arrives on the page)
    if n_clicks is None:
        return True, None, [10, 10], 3

    # We instantiate the form feedback output
    form_feedback = [dcc.Markdown('---')]

    # First check verifies whether both a username and a password have been provided
    if username is None or password is None or len(username) == 0 or len(password) == 0:
        # If either the username or the password is missing, the condition is verified

        # We add the appropriate feedback
        form_feedback.append(html.P("Il semble qu'il manque votre nom d'utilisateur et/ou votre mot de passe."))

        # The login modal remains open; other outputs are updated with arbitrary values
        return True, form_feedback, [10, 10], 3

    else:
        # This is the route of the API that we are going to use for the credential check
        login_route_url = 'http://pyronear-api.herokuapp.com/login/access-token'

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

            # We make the HTTP request to the login route of the API
            response = requests.post(login_route_url, data=data).json()

            # The login modal remains open; other outputs are updated with arbitrary values
            return True, form_feedback, [10, 10], 3

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

            # The login modal is closed; site devices data is fetched from the API and the right outputs are returned
            return False, form_feedback, [lat, lon], zoom


@app.callback(
    Output('login_background', 'children'),
    Output('main_navbar', 'style'),
    Input('login_modal', 'is_open')
)
def clean_login_background(is_modal_opened):
    """
    --- Erasing the login backrgound image when credentials are validated ---

    This callback is triggered by the login modal being closed, ie. indirectly by the user entering a valid username /
    password pair and removes the login background image from the home pag layout.
    """
    if is_modal_opened:
        raise PreventUpdate

    else:
        return '', {}


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "Alerts and Infrastructure" view


@app.callback(
    Output('fire_markers_alerts', 'children'),
    [Input('geojson_departments', 'click_feature'),
     Input('historic_fires_radio_button', 'value')]
)
def click_department_alerts(feature, radio_button_value):
    """
    -- Displaying past fires on the alerts map --

    This callback detects what department the user is clicking on.
    It returns the position of past fires in this department as markers on the map.

    It relies on the get_old_fire_positions function, imported from utils.

    It also takes as input the value of the radio button dedicated to past fires:

    - if the user has selected "Non", the container of historic fire markers is left empty;
    - if the user has selected "Yes", we fill it in with the relevant information.
    """
    if feature is not None:
        if radio_button_value == 1:
            return build_historic_markers(dpt_code=feature['properties']['code'])
        else:
            return None


@app.callback(
    Output({'type': 'acknowledge_alert_div', 'index': MATCH}, 'children'),
    Input({'type': 'acknowledge_alert_checkbox', 'index': MATCH}, 'children')
)
def acknowledge_alert(checkbox_checked):
    """
    -- Allowing user to acknowledge an alert --

    This callback takes as input the status of the checkbox that the user can see when
    clicking on an alert marker and can use to acknowledge the alert.

    For now, if the checkbox is checked, it simply eliminates the checkbox and displays
    a message according to which the alert has already been taken into account.

    Still to be done regarding this callback:

    - use the client to effectively report the acknowledgement to the DB;
    - check if an alert is acknowledged or not in the DB to display the right message.
    """

    ctx = dash.callback_context

    if not checkbox_checked:
        return [dbc.FormGroup([dbc.Checkbox(id=ctx.triggered[0]['prop_id'].split('.')[0],
                                            className="form-check-input"),
                               dbc.Label("Confirmer la prise en compte de l'alerte",
                                         className="form-check-label")],
                              check=True,
                              inline=True)]

    elif checkbox_checked:
        return [html.P("Prise en compte de l'alerte confirmée")]


@app.callback(
    [Output('user_selection_column', 'md'),
     Output('map_column', 'md'),
     Output("new_alerts_selection_list", "children"),
     Output("live_alert_header_btn", "style")],
    Input("alert_button_alerts", "n_clicks"),
    State('map_style_button', 'children'),
    State("store_live_alerts_data", "data")
)
@cache.memoize()
def click_new_alerts_button(n_clicks, map_style_button_label, live_alerts):
    """
    -- Initiating the whole alert flow  --

    This callback is triggered by the number of clicks on the new alert button.

    - If the number of clicks is strictly above 0 it triggers the creation of the user_alerts_selection_area with
    the alerts list. To do so, it relies on the build_user_alerts_selection_area and the function, imported from alerts.

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
        return build_user_alerts_selection_area(n_clicks, live_alerts)

    elif map_style == 'risks':
        raise PreventUpdate


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
     Output("user-div", "children")],
    Input("store_live_alerts_data", "data"),
    [State('map_style_button', 'children'),
     State('images_url_live_alerts', 'data')]
)
def update_live_alerts_components(
        live_alerts, map_style_button_label, images_url_live_alerts
):
    """
    -- Updating style components with corresponding alerts data --

    This callback takes as input "live_alerts", a json object containing live_alerts data. It is triggered each time a
    new alert is sent by the API then processed by the websocket and then stored in store_live_alerts_data.

    It also takes as states the images_url_live_alerts and the label of the button that allows users to change the
    style of the map , in order to deduce the style of the map that the user is currently looking at.

    Each time it is triggered, the callback uses the data of all ongoing alerts which are stored in
    "store_live_alerts_data" and returns several elements:

    - it stores the URL address of the frame associated with the last alert;
    - it creates the elements (alert notifications button, alerts lists within alert selection area);
    - it changes the navabar color and title into alert mode
    - and instantiates the alert markers on the map.

    To build these elements, it relies on the build_alerts_elements imported from alerts.
    """

    # Deducing the style of the map in place from the map style button label
    if "risques" in map_style_button_label.lower():
        map_style = "alerts"

    elif "alertes" in map_style_button_label.lower():
        map_style = "risks"

    if map_style == 'alerts':
        return build_alerts_elements(images_url_live_alerts, live_alerts, map_style)

    elif map_style == 'risks':
        raise PreventUpdate

    """
    Will be replaced by a display_alert_modal callback

@app.callback(
    [Output({'type': 'display_alert_frame_btn', 'index': MATCH}, 'children')],
    Input({'type': 'display_alert_frame_btn', 'index': MATCH}, 'n_clicks'),
    State('img_url', 'children')
)
def display_alert_frame_metadata(n_clicks_marker, images_url_live_alerts):


    This callback detects the number of clicks the user has made on the button that allows
    to display the detection data and the alert frame (in the popup of the alert marker).

    If an odd number of clicks has been made, the function returns the image of the corresponding alert
    and the associated metadata in the blank space on the left of the map.


    if (n_clicks_marker + 1) % 2 == 0:
        return display_alerts_frames(n_clicks_marker), 'Masquer les données de détection'
    else:
        return display_alerts_frames(), 'Afficher les données de détection'
"""


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to alert_screen page
@app.callback(
    [
        Output("core_layout_alert_screen", "children"),
        Output("core_layout_alert_screen", "style"),
        Output("last_displayed_event_id", "data"),
    ],
    Input("interval-component-alert-screen", "n_intervals"),
    [
        State("store_live_alerts_data", "data"),
        State("last_displayed_event_id", "data"),
    ],
)
def update_alert_screen(n_intervals, live_alerts, last_displayed_event_id):
    """
    -- Update elements related to the Alert Screen page when the interval component "alert-screen" is triggered --
    """
    if live_alerts is None:
        style_to_display = build_no_alert_detected_screen()
        return (
            [{}],
            style_to_display,
            last_displayed_event_id
        )

    else:
        # Fetching the last alert
        live_alerts = pd.read_json(live_alerts)
        last_alert = live_alerts.loc[live_alerts["id"].idxmax()]
        last_event_id = str(last_alert["event_id"])

        # Fetching the URL address of the frame associated with the last alert
        img_url = ""
        try:
            img_url = api_client.get_media_url(last_alert["media_id"]).json()["url"]
        except Exception:
            pass

        if last_event_id == last_displayed_event_id:
            # the alert is related to an event id which has already been displayed
            # need to send the img_url to the GIF
            raise PreventUpdate
        else:
            # new event, not been displayed yet
            layout_div, style_to_display = build_alert_detected_screen(
                img_url, live_alerts, last_alert
            )
            return layout_div, style_to_display, last_event_id


@app.callback(
    Output("alert_frame", "src"),
    Input("interval-component-img-refresh", "n_intervals"),
    [
        State("last_displayed_event_id", "data"),
        State("images_url_live_alerts", "data")
    ]
)
def update_images_for_doubt_removal(n_intervals, last_displayed_event_id, dict_images_url_live_alerts):
    """
    -- Create a pseudo GIF --

    Created from the x frames we received each time there is an alert related to the same event.
    The urls of these images are stored in a dictionary "images_url_live_alerts".
    """
    if n_intervals is None:
        raise PreventUpdate

    if last_displayed_event_id not in dict_images_url_live_alerts.keys():
        raise PreventUpdate

    if n_intervals is None:
        raise PreventUpdate

    list_url_images = dict_images_url_live_alerts[last_displayed_event_id]
    # Only for demo purposes: will be removed afterwards
    list_url_images = [
        "http://placeimg.com/625/225/nature",
        "http://placeimg.com/625/225/animals",
        "http://placeimg.com/625/225/nature"
    ]
    return list_url_images[n_intervals % len(list_url_images)]


# ----------------------------------------------------------------------------------------------------------------------
# RUNNING THE WEB-APP SERVER

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Pyronear web-app',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host of the server')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the server on')
    args = parser.parse_args()

    run_server(app, port=args.port)
