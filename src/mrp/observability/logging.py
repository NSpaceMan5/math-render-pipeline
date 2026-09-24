"""JSON logging with correlation_id.

Every record is emitted as a single-line JSON object. Fields:
    ts           ISO-8601 UTC
    level        INFO / WARNING / ERROR
    logger       logger name
    msg          the log message
    correlation_id   from contextvar (may be null)
    extras       any additional fields passed via `extra={"extra": {...}}`
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

from .context import get_correlation_id

_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc)
                          .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        cid = get_correlation_id()
        if cid:
            payload["correlation_id"] = cid

        # extras: anything not in the reserved set
        for k, v in record.__dict__.items():
            if k in _RESERVED or k.startswith("_"):
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except (TypeError, ValueError):
                payload[k] = repr(v)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str | None = None) -> None:
    """Configure root logging to emit one JSON object per line.

    Safe to call more than once — replaces handlers.
    """
    lvl = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    root.setLevel(lvl)
    for h in list(root.handlers):
        root.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root.addHandler(h)

    # quiet noisy libs
    for name in ("confluent_kafka", "urllib3", "botocore", "boto3"):
        logging.getLogger(name).setLevel("WARNING")
