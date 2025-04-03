# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import dash_bootstrap_components as dbc
from dash import Dash

import config as cfg
from components.alerts import alert_layout

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.css.append_css({"external_url": "/assets/style.css"})


def homepage_layout(user_token, api_cameras, lang="fr"):
    return alert_layout(api_cameras, cfg.TRANSLATION["alert_default"], lang)
