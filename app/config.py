# Copyright (C) 2020-2022, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import os
from typing import Optional

from dotenv import load_dotenv

# If there is an .env, load it
load_dotenv()

VERSION: str = "0.1.2.dev0"
DEBUG: bool = os.environ.get("DEBUG", "").lower() != "false"
API_URL: str = os.environ.get("API_URL", "")
API_LOGIN: str = os.environ.get("API_LOGIN", "")
API_PWD: str = os.environ.get("API_PWD", "")
PYRORISK_FALLBACK: str = "https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/pyrorisk_20200901.json"
GEOJSON_FILE: str = "https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/departements.geojson"
# Sentry
SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
SERVER_NAME: Optional[str] = os.getenv("SERVER_NAME")
