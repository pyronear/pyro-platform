# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import os
from typing import List, Optional

from dotenv import load_dotenv

# If there is an .env, load it
load_dotenv()

VERSION: str = "2.0.0"
DEBUG: bool = os.environ.get("DEBUG", "").lower() != "false"
API_URL: str = os.environ.get("API_URL", "")
API_LOGIN: str = os.environ.get("API_LOGIN", "")
API_PWD: str = os.environ.get("API_PWD", "")
LOGIN: bool = os.environ.get("LOGIN", "true").lower() == "true"
PYRORISK_FALLBACK: str = "https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/pyrorisk_20200901.json"
GEOJSON_FILE: str = "https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/departements.geojson"
AVAILABLE_LANGS: List[str] = ["fr", "es"]
DEFAULT_LANGUAGE: str = "fr"
CAMERA_INACTIVITY_THRESHOLD_MINUTES: int = 30
# Sentry
SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
SERVER_NAME: Optional[str] = os.getenv("SERVER_NAME")

# Safeguards
SAFE_DEV_MODE: Optional[str] = os.getenv("SAFE_DEV_MODE")

# App config variables
MAX_ALERTS_PER_EVENT = 10
CAM_OPENING_ANGLE = 87
CAM_RANGE_KM = 15

# Translation
TRANSLATION = {
    "alert_default": {
        "fr": {
            "show_hide_prediction": "Afficher / Cacher la prédiction",
            "download_image": "Télécharger l'image",
            "acknowledge_alert": "Acquitter l'alerte",
            "confirmation_modal_title": "Est-ce une fumée suspecte ?",
            "confirmation_modal_yes": "Oui, c'est une fumée",
            "confirmation_modal_no": "Non, c'est un faux positif",
            "confirmation_modal_cancel": "Annuler",
            "enlarge_map": "Agrandir la carte",
            "alert_information": "Information Alerte",
            "camera": "Caméra: ",
            "camera_location": "Position caméra: ",
            "detection_azimuth": "Azimuth de detection: ",
            "date": "Date: ",
            "map": "Carte",
            "no_alert_default_image": "./assets/images/no-alert-default.png",
        },
        "es": {
            "show_hide_prediction": "Mostrar / Ocultar la predicción",
            "download_image": "Descargar la imagen",
            "acknowledge_alert": "Descartar la alerta",
            "confirmation_modal_title": "¿Es un humo sospechoso?",
            "confirmation_modal_yes": "Sí, es un humo",
            "confirmation_modal_no": "No, es un falso positivo",
            "confirmation_modal_cancel": "Cancelar",
            "enlarge_map": "Ampliar el mapa",
            "alert_information": "Información sobre alerta",
            "camera": "Cámara: ",
            "camera_location": "Ubicación cámara: ",
            "detection_azimuth": "Azimut de detección: ",
            "date": "Fecha: ",
            "map": "Mapa",
            "no_alert_default_image": "./assets/images/no-alert-default-es.png",
        },
    },
    "history": {
        "fr": {
            "pick_date_msg": "Sélectionnez une date pour afficher l'historique des alertes",
            "breadcrumb": "Historique des alertes",
            "page_title": "Historique des alertes",
            "no_alert_history_image": "./assets/images/no-alert-history-fr.png",
        },
        "es": {
            "pick_date_msg": "Seleccione una fecha para visualizar el historial de alertas",
            "breadcrumb": "Histórico de las alertas",
            "page_title": "Histórico de las alertas",
            "no_alert_history_image": "./assets/images/no-alert-history-es.png",
        },
    },
}
