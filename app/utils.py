"""The following file gathers a few items (variables, functions...) that are common to both dashboards."""

# ------------------------------------------------------------------------------
# Imports

from pathlib import Path

import pandas as pd

import datetime as dt

import dash_html_components as html
import dash_leaflet as dl


# ------------------------------------------------------------------------------
# Content  : Those functions aim at returning either the name of :
#  the hovered department
#  the hovered camera (marker)
# ------------------------------------------------------------------------------

map_style = {'width': '100%',
             'height': '90vh',
             'margin': 'auto',
             'display': 'block'}


def build_info_box(feature=None):
    """
    This function generates an information box about the hovered department.
    It takes as argument the geojson hovered by the user
    It returns the appropriate message for each element in the box.
    """
    header_dept = [html.H4('Département sélectionné :')]

    if feature:
        return header_dept + [html.B(feature['properties']['nom'])]

    # If no object is hovered, it just returns a standard statement
    return header_dept + [html.P('Faites glisser votre curseur sur un département')]


def build_popup(feature=None):
    """
    This function extract info to display from the geojson object
    It takes as argument the geojson clicked by user
    It returns the popup with the appropriate info for each markers on the map.
    """
    if feature is not None:
        coord = 'Coordonnées de la caméra : {}'.format(feature['geometry']['coordinates'])
        return [dl.Popup(coord)]


def build_info_object(app_page):
    """
    This function takes as input the page of interest and outputs the relevant
    information box located at the top right of the map.
    """
    if app_page == 'alerts':
        object_id = 'alerts_info'

    else:
        object_id = 'risks_info'

    return html.Div(children=build_info_box(),
                    id=object_id,
                    className='info',
                    style={'position': 'absolute',
                           'top': '10px',
                           'right': '10px',
                           'z-index': '1000'}
                    )


def build_legend_box(app_page=None):
    """
    This function generates a legend box, whose content depends on the map chosen.
    It takes as argument the type of map (alerts or risks chosen by the user).
    It returns the appropriate legend for each of the two maps in the box.
    """
    site_img_url = '../assets/pyro_site_icon.png'
    past_fire_img_url = '../assets/pyro_oldfire_icon.png'
    alert_img_url = '../assets/pyro_alert_icon.png'

    img_style = {'width': '4.5vh',
                 'height': '4.5vh'}

    image_div_style = {'display': 'inline-block', 'height': '22px', 'margin-left': '2px'}
    text_div_style = {'display': 'inline-block', 'height': '22px', 'margin-left': '7px'}

    if app_page == 'alerts':

        # Site de surveillance
        legend_body = [html.Div([html.Div(html.Img(src=site_img_url, style=img_style),
                                          style=image_div_style),
                                 html.Div(html.P('Matériel installé'),
                                          style=text_div_style)])]

        # Historique des feux
        legend_body.append(html.Div([html.Div(html.Img(src=past_fire_img_url, style=img_style),
                                              style=image_div_style),
                                     html.Div(html.P('Feu passé'),
                                              style=text_div_style)]))

        # Alerte
        legend_body.append(html.Div([html.Div(html.Img(src=alert_img_url, style=img_style),
                                              style=image_div_style),
                                     html.Div(html.P('Alerte en cours'),
                                              style=text_div_style)]))

    elif app_page == 'risks':
        legend_body = [html.Div([html.Div(html.Img(src=past_fire_img_url, style=img_style),
                                          style=image_div_style),
                                 html.Div(html.P('Feu passé'),
                                          style=text_div_style)])]

    legend_id = 'legend_' + app_page

    return html.Div(children=legend_body,
                    id=legend_id,
                    className='info',
                    style={'position': 'absolute',
                           'bottom': '30px',
                           'right': '10px',
                           'z-index': '1000'}
                    )


# Block dedicated to fetching the positions of past fires and building the related map attribute
# Fetching the positions of past fires in a given department
def get_old_fire_positions(dpt_code=None):

    # As long as the user does not click on a department, dpt_code is None and we return no fire marker
    if not dpt_code:
        return None

    # We read the csv file that locates the old fires and filter for the department of interest
    old_fire_positions = pd.read_csv(Path(__file__).parent.joinpath('data', 'historic_fires.csv'), ',')
    # Below it allows us to filter by department with a click on the map
    old_fire_positions = old_fire_positions[old_fire_positions['Département'] == int(dpt_code)].copy()

    icon = {"iconUrl": '../assets/pyro_oldfire_icon.png',
            "iconSize": [50, 50],       # Size of the icon
            "iconAnchor": [25, 45],      # Point of the icon which will correspond to marker's and popup's location
            "popupAnchor": [0, -20]  # Point from which the popup should open relative to the iconAnchor
            }

    # We build a list of dictionaries containing the coordinates of each fire
    fire_markers = []
    for i, row in old_fire_positions.iterrows():
        lat = row['latitude']
        lon = row['longitude']
        location = row['location']
        date = dt.datetime.strptime(row['acq_date'], '%Y-%m-%d')\
                          .strftime('%d %b %Y')

        if row['daynight'] == 'D':
            daynight = 'Diurne'
        elif row['daynight'] == 'N':
            daynight = 'Nocturne'
        else:
            daynight = None

        fire_markers.append(dl.Marker(id=f'historic_fire_{i}',  # Set an id for each marker to receive callbacks
                                      position=(lat, lon),
                                      icon=icon,
                                      children=[dl.Tooltip(f"Date: {date}"),
                                                dl.Popup([html.H2(f'Feu du {date}'),
                                                          html.P(f'Commune : {location}'),
                                                          html.P(f'Type : {daynight}')])
                                                ]
                                      )
                            )

    return fire_markers


# Once we have the positions of past fires, we output another GeoJSON object gathering these locations
def build_historic_markers(dpt_code=None):
    fire_markers = dl.LayerGroup(children=get_old_fire_positions(dpt_code), id='historic_fires_markers')

    return fire_markers

# ------------------------------------------------------------------------------
# Content  : Those functions aim at fetching API data and more specifically :
#  query alerts db to build alert metadata
#  query devices db to devices alert metadata
#  for now this is still a drafted response, proper API calls will be done soon
# ------------------------------------------------------------------------------


def build_live_alerts_metadata():

    alert_metadata = {
        "id": 0,
        "created_at": "2020-11-25T15:22:21.690Z",
        "media_url": "https://photos.lci.fr/images/613/344/photo-incendie-generac-gard-e8f2d9-0@1x.jpeg",
        "lat": 44.765181,
        "lon": 4.51488,
        "event_id": 0,
        "azimuth": "49.2°",
        "site_name": "Serre de pied de Boeuf",
        "type": "start",
        "is_acknowledged": False,
        "device_id": 123
    }

    return alert_metadata
