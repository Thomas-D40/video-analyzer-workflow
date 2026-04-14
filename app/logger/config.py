"""
Logging configuration.

Call configure_logging() once at application startup (app/api.py lifespan).
Reads LOG_LEVEL from config and attaches the JSON formatter to the root logger.
"""
import logging
import sys

from .formatter import JSONFormatter


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure the root logger with JSON output.

    Args:
        log_level: Logging level string ("DEBUG", "INFO", "WARNING", "ERROR").
                   Defaults to "INFO".
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)

    # Replace any existing handlers (e.g. FastAPI's default basicConfig)
    root.handlers.clear()
    root.addHandler(handler)
