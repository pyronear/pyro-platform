# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

import os
from dotenv import load_dotenv

# If there is an .env, load it
load_dotenv()

DEBUG: bool = os.environ.get('DEBUG', '') != 'False'
API_URL: str = os.environ.get('API_URL')
API_LOGIN: str = os.environ.get('API_LOGIN')
API_PWD: str = os.environ.get('API_PWD')
PYRORISK_FALLBACK: str = "https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/pyrorisk_20200901.json"
GEOJSON_FILE: str = 'https://github.com/pyronear/pyro-risks/releases/download/v0.1.0-data/departements.geojson'
