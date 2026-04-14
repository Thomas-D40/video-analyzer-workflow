"""
Structured logger package.

Usage:
    from app.logger import get_logger

    logger = get_logger(__name__)
    logger.info("step_start", video_id=video_id, step="transcript_extraction")
    logger.debug("source_score", video_id=video_id, score=0.85, source="pubmed")
    logger.warning("fallback_triggered", video_id=video_id, service="arxiv")
    logger.error("step_failed", video_id=video_id, step="argument_extraction", detail=str(e))
"""
import logging
from typing import Any


class ContextLogger:
    """
    Thin wrapper around a standard Logger that accepts keyword arguments
    as structured JSON context fields (passed via logging's `extra` mechanism).

    Error logs never include exc_info to avoid leaking stack traces with
    sensitive data (e.g. API keys visible in tracebacks).
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._logger.debug(msg, extra=kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._logger.info(msg, extra=kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._logger.warning(msg, extra=kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        # exc_info deliberately omitted — no stack traces in ERROR logs
        self._logger.error(msg, extra=kwargs)

    def isEnabledFor(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    @property
    def name(self) -> str:
        return self._logger.name


def get_logger(name: str) -> ContextLogger:
    """
    Return a ContextLogger for the given module name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        ContextLogger instance.
    """
    return ContextLogger(logging.getLogger(name))
