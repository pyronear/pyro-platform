# Copyright (C) 2020-2022, Pyronear.

# This program is licensed under the Apache License version 2.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0.txt> for full license details.

import config as cfg
from pyroclient import Client

__all__ = ["api_client"]


if any(not isinstance(val, str) for val in [cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD]):
    raise ValueError("The following environment variables need to be set: 'API_URL', 'API_LOGIN', 'API_PWD'")

api_client = Client(cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD)
