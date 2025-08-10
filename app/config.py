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

# Stream server
MEDIAMTX_SERVER_URL = os.environ.get("MEDIAMTX_SERVER_URL", "")

# App config variables
MAX_ALERTS_PER_EVENT = 10
CAM_OPENING_ANGLE = 87
CAM_RANGE_KM = 30
