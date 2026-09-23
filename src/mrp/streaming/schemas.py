from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

TOPIC = "render.events"


class RenderEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    event_ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    render_id: str
    formula_id: str
    formula_hash: str
    params_json: dict[str, Any]
    width: int
    height: int
    runtime_ms: int
    checksum: str
    storage_uri: str
    preview_uri: str
    bytes_full: int
    bytes_preview: int
    ingest_source: str = "stream"


def event_from_result(r, ingest_source: str = "stream") -> RenderEvent:
    return RenderEvent(
        render_id=r.render_id,
        formula_id=r.formula_id,
        formula_hash=r.formula_hash,
        params_json=r.params_json,
        width=r.width,
        height=r.height,
        runtime_ms=r.runtime_ms,
        checksum=r.checksum,
        storage_uri=r.storage_uri,
        preview_uri=r.preview_uri,
        bytes_full=r.bytes_full,
        bytes_preview=r.bytes_preview,
        ingest_source=ingest_source,
    )
