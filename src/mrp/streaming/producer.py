from __future__ import annotations

import json
import logging
from typing import Any

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
