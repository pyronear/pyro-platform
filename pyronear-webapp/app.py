'''Module docstring to be completed.'''

import pandas as pd
import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

app = dash.Dash(__name__)

# ------------------------------------------------------------------------------
# Import and clean data (importing csv into pandas)

#...

# ------------------------------------------------------------------------------
# App layout

#...

# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components

#...

# ------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
