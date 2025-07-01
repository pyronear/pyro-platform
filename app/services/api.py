# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from urllib.parse import urljoin

import requests
from pyroclient import Client

import config as cfg

__all__ = ["get_client", "get_token"]


if any(not isinstance(val, str) for val in [cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD]):
    raise ValueError("The following environment variables need to be set: 'API_URL', 'API_LOGIN', 'API_PWD'")


def get_token(login: str, passwrd: str) -> str:
    """Authenticate with API and return access token"""
    response = requests.post(
        urljoin(cfg.API_URL, "/api/v1/login/creds"),
        data={"username": login, "password": passwrd},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_client(access_token: str) -> Client:
    """Return a per-user authenticated API client"""
    return Client(access_token, cfg.API_URL)
