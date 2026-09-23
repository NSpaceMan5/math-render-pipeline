from __future__ import annotations

import json
import logging
import os
import signal
import sys

from .. import metadata

log = logging.getLogger("mrp.streaming.consumer")

try:
    from confluent_kafka import Consumer, KafkaError
    _HAS_KAFKA = True
except ImportError:
    Consumer = None
    KafkaError = None
    _HAS_KAFKA = False


class RenderConsumer:
    def __init__(self, bootstrap: str, topic: str, group_id: str):
        if not _HAS_KAFKA:
            raise RuntimeError("confluent-kafka not installed")
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self._consumer.subscribe([topic])
        self._running = True

    def stop(self, *_):
        log.info("stop requested")
        self._running = False

    def run(self, max_messages: int | None = None, timeout: float = 1.0) -> int:
        metadata.init_db()
        n = 0
        try:
            while self._running:
                msg = self._consumer.poll(timeout)
                if msg is None:
                    if max_messages and n >= max_messages:
                        break
                    continue
                if msg.error():
                    if KafkaError and msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    raise RuntimeError(msg.error())
                event = json.loads(msg.value().decode("utf-8"))
                metadata.insert_event(event)
                self._consumer.commit(msg)
                n += 1
                log.info("ingested render_id=%s formula=%s",
                         event.get("render_id"), event.get("formula_id"))
                if max_messages and n >= max_messages:
                    break
        finally:
            self._consumer.close()
        return n


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
    topic     = os.environ.get("KAFKA_TOPIC", "render.events")
    group     = os.environ.get("KAFKA_GROUP", "mrp-consumer")

    c = RenderConsumer(bootstrap, topic, group)
    signal.signal(signal.SIGINT, c.stop)
    signal.signal(signal.SIGTERM, c.stop)
    log.info("consuming %s from %s (group=%s)", topic, bootstrap, group)
    n = c.run()
    log.info("consumed %d events", n)
    sys.exit(0)


if __name__ == "__main__":
    main()
