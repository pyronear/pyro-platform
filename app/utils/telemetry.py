# Copyright (C) 2020-2025, Pyronear.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

from typing import Any, Optional

import logging_config
from posthog import Posthog

import config as cfg

logger = logging_config.configure_logging(cfg.DEBUG, cfg.SENTRY_DSN)


class TelemetryClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self.is_enabled = isinstance(api_key, str)
        if self.is_enabled:
            self.ph_client = Posthog(project_api_key=api_key, host=cfg.POSTHOG_HOST)
            logger.info("Telemetry client initialized")

    def capture(self, event: str, distinct_id: str, properties: Optional[dict[str, Any]] = None) -> None:
        if self.is_enabled:
            self.ph_client.capture(distinct_id=distinct_id, event=event, properties=properties)

    def identify(self, distinct_id: str, properties: Optional[dict[str, Any]] = None) -> None:
        if self.is_enabled:
            self.ph_client.identify(distinct_id=distinct_id, properties=properties)


telemetry_client = TelemetryClient(api_key=cfg.POSTHOG_KEY)
