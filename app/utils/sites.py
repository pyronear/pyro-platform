# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import Any, Dict, Optional

import pandas as pd
import requests

import config as cfg


def get_token(api_url: str, login: str, pwd: str) -> str:
    response = requests.post(
        f"{api_url}/login/access-token",
        data={"username": login, "password": pwd},
    )
    if response.status_code != 200:
        raise ValueError(response.json()["detail"])
    return response.json()["access_token"]


def api_request(method_type: str, route: str, headers=Dict[str, str], payload: Optional[Dict[str, Any]] = None):
    kwargs = {"json": payload} if isinstance(payload, dict) else {}

    response = getattr(requests, method_type)(route, headers=headers, **kwargs)
    return response.json()


def get_sites(user_credentials):
    api_url = cfg.API_URL.split(".org")[0] + ".org"  # prevent last "/"
    superuser_login = user_credentials["username"]
    superuser_pwd = user_credentials["password"]

    superuser_auth = {
        "Authorization": f"Bearer {get_token(api_url, superuser_login, superuser_pwd)}",
        "Content-Type": "application/json",
    }
    api_sites = api_request("get", f"{api_url}/sites/", superuser_auth)
    return pd.DataFrame(api_sites)
