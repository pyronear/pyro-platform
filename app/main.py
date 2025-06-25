# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import os

import dash
import dash_bootstrap_components as dbc
import logging_config
import sentry_sdk
from flask import send_file
from sentry_sdk.integrations.flask import FlaskIntegration

import config as cfg

# Configure logging
logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)

# Sentry (this will be handled by logging configuration now)
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
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.UNITED],
    external_scripts=["https://unpkg.com/panzoom@9.4.0/dist/panzoom.min.js"],
)

# We define a few attributes of the app object
app.title = "Pyronear - Monitoring platform"
app.config.suppress_callback_exceptions = True
server = app.server  # Gunicorn will be looking for the server attribute of this module


@server.route("/download/<path:filename>")
def download_file(filename):
    zip_dir = os.path.join(os.getcwd(), "zips")  # Full path to the zips folder
    file_path = os.path.join(zip_dir, filename)

    if not os.path.exists(file_path):
        return f"File {filename} not found.", 404

    return send_file(file_path, as_attachment=True)
