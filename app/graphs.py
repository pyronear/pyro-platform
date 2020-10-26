"""The following file is dedicated to storing graphs functions.

These graphs will be called from homepage.py
in order to plot them right under the homepage map
"""

import plotly.graph_objects as go
import numpy as np


def generate_meteo_fig():
    np.random.seed(1)

    N = 100
    random_x = np.linspace(0, 1, N)
    random_y0 = np.random.randn(N) + 5
    random_y1 = np.random.randn(N)
    random_y2 = np.random.randn(N) - 5

    # Create traces
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=random_x, y=random_y0,
                             mode='lines',
                             name='lines'))
    fig.add_trace(go.Scatter(x=random_x, y=random_y1,
                             mode='lines+markers',
                             name='lines+markers'))
    fig.add_trace(go.Scatter(x=random_x, y=random_y2,
                             mode='markers', name='markers'))

    # updating layout to get small margins and reposition legend
    fig.update_layout(margin=dict(l=20,
                                  r=20,
                                  b=20,
                                  t=20),
                      legend=dict(yanchor="top",
                                  y=0.99,
                                  xanchor="left",
                                  x=0.01)
                      )

    return fig


def generate_second_indicator_fig():
    fig = go.Figure()
    return fig


def generate_third_indicator_fig():
    fig = go.Figure()
    return fig
