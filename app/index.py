# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.
import argparse

import callbacks.data_callbacks
import callbacks.display_callbacks  # noqa: F401
import logging_config
from dash import html
from dash.dependencies import Input, Output, State
from layouts.main_layout import get_main_layout
from main import app

import config as cfg
from pages.homepage import homepage_layout
from pages.login import login_layout

# Configure logging
logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)

# Set the app layout
app.layout = get_main_layout()


# Manage Pages
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname"), Input("user_headers", "data")],
    State("user_credentials", "data"),
)
def display_page(pathname, user_headers, user_credentials):

    logger.debug(
        "display_page called with pathname: %s, user_headers: %s, user_credentials: %s",
        pathname,
        user_headers,
        user_credentials,
    )
    if user_headers is None:
        if pathname == "/" or pathname is None:
            logger.info("No user headers found, showing login layout (default language: French).")
            return login_layout(lang="fr")
        if pathname == "/fr":
            logger.info("No user headers found, showing login layout (language: French).")
            return login_layout(lang="fr")
        if pathname == "/es":
            logger.info("No user headers found, showing login layout (language: Spanish).")
            return login_layout(lang="es")
    if pathname == "/" or pathname is None:
        logger.info("Showing homepage layout (default language: French).")
        return homepage_layout(user_headers, user_credentials, lang="fr")
    if pathname == "/fr":
        logger.info("Showing homepage layout (language: French).")
        return homepage_layout(user_headers, user_credentials, lang="fr")
    if pathname == "/es":
        logger.info("Showing homepage layout (language: Spanish).")
        return homepage_layout(user_headers, user_credentials, lang="es")
    else:
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
    app.run_server(host=args.host, port=args.port, debug=cfg.DEBUG, dev_tools_hot_reload=cfg.DEBUG)
