"""
JSON log formatter for structured logging.

Produces one JSON line per log event, with video_id as the first field
when available. Non-serializable values are safely converted to str.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any


# Standard LogRecord attributes that must not be echoed back in the JSON output
_RESERVED_ATTRS = frozenset({
    'args', 'created', 'exc_info', 'exc_text', 'filename', 'funcName',
    'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
    'msg', 'name', 'pathname', 'process', 'processName', 'relativeCreated',
    'stack_info', 'thread', 'threadName',
})

# Fields written explicitly — skip them when iterating record.__dict__
_EXPLICIT_FIELDS = frozenset({'video_id', 'timestamp', 'level', 'module', 'message'})


def _safe_serialize(value: Any) -> Any:
    """Return value as-is if JSON-serializable, else convert to str."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON.

    Output order:
        video_id (if present), timestamp, level, module, message, extra fields...

    Stack traces are intentionally omitted to avoid leaking sensitive data.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, Any] = {}

        # video_id as first field when present (required by spec)
        video_id = getattr(record, 'video_id', None)
        if video_id is not None:
            log_dict['video_id'] = _safe_serialize(video_id)

        # Core fields
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        log_dict['timestamp'] = ts.strftime('%Y-%m-%dT%H:%M:%S.') + f'{int(record.msecs):03d}Z'
        log_dict['level'] = record.levelname
        log_dict['module'] = record.module
        log_dict['message'] = record.getMessage()

        # Extra context fields (step, args_count, tokens_used, …)
        for key, value in record.__dict__.items():
            if (
                key not in _RESERVED_ATTRS
                and key not in _EXPLICIT_FIELDS
                and not key.startswith('_')
            ):
                log_dict[key] = _safe_serialize(value)

        # No exc_info / stack_trace — intentionally excluded
        return json.dumps(log_dict, ensure_ascii=False)
