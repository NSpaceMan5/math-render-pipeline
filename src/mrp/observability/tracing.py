"""OpenTelemetry tracing.

- If OTEL_EXPORTER_OTLP_ENDPOINT is set, spans are exported via OTLP/gRPC.
- Otherwise, a no-op tracer is used (safe to call `get_tracer()` and
  `traced()` unconditionally).

Usage:
    init_tracing(service_name="mrp-consumer")
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("consumer.process") as span:
        span.set_attribute("render_id", rid)
"""
from __future__ import annotations

import contextlib
import logging
import os

log = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    _HAS_OTEL = True
except ImportError:
    trace = None
    TracerProvider = None
    Resource = None
    BatchSpanProcessor = None
    OTLPSpanExporter = None
    _HAS_OTEL = False


_initialized = False


def init_tracing(service_name: str) -> None:
    """Initialise global tracer provider once per process."""
    global _initialized
    if _initialized:
        return
    if not _HAS_OTEL:
        log.info("opentelemetry not installed; tracing disabled")
        _initialized = True
        return

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        log.info("OTEL_EXPORTER_OTLP_ENDPOINT not set; tracing disabled")
        _initialized = True
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True
    log.info("tracing enabled -> %s (service=%s)", endpoint, service_name)


def get_tracer(name: str):
    if not _HAS_OTEL:
        class _Noop:
            @contextlib.contextmanager
            def start_as_current_span(self, *_, **__):
                yield None
        return _Noop()
    return trace.get_tracer(name)


@contextlib.contextmanager
def traced(name: str, attributes: dict | None = None):
    """Context manager wrapping `start_as_current_span` with attrs."""
    tracer = get_tracer("mrp")
    with tracer.start_as_current_span(name) as span:
        if span is not None and attributes:
            for k, v in attributes.items():
                try:
                    span.set_attribute(k, v)
                except Exception:
                    pass
        yield span
