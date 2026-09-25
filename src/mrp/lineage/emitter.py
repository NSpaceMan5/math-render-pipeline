"""Thin wrapper around openlineage-python.

Design
------
- Enabled only when OPENLINEAGE_URL is set (e.g. http://marquez:5000).
- Missing package or unreachable server never raises: emit failures are
  logged at WARNING and swallowed. Lineage is best-effort.
- One emitter per process (singleton). Tests can reset it via
  `reset_emitter()`.

Event shape (OpenLineage spec):
    RunEvent(
        eventType=START | COMPLETE | FAIL,
        run=Run(runId=<hex>),
        job=Job(namespace="mrp", name="render" | "consume"),
        inputs=[Dataset(namespace="mrp", name=...)],
        outputs=[...],
        producer="mrp/0.1.0",
    )
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

log = logging.getLogger(__name__)

try:
    from openlineage.client import OpenLineageClient
    from openlineage.client.run import Dataset, Job, Run, RunEvent, RunState
    _HAS_OL = True
except ImportError:
    OpenLineageClient = None
    Dataset = Job = Run = RunEvent = RunState = None
    _HAS_OL = False


DEFAULT_NAMESPACE = "mrp"
PRODUCER = "mrp/0.1.0"


def _safe_uuid(s: str) -> str:
    """Coerce a string into a valid UUID string.

    OpenLineage validates runId as a UUID. If the caller passed a plain
    string (e.g. in tests, or an external id), derive a deterministic
    UUID5 from it instead of failing.
    """
    try:
        return str(uuid.UUID(str(s)))
    except (ValueError, AttributeError, TypeError):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, str(s)))


class LineageEmitter:
    def __init__(self, url: str | None = None,
                 namespace: str | None = None):
        self.url = url or os.environ.get("OPENLINEAGE_URL")
        self.namespace = (namespace
                          or os.environ.get("OPENLINEAGE_NAMESPACE")
                          or DEFAULT_NAMESPACE)
        self._client = None
        self._enabled = False

        if not self.url:
            log.debug("OPENLINEAGE_URL not set; lineage disabled")
            return
        if not _HAS_OL:
            log.warning("openlineage-python not installed; lineage disabled")
            return
        try:
            self._client = OpenLineageClient(url=self.url)
            self._enabled = True
            log.info("lineage enabled -> %s (ns=%s)", self.url, self.namespace)
        except Exception as e:
            log.warning("lineage client init failed: %s", e)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _emit(self, event_type, job_name: str, run_id: str,
              inputs: list[str], outputs: list[str]) -> None:
        if not self._enabled:
            return
        try:
            event = RunEvent(
                eventType=event_type,
                eventTime=datetime.now(timezone.utc).isoformat(),
                run=Run(runId=_safe_uuid(run_id)),
                job=Job(namespace=self.namespace, name=job_name),
                inputs=[Dataset(namespace=self.namespace, name=n)
                        for n in inputs],
                outputs=[Dataset(namespace=self.namespace, name=n)
                         for n in outputs],
                producer=PRODUCER,
            )
            self._client.emit(event)
        except Exception as e:
            log.warning("lineage emit failed: %s", e)

    # ---- render job -------------------------------------------------
    def emit_render_start(self, formula_id: str, spec_hash: str,
                          run_id: str) -> None:
        self._emit(RunState.START, "render", run_id,
                   inputs=[f"spec/{formula_id}/{spec_hash[:16]}"],
                   outputs=[])

    def emit_render_complete(self, formula_id: str, spec_hash: str,
                             render_id: str, storage_uri: str,
                             run_id: str) -> None:
        self._emit(RunState.COMPLETE, "render", run_id,
                   inputs=[f"spec/{formula_id}/{spec_hash[:16]}"],
                   outputs=[f"renders/{render_id}", storage_uri])

    def emit_render_fail(self, formula_id: str, spec_hash: str,
                         run_id: str) -> None:
        self._emit(RunState.FAIL, "render", run_id,
                   inputs=[f"spec/{formula_id}/{spec_hash[:16]}"],
                   outputs=[])

    # ---- consumer job -----------------------------------------------
    def emit_consumer_event(self, render_id: str, topic: str) -> None:
        self._emit(RunState.COMPLETE, "consume", str(uuid.uuid4()),
                   inputs=[f"topic/{topic}"],
                   outputs=[f"table/render_events/{render_id}"])


_singleton: LineageEmitter | None = None


def get_emitter() -> LineageEmitter:
    global _singleton
    if _singleton is None:
        _singleton = LineageEmitter()
    return _singleton


def reset_emitter() -> None:
    """For tests."""
    global _singleton
    _singleton = None
