# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from dash import dcc, html


def blinking_alarm_layout(user_token, api_cameras, lang="fr"):
    return html.Div(
        [
            dcc.Interval(id="blinking-alarm-interval", interval=500, n_intervals=0),
            html.Div(
                [
                    html.Img(
                        id="blinking-image",
                        style={
                            "max-width": "95%",  # Limit the width of the image to a % of the container
                            "max-height": "95%",  # Limit the height of the image to a % of the container
                            "object-fit": "contain",  # Preserve the aspect ratio of the image
                        },
                    )
                ],
                id="blinking-image-container",
            ),
        ]
    )
