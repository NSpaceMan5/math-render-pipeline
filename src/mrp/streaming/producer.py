from __future__ import annotations

import json
import logging
from typing import Any

from ..observability import get_correlation_id, get_tracer, new_correlation_id

log = logging.getLogger(__name__)

try:
    from confluent_kafka import Producer
    _HAS_KAFKA = True
except ImportError:
    Producer = None
    _HAS_KAFKA = False


class RenderProducer:
    def __init__(self, bootstrap: str, topic: str, linger_ms: int = 5):
        if not _HAS_KAFKA:
            raise RuntimeError('confluent-kafka not installed; pip install "mrp[streaming]"')
        self._topic = topic
        self._producer = Producer({
            "bootstrap.servers": bootstrap,
            "linger.ms": linger_ms,
            "enable.idempotence": True,
        })

    def publish(self, event: dict[str, Any]) -> None:
        # ensure a correlation_id exists and rides along the payload
        if "correlation_id" not in event:
            event["correlation_id"] = get_correlation_id() or new_correlation_id()
        with get_tracer("mrp.producer").start_as_current_span("producer.publish") as span:
            if span is not None:
                try:
                    span.set_attribute("render_id", event["render_id"])
                    span.set_attribute("formula_id", event["formula_id"])
                except Exception:
                    pass
            key = str(event["render_id"]).encode("utf-8")
            value = json.dumps(event).encode("utf-8")
            self._producer.produce(self._topic, key=key, value=value,
                                   callback=self._on_delivery)
            self._producer.poll(0)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)

    @staticmethod
    def _on_delivery(err, msg):
        if err is not None:
            log.error("delivery failed: %s", err)
