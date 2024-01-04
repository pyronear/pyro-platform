# Copyright (C) 2020-2023, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import callbacks.data_callbacks
import callbacks.display_callbacks  # noqa: F401
from dash import html
from dash.dependencies import Input, Output, State
from layouts.main_layout import get_main_layout

import config as cfg
from app import app
from pages.homepage import homepage_layout
from pages.login import login_layout

# Set the app layout
app.layout = get_main_layout()


# Manage Pages
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname"), Input("user_headers", "data")],
    State("user_credentials", "data"),
)
def display_page(pathname, user_headers, user_credentials):
    if user_headers is None:
        return login_layout()
    if pathname == "/" or pathname is None:
        return homepage_layout(user_headers, user_credentials)
    else:
        return html.Div([html.P("Unable to find this page.", className="alert alert-warning")])


# ----------------------------------------------------------------------------------------------------------------------
# RUNNING THE WEB-APP SERVER

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Pyronear web-app", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host of the server")
    parser.add_argument("--port", type=int, default=8050, help="Port to run the server on")
    args = parser.parse_args()

    app.run_server(host=args.host, port=args.port, debug=cfg.DEBUG, dev_tools_hot_reload=cfg.DEBUG)
