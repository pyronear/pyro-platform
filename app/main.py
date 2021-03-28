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

# General imports

# Main Dash imports, used to instantiate the web-app and create callbacks (ie. to generate interactivity)
import dash
import dash_bootstrap_components as dbc
# Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_leaflet as dl
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask_caching import Cache

import config as cfg  # Cf. config.py file
from alert_screen import AlertScreen, build_no_alert_detected_screen, build_alert_detected_screen
from alerts import define_map_zoom_center, build_alerts_elements, get_site_devices_data
# From homepage.py, we import the main layout instantiation function
from homepage import Homepage
# From other Python files, we import some functions needed for interactivity
from homepage import choose_map_style, display_alerts_frames
from risks import build_risks_geojson_and_colorbar
# Importing the pyro-API client
from services import api_client
from utils import choose_layer_style, build_info_box, build_info_object, \
    build_live_alerts_metadata, build_historic_markers, build_legend_box

import time
import pandas as pd

# ----------------------------------------------------------------------------------------------------------------------
# APP INSTANTIATION & OVERALL LAYOUT

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# We define a few attributes of the app object
app.title = 'Pyronear - Monitoring platform'
app.config.suppress_callback_exceptions = True
server = app.server  # Gunicorn will be looking for the server attribute of this module

# We create a rough layout, filled with the content of the homepage/alert page
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content", style={"height": "100%"}),
        # Interval component to generate call to API every 10 seconds
        dcc.Interval(
            id="interval-component-homepage",
            interval=10 * 1000
        ),
        # Hidden div to keep a record of live alerts data
        dcc.Store(id="store_live_alerts_data", storage_type="memory"),
        dcc.Store(id="last_displayed_event_id", storage_type="memory"),
        dcc.Store(id="images_url_current_alert", storage_type="session", data={}),

        # Storage component which contains data relative to site devices
        dcc.Store(id="site_devices_data_storage", storage_type="session")
    ]
)

# Cache configuration
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': '.cache',
    'CACHE_DEFAULT_TIMEOUT': 60
})

# Fetching reusable alert metadata
alert_metadata = build_live_alerts_metadata()
alert_id = alert_metadata["id"]


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
    Output("store_live_alerts_data", "data"),
    Input('interval-component-homepage', 'n_intervals')
)
def update_alert_data(interval):
    """
    The following function is used to update the div containing live alert data from API.
    """
    # Fetching live alerts where is_acknowledged is False
    response = api_client.get_ongoing_alerts().json()
    all_alerts = pd.DataFrame(response)
    live_alerts = all_alerts.loc[~all_alerts["is_acknowledged"]]

    return live_alerts.to_json()


@app.callback(
    [Output('login_modal', 'is_open'),
     Output('form_feedback_area', 'children'),
     Output('site_devices_data_storage', 'data')],
    Input('send_form_button', 'n_clicks'),
    [State('username_input', 'value'),
     State('password_input', 'value')]
)
def manage_login_feedback(n_clicks, username, password):
    if n_clicks is None:
        return True, None, ''

    form_feedback = [dcc.Markdown('---')]

    if username is None or password is None or len(username) == 0 or len(password) == 0:
        form_feedback.append(html.P("Il semble qu'il manque votre nom d'utilisateur et/ou votre mot de passe."))
        return True, form_feedback, ''

    else:

        correspondences = pd.read_csv('data/login_correspondences.csv')

        if username not in correspondences['username'].values or password not in correspondences['password'].values:
            form_feedback.append(html.P("Nom d'utilisateur ou mot de passe erroné."))
            return True, form_feedback, ''

        elif password != correspondences[correspondences['username'] == username]['password'][0]:
            form_feedback.append(html.P("Nom d'utilisateur ou mot de passe erroné."))
            return True, form_feedback, ''

        else:
            form_feedback.append(html.P("Vous êtes connecté, bienvenue sur la plateforme Pyronear !"))
            form_feedback.append('ok')
            return False, form_feedback, get_site_devices_data(client=api_client)


@app.callback(
    Output('login_modal', 'is_open'),
    Input('form_feedback_area', 'children')
)
def close_login_modal(feedback):
    if feedback is None:
        raise PreventUpdate

    if 'ok' in feedback:
        time.sleep(2)
        return False

    else:
        raise PreventUpdate


@app.callback(
    Output('login_background', 'children'),
    Input('login_modal', 'is_open')
)
def clean_login_background(is_modal_opened):
    if is_modal_opened:
        raise PreventUpdate

    else:
        return ''


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "Alerts and Infrastructure" view

