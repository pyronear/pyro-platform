"""The following file gathers a few items (variables, functions...) that are common to both dashboards."""

# ------------------------------------------------------------------------------
# Imports

import dash_html_components as html
import dash_leaflet as dl

# ------------------------------------------------------------------------------
# Content  : Those functions aim at returning either the name of :
#  the hovered department
#  the hovered camera (marker)
# ------------------------------------------------------------------------------

map_style = {'width': '100%',
             'height': '75vh',
             'margin': 'auto',
             'display': 'block'}


def build_alerts_map(feature=None, feature_type=None):
    """
    This function  the geojson object thanks to feature_type.
    It takes as argument the geojson hovered by user
    and the type of attribute we want to use from it
    It returns the appropriate message for each elements on the map.
    """
    header_dept = [html.H4('Département sélectionné :')]
    header_camera = [html.H4('Caméra sélectionnée :')]

    if feature:

        if feature_type == 'markers_hover':
            return header_camera + [html.B('Zone: {}'.format(feature['properties']['area']))]
        elif feature_type in ['geojson_alerts', 'geojson_risks']:
            return header_dept + [html.B(feature['properties']['nom'])]

    # If no object are hovered, it just return standard statement
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

    return html.Div(children=build_alerts_map(),
                    id=object_id,
                    className='info',
                    style={'position': 'absolute',
                           'top': '10px',
                           'right': '10px',
                           'z-index': '1000'}
                    )
