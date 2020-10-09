"""The following file gathers a few items (variables, functions...) that are common to both dashboards."""

# ------------------------------------------------------------------------------
# Imports

import dash_html_components as html


# ------------------------------------------------------------------------------
# Content

map_style = {
             'width': '100%',
             'height': '90vh',
             'margin': 'auto',
             'display': 'block'
             }

def get_info(feature = None):

    header = [html.H4('Département sélectionné :')]

    if not feature:
        return header + [html.P('Faites glisser votre curseur sur un département')]

    return header + [html.B(feature['properties']['nom'])]

def build_info_object(app_page):

    if app_page == 'alerts':
        object_id = 'alerts_info'
    else:
        object_id = 'risks_info'

    return html.Div(
                    children = get_info(),
                    id = object_id,
                    className = 'info',
                    style = {
                             'position' : 'absolute',
                             'top' : '10px',
                             'right' : '10px',
                             'z-index' : '1000'
                             }
                    )