@app.callback(
    Output('alerts_info', 'children'),
    Input('geojson_departments', 'hover_feature')
)
def hover_department_alerts(hovered_department):
    """
    -- Displaying department name in the alerts view --

    This callback detects what department is being hovered by the user's cursor.

    It returns the corresponding name in the info object in the upper right corner of the map.
    """
    if hovered_department is not None:
        return build_info_box(hovered_department)
    else:
        return build_info_box()


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
    Output('acknowledge_alert_div_{}'.format(alert_id), 'children'),
    Input('acknowledge_alert_checkbox_{}'.format(alert_id), 'checked')
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
    if not checkbox_checked:
        return [dbc.FormGroup([dbc.Checkbox(id='acknowledge_alert_checkbox_{}'.format(alert_id),
                                            className="form-check-input"),
                               dbc.Label("Confirmer la prise en compte de l'alerte",
                                         html_for='acknowledge_alert_checkbox_{}'.format(alert_id),
                                         className="form-check-label")],
                              check=True,
                              inline=True)]

    elif checkbox_checked:
        return [html.P("Prise en compte de l'alerte confirmée")]


@app.callback(
    [Output('map', 'center'),
     Output('map', 'zoom')],
    Input("alert_button_alerts", "n_clicks"),
    State('map_style_button', 'children')
)
@cache.memoize()
def change_zoom_center(n_clicks, map_style_button_label):
    """
    -- Zooming on the alert from the banner --

    This callback is triggered by the number of clicks on the alert banner.

    It also takes as argument the message displayed on the button which allows the user to choose either the "alerts" or
    "risks" mode for the map, so as to identify which map the user is currently viewing.

    - If the number of clicks is strictly above 0 and we are viewing the "alerts" map, it triggers a zoom on the alert
    marker. To do so, it relies on the define_map_zoom_center function, imported from alerts.

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
        return define_map_zoom_center(n_clicks, alert_metadata)

    elif map_style == 'risks':
        raise PreventUpdate


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "Risk Score" page

@app.callback(
    Output('risks_info', 'children'),
    Input('geojson_risks', 'hover_feature')
)
def hover_department_risks(hovered_department):
    """
    -- Displaying department name in the alerts view --

    This callback detects which department is being hovered on by the user's cursor.
    It returns the corresponding name in the info object in the upper right corner of the map.
    """
    return build_info_box(hovered_department)


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
            build_info_object(map_type='risks'),
            build_legend_box(map_type='risks'),
            html.Div(id='fire_markers_risks'),  # Will contain the past fire markers of the risks map
            html.Div(id='live_alerts_marker')
            ]


@app.callback(Output('fire_markers_risks', 'children'),
              [Input('geojson_risks', 'click_feature'),
               Input('historic_fires_radio_button', 'value')])
def click_department_risks(feature, radio_button_value):
    """
    -- Displaying past fires on the risks map --

    This callback detects what department the user is clicking on.
    It returns the position of past fires in this department as markers on the map.

    It relies on the get_old_fire_positions function, imported from utils.py that takes
    a department code as input and returns a LayerGroup object gathering the markers.

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
    [
        Output("img_url", "children"),
        Output("live_alert_header_btn", "children"),
        Output("live_alerts_marker", "children"),
    ],
    Input("store_live_alerts_data", "data"),
    State("map_style_button", "children")
)
def update_style_components_with_alert_metadata(
        live_alerts, map_style_button_label
):
    """
    -- Updating style components with corresponding alerts data --

    This callback takes as input "live_alerts" which is the json object containing all live alerts. This json is
    retrieved thanks to every 10s call to the API.

    It also takes as input the label of the button that allows users to change the style of the map (but as a 'State'
    mode, so that the callback is not triggered by a change in this label), in order to deduce the style of the map that
    the user is currently looking at.

    Each time it is triggered, the callback uses the data of all ongoing alerts which are stored in
    "store_live_alerts_data" and returns several elements:

    - it stores the URL address of the frame associated with the last alert;
    - it creates the elements that signal the alert around the map (banner);
    - and instantiates the alert markers on the map.

    To build these elements, it relies on the build_alerts_elements imported from alerts.
    """

    # Deducing the style of the map in place from the map style button label
    if "risques" in map_style_button_label.lower():
        map_style = "alerts"

    elif "alertes" in map_style_button_label.lower():
        map_style = "risks"

    # Get live alerts data
    if live_alerts is None:
        raise PreventUpdate

    live_alerts = pd.read_json(live_alerts)

    # Defining the alert status
    if live_alerts.empty:
        alert_status = 0

        img_url = ""

        return build_alerts_elements(img_url, alert_status, alert_metadata, map_style)

    else:
        alert_status = 1

        # Fetching the last alert
        last_alert = live_alerts.loc[live_alerts["id"].idxmax()]

        # Fetching the URL address of the frame associated with the last alert
        img_url = api_client.get_media_url(last_alert["media_id"]).json()["url"]

        return build_alerts_elements(img_url, alert_status, alert_metadata, map_style)


