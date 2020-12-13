"""The following is the main file and the script to run in order to launch the app locally.
Based on the url path, it calls functions imported from the .py in order to build
the appropriate page layout.
"""

# ------------------------------------------------------------------------------
# Imports

# Main Dash imports, used to instantiate the web-app and create callbacks (ie. to generate interactivity)
import dash
from dash.dependencies import Input, Output, State

# Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_leaflet as dl

# For each page of the web-app, we import the corresponding instantiation function
# as well as some other functions from alerts.py and utils.py for interactivity
from homepage import Homepage, choose_map_style, display_alerts_frames
from alerts import AlertsApp, choose_layer_style, define_map_zoom_center, build_alerts_elements
from risks import RisksApp, build_risks_geojson_and_colorbar
from utils import build_info_box, build_info_object, build_live_alerts_metadata
from utils import build_historic_markers, build_legend_box
import config as cfg

from flask_caching import Cache

# Pandas, to read API json responses
import pandas as pd

# Client API import
from services import api_client

# ------------------------------------------------------------------------------
# App instantiation and overall layout

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])
app.title = 'Pyronear - Monitoring platform'
app.config.suppress_callback_exceptions = True
# Gunicorn will be looking for the server attribute of this module
server = app.server

# We create a rough layout that will be filled by the first callback based on the url path
app.layout = html.Div([dcc.Location(id='url', refresh=False),
                       html.Div(id='page-content')])

#Cache configuration
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': '.cache',
    'CACHE_DEFAULT_TIMEOUT': 60
})
# ------------------------------------------------------------------------------
# CALLBACKS

# ------------------------------------------------------------------------------
# General callbacks


# Overall navbar callback for toggling the collapse on small screens
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# Overall page layout callback
@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    '''
    This is the main callback of the app.
    It takes the url path as input and returns the corresponding page layout,
    thanks to the instantiation functions built in the various .py files.
    '''

    if pathname == '/alerts':
        return AlertsApp()

    elif pathname == '/risks':
        return RisksApp()

    else:
        return Homepage()


# ------------------------------------------------------------------------------
# Callbacks related to the "Alertes et Infrastructures" dashboard

# Fetching reusable alert metadata
alert_metadata = build_live_alerts_metadata()
alert_id = alert_metadata["id"]


@app.callback(Output('alerts_info', 'children'),
              [Input('geojson_departments', 'hover_feature')])
def dpt_hover_alerts(hovered_department):
    '''
    This one detects what department is being hovered by the user's cursor and
    returns the corresponding name in the info object in the upper right corner of the map.
    If a marker is hovered instead of a department, it returns its area info for now.
    If a marker is clicked instead of hovered, it returns a simple message for now.
    '''
    if hovered_department is not None:
        return build_info_box(hovered_department)
    else:
        return build_info_box()


# @app.callback(Output('sites_markers', 'children'), [Input('geojson_departments', 'click_feature')])
# def region_click(feature):
#     '''
#     This one detects which department the user is clicking on and returns the position
#     of the cameras deployed in this department as markers on the map. It relies on the
#     get_camera_positions function, imported from alerts.py that takes a department code
#     as input and returns a GeoJSON file containing cameras positions.
#     '''
#     if feature is not None:
#         return get_sites_list(feature['properties']['code'])


@app.callback([Output('layer_style_button', 'children'), Output('tile_layer', 'url'),
               Output('tile_layer', 'attribution')],
              Input('layer_style_button', 'n_clicks'))
def change_layer_style(n_clicks=None):
    '''
    This callback detects clicks on the button used to change the layer style of the map
    and returns the right topographic or satellite view, as well as the appropriate
    content for the button.
    '''
    if n_clicks is None:
        n_clicks = 0

    return choose_layer_style(n_clicks)


@app.callback(Output('fire_markers_alerts', 'children'),
              [Input('geojson_departments', 'click_feature'),
               Input('historic_fires_radio_button', 'value')])
def region_click_alerts(feature, radio_button_value):
    '''
    -- Displaying past fires on the alerts map --

    This one detects what department the user is clicking on and returns the
    position of the old fires in this department as markers on the map.

    It relies on the get_old_fire_positions function, imported from historic.py that takes
    a department code as input and returns a GeoJSON file containing the position of the old fires.

    It also takes as input the value of the radio button dedicated to past fires,
    so that if the user has selected "Non", the container of historic fire markers
    is left empty and we fill it with the relevant information if the user has selected "Yes".
    '''
    if feature is not None:
        if radio_button_value == 1:
            return build_historic_markers(dpt_code=feature['properties']['code'])
        else:
            return None

@app.callback(Output('acknowledge_alert_div_{}'.format(alert_id), 'children'),
              [Input('acknowledge_alert_checkbox_{}'.format(alert_id), 'checked')])
def acknowledge_alert(checkbox_checked):
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

# ------------------------------------------------------------------------------
# Callbacks related to the "Niveau de Risque" page


@app.callback(Output('risks_info', 'children'), Input('geojson_risks', 'hover_feature'))
def dpt_hover_risks(hovered_department):
    '''
    This one detects which department is being hovered on by the user's cursor and
    returns the corresponding name in the info object in the upper right corner of the map.
    '''
    return build_info_box(hovered_department)


