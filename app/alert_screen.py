# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

"""
The following Python file is dedicated to the big screen of the web application.
The big screen corresponds to a web page which will be displayed on a big screen in the CODIS room. There will be no
interaction with the user. The main use of this page is to display a "sober" screen when there are no alerts. When an
alert pops out, the screen will automatically change to display various information.

Most functions defined below are designed to be called in the main.py file.
"""

# ----------------------------------------------------------------------------------------------------------------------
# IMPORTS

# Various modules provided by Dash to build the page layout
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html

# From navbar.py to add the navigation bar at the top of the page
from navbar import Navbar

# Importing alerts map builder from alerts.py
from alerts import build_alerts_map

# Importing risks map and opacity slider builders from risks.py
from risks import build_risks_map, build_opacity_slider

# Importing plotly fig objects from graphs.py
from graphs import generate_meteo_fig

# Importing layer style button builder and fetched API data from utils.py
from utils import build_layer_style_button, build_live_alerts_metadata


# ----------------------------------------------------------------------------------------------------------------------
# CONTENT



# ----------------------------------------------------------------------------------------------------------------------
# App layout
# The following block gathers elements defined above and returns them via the BigScreen function


def Bigscreen():
    """
    The following function is used in the main.py file to build the layout of the big screen page.
    """
    raise NotImplementedError
