# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import logging

import dash
import dash_bootstrap_components as dbc
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

import config as cfg

# APP INSTANTIATION & OVERALL LAYOUT
logger = logging.getLogger("uvicorn.error")
# Sentry
if isinstance(cfg.SENTRY_DSN, str):
    sentry_sdk.init(
        dsn=cfg.SENTRY_DSN,
        release=cfg.VERSION,
        server_name=cfg.SERVER_NAME,
        environment="production" if isinstance(cfg.SERVER_NAME, str) else None,
        integrations=[
            FlaskIntegration(),
        ],
        traces_sample_rate=1.0,
    )
    logger.info(f"Sentry middleware enabled on server {cfg.SERVER_NAME}")

# We start by instantiating the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# We define a few attributes of the app object
app.title = "Pyronear - Monitoring platform"
app.config.suppress_callback_exceptions = True
server = app.server  # Gunicorn will be looking for the server attribute of this module
