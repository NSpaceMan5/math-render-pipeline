"""correlation_id contextvar.

Flow: producer creates it, embeds it in the event payload. Consumer reads
it back out and sets it again. Every log line and span within that request
carries the same id.
"""
from __future__ import annotations

import contextvars
import uuid

_cid: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def new_correlation_id() -> str:
    cid = uuid.uuid4().hex[:12]
    _cid.set(cid)
    return cid


def set_correlation_id(cid: str | None) -> None:
    _cid.set(cid)


def get_correlation_id() -> str | None:
    return _cid.get()
