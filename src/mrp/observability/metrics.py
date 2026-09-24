"""Prometheus metrics.

Metrics are module-level singletons from `prometheus_client`. Calling
`observe_render` / `observe_consumer_event` updates them. `start_metrics_server`
runs the HTTP exporter in a background thread — call it once per process.
"""
from __future__ import annotations

import logging
import threading

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
render_total = Counter(
    "mrp_render_total",
    "Number of renders by formula and status.",
    labelnames=("formula_id", "status"),
)

render_duration_seconds = Histogram(
    "mrp_render_duration_seconds",
    "Wall-clock render duration in seconds.",
    labelnames=("formula_id",),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)

render_bytes = Histogram(
    "mrp_render_bytes",
    "Output size in bytes by formula and kind (full|preview).",
    labelnames=("formula_id", "kind"),
    buckets=(1e3, 1e4, 5e4, 1e5, 5e5, 1e6, 5e6, 1e7),
)


def observe_render(formula_id: str, runtime_ms: int,
                   bytes_full: int, bytes_preview: int,
                   status: str = "ok") -> None:
    render_total.labels(formula_id=formula_id, status=status).inc()
    render_duration_seconds.labels(formula_id=formula_id).observe(runtime_ms / 1000.0)
    render_bytes.labels(formula_id=formula_id, kind="full").observe(bytes_full)
    render_bytes.labels(formula_id=formula_id, kind="preview").observe(bytes_preview)


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------
consumer_events_total = Counter(
    "mrp_consumer_events_total",
    "Events processed by the consumer.",
    labelnames=("status",),   # ok | dlq | skipped
)

consumer_retries_total = Counter(
    "mrp_consumer_retries_total",
    "Total insert retries triggered by transient errors.",
)

consumer_processing_seconds = Histogram(
    "mrp_consumer_processing_seconds",
    "Time spent processing each event (insert path only).",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5),
)

dlq_publish_total = Counter(
    "mrp_dlq_publish_total",
    "Messages published to the DLQ.",
    labelnames=("reason",),   # parse | insert
)

# Last observed message age. Populated by the consumer when it can read
# the record timestamp. Grafana can alert on this directly.
consumer_last_event_age_seconds = Gauge(
    "mrp_consumer_last_event_age_seconds",
    "Age of the most recently processed event.",
)


def observe_consumer_event(status: str) -> None:
    consumer_events_total.labels(status=status).inc()


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
_server_started = False
_lock = threading.Lock()


def start_metrics_server(port: int = 9100, addr: str = "0.0.0.0") -> None:
    """Start the Prometheus HTTP exporter in a background thread.

    Safe to call multiple times; only the first call has an effect.
    """
    global _server_started
    with _lock:
        if _server_started:
            return
        try:
            start_http_server(port, addr=addr)
            _server_started = True
            log.info("metrics server listening on %s:%d", addr, port)
        except OSError as e:
            log.warning("metrics server failed to bind: %s", e)
