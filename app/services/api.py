# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from functools import wraps
from typing import Callable, Dict

from pyroclient import Client

import config as cfg

__all__ = ["api_client", "call_api"]


if any(not isinstance(val, str) for val in [cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD]):
    raise ValueError("The following environment variables need to be set: 'API_URL', 'API_LOGIN', 'API_PWD'")

api_client = Client(cfg.API_URL, cfg.API_LOGIN, cfg.API_PWD)


def call_api(func: Callable, user_credentials: Dict[str, str]) -> Callable:
    """Decorator to call API method and renew the token if needed. Usage:

     result = call_api(my_func, user_credentials)(1, 2, verify=False)

    Instead of:

    response = my_func(1, verify=False)
    if response.status_code == 401:
        api_client.refresh_token(user_credentials["username"], user_credentials["password"])
    response = my_func(1, verify=False)
    result = response.json()

    Args:
        func: function that calls API method
        user_credentials: a dictionary with two keys, the username and password for authentication

    Returns: decorated function, to be called with positional and keyword arguments
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code == 401:
            api_client.refresh_token(user_credentials["username"], user_credentials["password"])
            response = func(*args, **kwargs)
        assert response.status_code // 100 == 2, response.text
        return response.json()

    return wrapper
