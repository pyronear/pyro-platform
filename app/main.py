'''
The following is the main file and the script to run in order to launch the app locally.

It can be launched from the root of the repository by running in a Terminal window:

"python app/main.py"

It is built around 4 main sections:

- Imports

- App instantiation and overall layout, which creates the app and related attributes

- Callbacks, which gathers the functions that create interactivity for:
    - The whole app
    - The "Alerts and Infrastructure" view
    - The "Risk Score" view
    - The homepage

- Running the web-app server, which allows to launch the app via the Terminal command.
'''


# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# General imports
import pandas as pd
from flask_caching import Cache
import config as cfg  # Cf. config.py file

# Importing the pyro-API client
from services import api_client

# Main Dash imports, used to instantiate the web-app and create callbacks (ie. to generate interactivity)
import dash
from dash.dependencies import Input, Output, State

# Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# From homepage.py, we import the main layout instantiation function
from homepage import Homepage

# From other Python files, we import some functions needed for interactivity
from homepage import choose_map_style, display_alerts_frames
from alerts import define_map_zoom_center, build_alerts_elements
from risks import build_risks_geojson_and_colorbar
from utils import choose_layer_style, build_info_box, build_info_object,\
    build_live_alerts_metadata, build_historic_markers, build_legend_box


# ----------------------------------------------------------------------------------------------------------------------
# APP INSTANTIATION & OVERALL LAYOUT

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# We define a few attributes of the app object
app.title = 'Pyronear - Monitoring platform'
app.config.suppress_callback_exceptions = True
server = app.server   # Gunicorn will be looking for the server attribute of this module

# We create a rough layout, filled with the content of the homepage
app.layout = html.Div([dcc.Location(id='url', refresh=False),
                       html.Div(id='page-content', children=Homepage())])

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
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n, is_open):
    '''
    This overall callback on the navigation bar allows
    to toggle the collapse on small screens.'''
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
    '''
    -- Moving between schematic and satellite layers --

    This callback detects clicks on the button used to change the layer style of the map.

    It returns:

    - the right topographic or satellite view, by changing the 'url' and 'attribution'
    attributes of the 'tile_layer' object in the alerts map;
    - and the appropriate content for the button allowing to change the layer style.

    To do so, it relies on the choose_layer_style function defined in the alerts Python file.
    '''
    if n_clicks is None:
        n_clicks = 0

    return choose_layer_style(n_clicks)


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "Alertes and Infrastructure" view

@app.callback(
    Output('alerts_info', 'children'),
    Input('geojson_departments', 'hover_feature')
)
def hover_department_alerts(hovered_department):
    '''
    -- Displaying department name in the alerts view --

    This callback detects what department is being hovered by the user's cursor.

    It returns the corresponding name in the info object in the upper right corner of the map.
    '''
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
    '''
    -- Displaying past fires on the alerts map --

    This callback detects what department the user is clicking on.
    It returns the position of past fires in this department as markers on the map.

    It relies on the get_old_fire_positions function, imported from utils.

    It also takes as input the value of the radio button dedicated to past fires:

    - if the user has selected "Non", the container of historic fire markers is left empty;
    - if the user has selected "Yes", we fill it in with the relevant information.
    '''
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
    '''
    -- Allowing user to acknowledge an alert --

    This callback takes as input the status of the checkbox that the user can see when
    clicking on an alert marker and can use to acknowledge the alert.

    For now, if the checkbox is checked, it simply eliminates the checkbox and displays
    a message according to which the alert has already been taken into account.

    Still to be done regarding this callback:

    - use the client to effectively report the acknowledgement to the DB;
    - check if an alert is acknowledged or not in the DB to display the right message.
    '''
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


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the "Risk Score" page

@app.callback(
    Output('risks_info', 'children'),
    Input('geojson_risks', 'hover_feature')
)
def hover_department_risks(hovered_department):
    '''
    -- Displaying department name in the alerts view --

    This callback detects which department is being hovered on by the user's cursor.
    It returns the corresponding name in the info object in the upper right corner of the map.
    '''
    return build_info_box(hovered_department)


@app.callback(
    Output('map', 'children'),
    Input('opacity_slider_risks', 'value')
)
def change_color_opacity(opacity_level):
    '''
    -- Managing color opacity in the choropleth map --

    This callback takes as input the opacity level chosen by the user on the slider.
    It then reinstantiates the colorbar and geojson objects accordingly.
    These new objects are finally returned into the risks map's children attribute.
    '''
    colorbar, geojson = build_risks_geojson_and_colorbar(opacity_level=opacity_level)

    return [dl.TileLayer(id='tile_layer'),
            geojson,
            colorbar,
            build_info_object(map_type='risks'),
            build_legend_box(map_type='risks'),
            html.Div(id='fire_markers_risks')  # Will contain the past fire markers of the risks map
            ]


@app.callback(Output('fire_markers_risks', 'children'),
              [Input('geojson_risks', 'click_feature'),
               Input('historic_fires_radio_button', 'value')])
