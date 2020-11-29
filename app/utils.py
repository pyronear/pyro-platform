"""The following file gathers a few items (variables, functions...) that are common to both dashboards."""

# ------------------------------------------------------------------------------
# Imports

import dash_html_components as html
import dash_leaflet as dl
import dash_bootstrap_components as dbc

# ------------------------------------------------------------------------------
# Content  : Those functions aim at returning either the name of :
#  the hovered department
#  the hovered camera (marker)
# ------------------------------------------------------------------------------

map_style = {'width': '100%',
             'height': '75vh',
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

# ------------------------------------------------------------------------------
# Content  : Those functions aim at fetching API data and more specificaly :
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
