'''This file is the main one and the script to run in order to launch the app locally.

Based on the url path, it calls functions imported from the .py in order to build
the appropriate page layout.
'''

# ------------------------------------------------------------------------------
# Imports

### Main Dash imports, used to instantiate the web-app and create callbacks (ie. to generate interactivity)
import dash
from dash.dependencies import Input, Output

### Various modules provided by Dash to build the page layout
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

### For each page of the web-app, we import the corresponding instantiation function
### As well as some other functions from alerts.py and utils.py for interactivity
from homepage import Homepage
from alerts import AlertsApp, get_camera_positions, choose_layer_style
from risks import RisksApp
from utils import get_info


# ------------------------------------------------------------------------------
# App instantiation and overall layout

# We start by instantiating the app (NB: did not try to look for other stylesheets yet)
app = dash.Dash(__name__, external_stylesheets = [dbc.themes.UNITED])
app.config.suppress_callback_exceptions = True

# We create a rough layout that will be filled by the first callback based on the url path
app.layout = html.Div(
                      [
                       dcc.Location(
                                    id = 'url',
                                    refresh = False
                                    ),

                       html.Div(id = 'page-content')
                       ]
                       )


# ------------------------------------------------------------------------------
# CALLBACKS

# ------------------------------------------------------------------------------
# Overall page layout callback

'''
This is the main callback of the app.
It takes the url path as input and returns the corresponding page layout,
thanks to the instantiation functions built in the various .py files.
'''
@app.callback(
              Output('page-content', 'children'),
              Input('url', 'pathname')
              )
def display_page(pathname):
    if pathname == '/alerts':
        return AlertsApp()

    elif pathname == '/risks':
        return RisksApp()

    else:
        return Homepage()


# ------------------------------------------------------------------------------
# Callbacks related to the "Alertes et Infrastructures" dashboard

'''
This one detects what department is being hovered by the user's cursor and
returns the corresponding name in the info object in the upper right corner of the map.
If a marker is hovered instead of a department, it returns nothing for now.
'''
@app.callback(
              Output('alerts_info', 'children'),
              [
               Input('geojson_alerts', 'hover_feature'),
               Input('markers', 'hover_feature')
               ]
              )
def dpt_hover_alerts(hovered_department, hovered_marker):
    if hovered_marker is not None:
        hovered_marker = None
        return None

    return get_info(hovered_department)


'''
This one detects what department the user is clicking on and returns the position
of the cameras deployed in this department as markers on the map. It relies on the
get_camera_positions function, imported from alerts.py that takes a department code
as input and returns a GeoJSON file containing the position of cameras.
'''
@app.callback(Output('markers', 'data'), [Input('geojson_alerts', 'click_feature')])
def region_click(feature):
    if feature is not None:
        return get_camera_positions(feature['properties']['code'])


'''
This callback detects clicks on the button used to change the layer style of the map
and returns the right topographic or satellite view, as well as the appropriate
content for the button.
'''
@app.callback(
              [Output('layer_style_button', 'children'),
               Output('alerts_tile_layer', 'url'),
               Output('alerts_tile_layer', 'attribution')
               ],
              Input('layer_style_button', 'n_clicks')
              )
def change_layer_style(n_clicks = None):
    if n_clicks is None:
        n_clicks = 0

    return choose_layer_style(n_clicks)


# ------------------------------------------------------------------------------
# Callbacks related to the "Niveau de Risque" page

'''
This one detects what department is being hovered by the user's cursor and
returns the corresponding name in the info object in the upper right corner of the map.
'''
@app.callback(
              Output('risks_info', 'children'),
              Input('geojson_risks', 'hover_feature')
              )
def dpt_hover_risks(hovered_department):
    return get_info(hovered_department)


# ------------------------------------------------------------------------------
# Running the web-app server

if __name__ == '__main__':
    app.run_server(debug = True)
