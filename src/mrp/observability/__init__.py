"""
Observability primitives: correlation_id context, JSON logs,
Prometheus metrics, OpenTelemetry tracing.

Import order matters little — each submodule is independent.
"""
from .context import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from .logging import JsonFormatter, setup_logging
from .metrics import (
    consumer_events_total,
    consumer_processing_seconds,
    consumer_retries_total,
    dlq_publish_total,
    observe_consumer_event,
    observe_render,
    render_bytes,
    render_duration_seconds,
    render_total,
    start_metrics_server,
)
from .tracing import get_tracer, init_tracing, traced

__all__ = [
    "JsonFormatter",
    "consumer_events_total",
    "consumer_processing_seconds",
    "consumer_retries_total",
    "dlq_publish_total",
    "get_correlation_id",
    "get_tracer",
    "init_tracing",
    "new_correlation_id",
    "observe_consumer_event",
    "observe_render",
    "render_bytes",
    "render_duration_seconds",
    "render_total",
    "set_correlation_id",
    "setup_logging",
    "start_metrics_server",
    "traced",
]