def click_department_risks(feature, radio_button_value):
    '''
    -- Displaying past fires on the risks map --

    This callback detects what department the user is clicking on.
    It returns the position of past fires in this department as markers on the map.

    It relies on the get_old_fire_positions function, imported from utils.py that takes
    a department code as input and returns a LayerGroup object gathering the markers.

    It also takes as input the value of the radio button dedicated to past fires:

    - if the user has selected "Non", the container of historic fire markers is left empty;
    - if the user has selected "Yes", we fill it in with the relevant information.
    '''
    if feature is not None:
        if radio_button_value == 1:
            return build_historic_markers(dpt_code=feature['properties']['code'])
        else:
            return None


# ----------------------------------------------------------------------------------------------------------------------
# Callbacks related to the homepage

@app.callback(
    [Output('map_style_button', 'children'),
     Output('hp_map', 'children'),
     Output('hp_slider', 'children')],
    Input('map_style_button', 'n_clicks'))
def change_map_style(n_clicks=None):
    '''
    -- Moving between alerts and risks views --

    This callback detects clicks on the button used to change the style of the map, ie.
    to switch from the "Alerts and Infrastructure" to the "Risk Scores" view and vice-versa.

    It relies on the choose_map_style function, imported from homepage.

    It returns:

    - the appropriate for the button on which the user has just clicked;
    - the right map object;
    - the slider object if relevant.
    '''
    if n_clicks is None:
        n_clicks = 0

    return choose_map_style(n_clicks)


@app.callback(
    [Output('map', 'center'),
     Output('map', 'zoom')],
    Input("alert_button", "n_clicks")
)
@cache.memoize()
def change_zoom_center(n_clicks=None):
    '''
    -- Zooming on the alert from the banner --

    This callback takes as input the number of clicks on the alert banner.
    If the number of clicks is strictly above 0, it triggers a zoom on the alert marker.
    It relies on the define_map_zoom_center function, imported from alerts.
    '''
    if n_clicks is None:
        n_clicks = 0

    return define_map_zoom_center(n_clicks, alert_metadata)


@app.callback(
    [Output('img_url', 'children'),
     Output('live_alert_header_btn', 'children'),
     Output('live_alerts_marker', 'children')],
    Input('interval-component', 'n_intervals')
)
def fetch_alert_status_metadata(n_intervals):
    '''
    -- Fetching and refreshing alerts data --

    This callback takes as input the 'n_intervals' attribute of the interval component,
    which acts as a timer with the number of intervals increasing by 1 every 10 seconds.

    Each time it is triggered, the callback makes a call to the API to get all ongoing alerts,
    filters out those which have been already acknowledged and returns several elements:

    - it stores the URL address of the frame associated with the last alert;
    - it creates the elements that signall the alert around the map (banner);
    - and instantiates the alert markers on the map.

    To build these elements, it relies on the build_alerts_elements imported from alerts.
    scheduling API metadata fetches and defining alert status
    '''

    # Fetching live alerts where is_acknowledged is False
    response = api_client.get_ongoing_alerts().json()
    all_alerts = pd.DataFrame(response)
    live_alerts = all_alerts.loc[~all_alerts['is_acknowledged']]

    # Defining the alert status
    if live_alerts.empty:
        alert_status = 0
        img_url = ""
        return build_alerts_elements(img_url, alert_status, alert_metadata)

    else:
        alert_status = 1

        # Fetching the last alert
        last_alert = live_alerts.loc[live_alerts['id'].idxmax()]

        # Fetching the URL address of the frame associated with the last alert
        img_url = api_client.get_media_url(last_alert['media_id']).json()["url"]

        return build_alerts_elements(img_url, alert_status, alert_metadata)


@app.callback(
    Output('hp_alert_frame_metadata', 'children'),
    Input('display_alert_frame_btn{}'.format(alert_id), 'n_clicks'),
    State('img_url', 'children')
)
def display_alert_frame_metadata(n_clicks_marker, img_url):
    '''
    -- Displaying detection data and the alert frame --

    This callback detects the number of clicks the user has made on the button that allows
    to display the detection data and the alert frame (in the popup of the alert marker).

    If an odd number of clicks has been made, the function returns the image of the corresponding alert
    and the associated metadata in the blank space on the left of the map.

    If an even number of clicks has been made, the space on the left of the map is left blank.
    '''
    if (n_clicks_marker + 1) % 2 == 0:
        return display_alerts_frames(n_clicks_marker, alert_metadata, img_url)
    else:
        return display_alerts_frames()


@app.callback(
    Output('interval-component', 'disabled'),
    Input("alert_marker_{}".format(alert_id), 'n_clicks')
)
def callback_func_start_stop_interval(n_clicks):
    '''
    -- Interrupting API calls for ongoing alerts --

    This callback detects the number of clicks the user made on an alert marker.
    If at least 1 click has been made, the function disables the interval component.

    NB: callback to be eliminated in the future.
    '''
    if n_clicks is not None and n_clicks > 0:
        return True
    else:
        return False


# To be uncommented for debug purposes
# @app.callback([Output('live_alert_header_btn', 'children'), Output('live_alerts_marker', 'children')],
#               [Input('alert_radio_button', 'value'), Input('interval-component', 'n_intervals')])
# def define_alert_status_debug(value=None, n_intervals=None):
#     '''
#     This callback takes as input the alert_radio_button for debug purposes and defines the alert status
#     depending on the associated values
#     '''
#     if value is None:
#         alert_status = 0
#     else:
#         alert_status = 1

#     return build_alerts_elements(alert_status, alert_metadata)


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
