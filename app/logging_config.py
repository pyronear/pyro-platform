# Copyright (C) 2023-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import logging
import sys
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration


def configure_logging(debug: bool, sentry_dsn: Optional[str] = None):
    # Standard logging configuration
    handlers = [logging.StreamHandler(sys.stdout)]

    # Sentry integration with logging
    if sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )
        sentry_sdk.init(dsn=sentry_dsn, integrations=[sentry_logging])
        handlers.append(logging.StreamHandler(sys.stdout))  # Keep stdout handler for local debug

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    logger = logging.getLogger(__name__)
    return logger
