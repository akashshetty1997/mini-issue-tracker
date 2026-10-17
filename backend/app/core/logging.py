"""Structured (JSON) logging so log lines from many workers/replicas can be correlated."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.context import get_request_id

# Attributes every LogRecord has; anything else was passed via `extra=` and is logged too.
_RESERVED_ATTRS = frozenset(vars(logging.makeLogRecord({})))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        payload.update(
            {k: v for k, v in vars(record).items() if k not in _RESERVED_ATTRS and k != "message"}
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log would duplicate ours (added with the access-log middleware).
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
