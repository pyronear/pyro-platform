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
import config as cfg

from flask_caching import Cache
# ------------------------------------------------------------------------------
# App instantiation and overall layout

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])
app.title = 'Pyronear - Monitoring platform'
app.config.suppress_callback_exceptions = True

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


@app.callback(Output('hp_alert_frame_metadata', 'children'),
              [Input('display_alert_frame_btn{}'.format(alert_id), 'n_clicks')])
@cache.memoize()
def display_alert_frame_metadata(n_clicks_marker):
    '''
    This one detects the number of clicks the user made on an alert popup button.
    If 1 click is made, the function returns the image of the corresponding alert.
    '''
    if (n_clicks_marker + 1) % 2 == 0:
        return display_alerts_frames(n_clicks_marker, alert_metadata)
    else:
        return display_alerts_frames()


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
            build_info_object(app_page='risks')]


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


@app.callback([Output('live_alert_header_btn', 'children'), Output('live_alerts_marker', 'children')],
              [Input('alert_radio_button', 'value')])
@cache.memoize()
def define_alert_status(value=None):
    if value is None:
        value = 0

    return build_alerts_elements(value, alert_metadata)


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
