"""The following file gathers a few items (variables, functions...) that are common to both dashboards."""

# ------------------------------------------------------------------------------
# Imports

import dash_html_components as html


# ------------------------------------------------------------------------------
# Content  : Those functions aim at returning either the name of :
#  the hovered department
#  the hovered camera (marker)
# ------------------------------------------------------------------------------

map_style = {'width': '100%',
             'height': '75vh',
             'margin': 'auto',
             'display': 'block'}


def get_info(feature=None, feature_type=None):
    '''
    This function check the geojson object thanks to the feature_type
    argument and returns the appropriate message.
    '''
    header_dept = [html.H4('Département sélectionné :')]
    header_camera = [html.H4('Caméra sélectionnée :')]
    if feature:
        if feature_type == 'markers_hover':
            return header_camera + [html.B('Zone: {}'.format(feature['properties']['area']))]
        elif feature_type == 'markers_click':
            return header_camera + [html.B(feature['properties']['popup'])]
        elif feature_type in ['geojson_alerts', 'geojson_risks']:
            return header_dept + [html.B(feature['properties']['nom'])]
    # if no object are hovered, it just return standard statement
    return header_dept + [html.P('Faites glisser votre curseur sur un département')]


def build_info_object(app_page):

    if app_page == 'alerts':
        object_id = 'alerts_info'
    else:
        object_id = 'risks_info'

    return html.Div(children=get_info(),
                    id=object_id,
                    className='info',
                    style={'position': 'absolute',
                           'top': '10px',
                           'right': '10px',
                           'z-index': '1000'}
                    )
