# logging_config.py

import logging
import sys
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

def configure_logging(debug: bool, sentry_dsn: str = None):
    # Standard logging configuration
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Sentry integration with logging
    if sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[sentry_logging]
        )
        handlers.append(logging.StreamHandler(sys.stdout))  # Keep stdout handler for local debug

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )

    logger = logging.getLogger(__name__)
    return logger
