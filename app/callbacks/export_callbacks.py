# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from io import StringIO

import logging_config
import pandas as pd
from dash import Input, Output, State, dcc
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from main import app
from translations import translate

import config as cfg
from services import get_client

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


@app.callback(
    Output("export-status-text", "children"),
    Output("export-trigger", "data"),
    Input("export-button", "n_clicks"),
    State("language", "data"),
    prevent_initial_call=True,
)
def trigger_export(n_clicks, lang):
    return translate("downloading_in_progress", lang), True


@app.callback(
    Output("export-download", "data"),
    Output("export-status-text-done", "children"),
    Input("export-trigger", "data"),
    State("export-start-date", "date"),
    State("export-end-date", "date"),
    State("user_token", "data"),
    State("language", "data"),
    State("api_cameras", "data"),
    prevent_initial_call=True,
)
def handle_export(trigger, start_date, end_date, user_token, lang, api_cameras):
    if not trigger or not user_token or not start_date or not end_date:
        raise PreventUpdate

    try:
        cameras_df = pd.read_json(StringIO(api_cameras), orient="split")
        cameras_df = cameras_df.rename(columns={"id": "camera_id_metadata"})
        cameras_df = cameras_df[["camera_id_metadata", "name", "angle_of_view", "lat", "lon"]]
    except Exception as e:
        return None, f"Erreur lecture des caméras : {e}"

    client = get_client(user_token)

    try:
        all_sequences = []
        current = pd.to_datetime(start_date)
        final = pd.to_datetime(end_date)

        while current <= final:
            response = client.fetch_sequences_from_date(current.strftime("%Y-%m-%d"), limit=100)
            daily_df = pd.DataFrame(response.json())
            if not daily_df.empty:
                all_sequences.append(daily_df)
            current += pd.Timedelta(days=1)

        if not all_sequences:
            return None, translate("no_data_found", lang)

        export_df = pd.concat(all_sequences, ignore_index=True)

        if "camera_id" in export_df.columns:
            export_df = export_df.merge(cameras_df, how="left", left_on="camera_id", right_on="camera_id_metadata")
            export_df = export_df.drop(columns=["camera_id", "camera_id_metadata"])
        else:
            return None, "camera_id column missing", False

        # Reorder columns
        ordered_columns = [
            "id",
            "name",
            "azimuth",
            "cone_angle",
            "started_at",
            "last_seen_at",
            "is_wildfire",
            "angle_of_view",
            "lat",
            "lon",
        ]
        # Keep only those columns that exist
        export_df = export_df[[col for col in ordered_columns if col in export_df.columns]]

        return dcc.send_data_frame(export_df.to_csv, "export.csv", index=False), translate("download_ready", lang)

    except Exception as e:
        return None, str(e)


@app.callback(Output("export-title", "children"), Input("language", "data"))
def update_export_title(lang):
    return translate("export_title", lang)


@app.callback(Output("export-start-date-label", "children"), Input("language", "data"))
def update_export_start_label(lang):
    return translate("start_date", lang)


@app.callback(Output("export-end-date-label", "children"), Input("language", "data"))
def update_export_end_label(lang):
    return translate("end_date", lang)


@app.callback(Output("export-button", "children"), Input("language", "data"))
def update_export_button_text(lang):
    return translate("prepare_archive", lang)
