# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import dash
import dash_bootstrap_components as dbc

# We start by instantiating the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# We define a few attributes of the app object
app.title = "Pyronear - Monitoring platform"
app.config.suppress_callback_exceptions = True
server = app.server  # Gunicorn will be looking for the server attribute of this module
