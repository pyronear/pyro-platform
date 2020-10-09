'''This file is dedicated to the homepage.

The main item is the HomePage function that returns the corresponding page layout.
'''

# ------------------------------------------------------------------------------
# Imports

### Various modules provided by Dash to build the page layout
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

### From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar


# ------------------------------------------------------------------------------
# Content (NB: not modified from the tutorial)

nav = Navbar()

body = dbc.Container(
    [
       dbc.Row(
           [
               dbc.Col(
                  [
                     html.H2('Heading'),
                     html.P(
                         """\
Donec id elit non mi porta gravida at eget metus.Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentumnibh, ut fermentum massa justo sit amet risus. Etiam porta semmalesuada magna mollis euismod. Donec sed odio dui. Donec id elit nonmi porta gravida at eget metus. Fusce dapibus, tellus ac cursuscommodo, tortor mauris condimentum nibh, ut fermentum massa justo sitamet risus. Etiam porta sem malesuada magna mollis euismod. Donec sedodio dui.
                         """
                            ),
                     dbc.Button(
                                'View details',
                                color = 'secondary'
                                ),
                   ],
                   md = 4,
               ),
              dbc.Col(
                 [
                     html.H2("Graph"),
                     dcc.Graph(
                         figure={"data": [{"x": [1, 2, 3], "y": [1, 4, 9]}]}
                            ),
                        ]
                     ),
                ]
            )
       ],
className="mt-4",
)

def Homepage():

    layout = html.Div(
                      [
                       nav,
                       body
                       ]
                      )

    return layout
