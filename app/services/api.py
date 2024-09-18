# Copyright (C) 2020-2024, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import Optional
from urllib.parse import urljoin

import requests
from pyroclient import Client

import config as cfg

__all__ = ["instantiate_token"]


def instantiate_token(login: Optional[str] = None, passwrd: Optional[str] = None):
    if not cfg.LOGIN:
        if any(not isinstance(val, str) for val in [cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD]):
            raise ValueError("The following environment variables need to be set: 'API_URL', 'API_LOGIN', 'API_PWD'")
        else:
            access_token = requests.post(
                urljoin(cfg.API_URL, "/api/v1/login/creds"),
                data={"username": cfg.API_LOGIN, "password": cfg.API_PWD},
                timeout=5,
            ).json()["access_token"]

            api_client = Client(access_token, cfg.API_URL)
            return api_client

    access_token = requests.post(
        urljoin(cfg.API_URL, "/api/v1/login/creds"),
        data={"username": login, "password": passwrd},
        timeout=5,
    ).json()["access_token"]

    api_client = Client(access_token, cfg.API_URL)
    return api_client
