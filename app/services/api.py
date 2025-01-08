# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from urllib.parse import urljoin

import requests
from pyroclient import Client

import config as cfg

__all__ = ["api_client", "get_token"]


if any(not isinstance(val, str) for val in [cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD]):
    raise ValueError("The following environment variables need to be set: 'API_URL', 'API_LOGIN', 'API_PWD'")


def get_token(login: str, passwrd: str):
    access_token = requests.post(
        urljoin(cfg.API_URL, "/api/v1/login/creds"),
        data={"username": login, "password": passwrd},
        timeout=5,
    ).json()["access_token"]

    return access_token


access_token = get_token(cfg.API_LOGIN, cfg.API_PWD)

api_client = Client(access_token, cfg.API_URL)
