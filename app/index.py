# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import argparse
import urllib.parse

import callbacks.data_callbacks
import callbacks.display_callbacks
import callbacks.export_callbacks
import callbacks.live_callbacks
import dash
import logging_config
from dash import html
from dash.dependencies import Input, Output, State
from layouts.main_layout import get_main_layout
from main import app

import config as cfg
from pages.blinking_alarm import blinking_alarm_layout
from pages.cameras_status import cameras_status_layout
from pages.export import export_layout
from pages.homepage import homepage_layout
from pages.live_stream import live_stream_layout
from pages.login import login_layout

# Configure logging
logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)

# Set the app layout
app.layout = get_main_layout()


# Manage Pages
# Manage Pages
@app.callback(
    Output("page-content", "children"),
    [
        Input("url", "pathname"),
        Input("api_cameras", "data"),
        Input("url", "search"),
        Input("selected-camera-info", "data"),
        Input("language", "data"),
        Input("my-date-picker-single", "date"),
    ],
    [State("user_token", "data"), State("available-stream-sites", "data")],
)
def display_page(
    pathname, api_cameras, search, selected_camera_info, lang, selected_date, user_token, available_stream
):
    logger.debug("display_page called with pathname: %s, user_token: %s using lang %s", pathname, user_token, lang)

    if not isinstance(user_token, str) or not user_token:
        return login_layout(lang=lang)

    triggered = dash.ctx.triggered_id

    if triggered == "selected-camera-info" and selected_camera_info:
        return live_stream_layout(user_token, api_cameras, available_stream, selected_camera_info, lang=lang)

    if triggered == "my-date-picker-single":
        return homepage_layout(user_token, api_cameras, lang=lang, descending_order=False)

    if pathname in ["/", None]:
        return homepage_layout(user_token, api_cameras, lang=lang, descending_order=True)

    if pathname == "/cameras-status":
        return cameras_status_layout(user_token, api_cameras, lang=lang)
    if pathname == "/blinking-alarm":
        return blinking_alarm_layout(user_token, api_cameras, lang=lang)
    if pathname == "/live-stream":
        return live_stream_layout(user_token, api_cameras, available_stream, lang=lang)

    if pathname == "/export":
        return export_layout(lang=lang)

    logger.warning("Unable to find page for pathname: %s", pathname)
    return html.Div([html.P("Unable to find this page.", className="alert alert-warning")])


# ----------------------------------------------------------------------------------------------------------------------
# RUNNING THE WEB-APP SERVER

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pyronear web-app", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host of the server")
    parser.add_argument("--port", type=int, default=8050, help="Port to run the server on")
    args = parser.parse_args()

    logger.info("Starting Pyronear web-app on host: %s, port: %d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=cfg.DEBUG, dev_tools_hot_reload=cfg.DEBUG)