@app.callback(
    [Output('hp_alert_frame_metadata', 'children'),
     Output('display_alert_frame_btn{}'.format(alert_id), 'children')],
    Input('display_alert_frame_btn{}'.format(alert_id), 'n_clicks'),
    State('img_url', 'children')
)
def display_alert_frame_metadata(n_clicks_marker, img_url):
    """
    -- Displaying detection data and the alert frame --

    This callback detects the number of clicks the user has made on the button that allows
    to display the detection data and the alert frame (in the popup of the alert marker).

    If an odd number of clicks has been made, the function returns the image of the corresponding alert
    and the associated metadata in the blank space on the left of the map.

    If an even number of clicks has been made, the space on the left of the map is left blank.
    """
    if (n_clicks_marker + 1) % 2 == 0:
        return display_alerts_frames(n_clicks_marker, alert_metadata, img_url), 'Masquer les données de détection'
    else:
        return display_alerts_frames(), 'Afficher les données de détection'


@app.callback(
    Output('interval-component-homepage', 'disabled'),
    Input("alert_marker_{}".format(alert_id), 'n_clicks')
)
def callback_func_start_stop_interval(n_clicks):
    """
    -- Interrupting API calls for ongoing alerts --

    This callback detects the number of clicks the user made on an alert marker.
    If at least 1 click has been made, the function disables the interval component.

    NB: callback to be eliminated in the future.
    """
    if n_clicks is not None and n_clicks > 0:
        return True
    else:
        return False


# To be uncommented for debug purposes
# @app.callback([Output('live_alert_header_btn', 'children'), Output('live_alerts_marker', 'children')],
#               [Input('alert_radio_button', 'value'), Input('interval-component', 'n_intervals')])
# def define_alert_status_debug(value=None, n_intervals=None):
#     """
#     This callback takes as input the alert_radio_button for debug purposes and defines the alert status
#     depending on the associated values
#     """
#     if value is None:
#         alert_status = 0
#     else:
#         alert_status = 1

#     return build_alerts_elements(alert_status, alert_metadata)


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
        img_url = api_client.get_media_url(last_alert["media_id"]).json()["url"]

        if last_event_id == last_displayed_event_id:
            # the alert is related to an event id which has already been displayed
            # need to send the img_url to the GIF
            raise PreventUpdate
        else:
            # new event, not been displayed yet
            layout_div, style_to_display = build_alert_detected_screen(
                img_url, alert_metadata, last_alert
            )
            return layout_div, style_to_display, last_event_id


@app.callback(
    Output("images_url_current_alert", "data"),
    Input("interval-component-homepage", "n_intervals"),
    [
        State("store_live_alerts_data", "data"),
        State("images_url_current_alert", "data")
    ],
)
def update_dict_of_images(n_intervals, live_alerts, dict_images_url_current_alert):
    """
    -- Update the dictionary of images of ongoing events --

    Dict where keys are event id and value is a list of all urls related to the same event.
    These url come from the API calls, triggered by "interval-component-homepage".
    """
    if live_alerts is None:
        raise PreventUpdate

    else:
        # Fetching the last alert
        live_alerts = pd.read_json(live_alerts)
        last_alert = live_alerts.loc[live_alerts["id"].idxmax()]
        last_event_id = str(last_alert["event_id"])

        # Fetching the URL address of the frame associated with the last alert
        img_url = api_client.get_media_url(last_alert["media_id"]).json()["url"]

        if last_event_id not in dict_images_url_current_alert.keys():
            dict_images_url_current_alert[last_event_id] = []
        dict_images_url_current_alert[last_event_id].append(img_url)

        return dict_images_url_current_alert


@app.callback(
    Output("alert_frame", "src"),
    Input("interval-component-img-refresh", "n_intervals"),
    [
        State("last_displayed_event_id", "data"),
        State("images_url_current_alert", "data")
    ]
)
def update_images_for_doubt_removal(n_intervals, last_displayed_event_id, dict_images_url_current_alert):
    """
    -- Create a pseudo GIF --

    Created from the x frames we received each time there is an alert related to the same event.
    The urls of these images are stored in a dictionary "images_url_current_alert".
    """
    if last_displayed_event_id not in dict_images_url_current_alert.keys():
        raise PreventUpdate

    list_url_images = dict_images_url_current_alert[last_displayed_event_id]
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

    app.run_server(host=args.host, port=args.port, debug=cfg.DEBUG, dev_tools_hot_reload=cfg.DEBUG)