@app.callback(Output('map', 'children'), Input('opacity_slider_risks', 'value'))
def dpt_color_opacity(opacity_level):
    '''
    This callback takes as input the opacity level chosen by the user on the slider
    and reinstantiates the colorbar and geojson objects accordingly.
    These new objects are then injected in the map's children attribute.
    '''
    colorbar, geojson = build_risks_geojson_and_colorbar(opacity_level=opacity_level)

    return [dl.TileLayer(id='tile_layer'),
            geojson,
            colorbar,
            build_info_object(app_page='risks'),
            build_legend_box(app_page='risks'),
            html.Div(id='fire_markers_risks')  # Will contain the past fire markers of the risks map
            ]


@app.callback(Output('fire_markers_risks', 'children'),
              [Input('geojson_risks', 'click_feature'),
               Input('historic_fires_radio_button', 'value')])
def region_click_risks(feature, radio_button_value):
    '''
    -- Displaying past fires on the risks map --

    This one detects what department the user is clicking on and returns the
    position of the old fires in this department as markers on the map.

    It relies on the get_old_fire_positions function, imported from historic.py that takes
    a department code as input and returns a GeoJSON file containing the position of the old fires.

    It also takes as input the value of the radio button dedicated to past fires,
    so that if the user has selected "Non", the container of historic fire markers
    is left empty and we fill it with the relevant information if the user has selected "Yes".
    '''
    if feature is not None:
        if radio_button_value == 1:
            return build_historic_markers(dpt_code=feature['properties']['code'])
        else:
            return None

# ------------------------------------------------------------------------------
# Callbacks related to Homepage


@app.callback([
    Output('map_style_button', 'children'), Output('hp_map', 'children'),
    Output('hp_slider', 'children')],
    Input('map_style_button', 'n_clicks'))
def change_map_style(n_clicks=None):
    '''
    This callback detects clicks on the button used to change the layer style of the map
    and returns the right topographic or satellite view, as well as the appropriate
    content for the button.
    '''
    if n_clicks is None:
        n_clicks = 0

    return choose_map_style(n_clicks)


@app.callback([Output('map', 'center'), Output('map', 'zoom')],
              Input("alert_button", "n_clicks"))
@cache.memoize()
def change_zoom_center(n_clicks=None):

    if n_clicks is None:
        n_clicks = 0

    return define_map_zoom_center(n_clicks, alert_metadata)


@app.callback(
    [Output('img_url', 'children'), Output('live_alert_header_btn', 'children'),
     Output('live_alerts_marker', 'children')],
    Input('interval-component', 'n_intervals'))
def fetch_alert_status_metadata(n_intervals):
    '''
    This callback takes as input the interval-component which acts as a timer,
    scheduling API metadata fetches and defining alert status
    '''
    # Fetching live alerts where is_acknowledged is False
    response = api_client.get_ongoing_alerts().json()
    all_alerts = pd.DataFrame(response)
    live_alerts = all_alerts.loc[~all_alerts['is_acknowledged']]

    # Defining alert status
    if live_alerts.empty:
        alert_status = 0
        img_url = ""
        return build_alerts_elements(img_url, alert_status, alert_metadata)
    else:
        alert_status = 1
        # Fetching last alert
        last_alert = live_alerts.loc[live_alerts['id'].idxmax()]

        # Fetching last alert frame url
        img_url = api_client.get_media_url(last_alert['media_id']).json()["url"]
        return build_alerts_elements(img_url, alert_status, alert_metadata)


'''
To be uncommented for debug purposes
@app.callback([Output('live_alert_header_btn', 'children'), Output('live_alerts_marker', 'children')],
              [Input('alert_radio_button', 'value'), Input('interval-component', 'n_intervals')])
def define_alert_status_debug(value=None, n_intervals=None):

    This callback takes as input the alert_radio_button for debug purposes and defines the alert status
    depending on the associated values

    if value is None:
        alert_status = 0
    else:
        alert_status = 1

    return build_alerts_elements(alert_status, alert_metadata)
'''


@app.callback(Output('hp_alert_frame_metadata', 'children'),
              Input('display_alert_frame_btn{}'.format(alert_id), 'n_clicks'), State('img_url', 'children'))
def display_alert_frame_metadata(n_clicks_marker, img_url):
    '''
    This one detects the number of clicks the user made on an alert popup button.
    If 1 click is made, the function returns the image of the corresponding alert.
    '''
    if (n_clicks_marker + 1) % 2 == 0:
        return display_alerts_frames(n_clicks_marker, alert_metadata, img_url)
    else:
        return display_alerts_frames()


@app.callback(
    Output('interval-component', 'disabled'),
    [Input("alert_marker_{}".format(alert_id), 'n_clicks')])
def callback_func_start_stop_interval(n_clicks):
    '''
    This one detects the number of clicks the user made on an alert marker.
    If 1 click is made, the function disables the interval component.
    '''
    if n_clicks is not None and n_clicks > 0:
        return True
    else:
        return False


# ------------------------------------------------------------------------------
# Running the web-app server


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pyronear web-app',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host of the server')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the server on')
    args = parser.parse_args()

    app.run_server(host=args.host, port=args.port, debug=cfg.DEBUG, dev_tools_hot_reload=cfg.DEBUG)
