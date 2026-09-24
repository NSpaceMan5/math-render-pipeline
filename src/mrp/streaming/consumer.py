"""
Consumer: reads `render.events`, writes to metadata.

Reliability contract
--------------------
* Idempotent on `render_id` — `insert_event()` uses ON CONFLICT DO NOTHING.
* Retry with exponential backoff on transient DB errors (max `max_retries`).
* Permanent failures go to `render.events.dlq` with error + attempt count.
* Malformed JSON is a poison pill — logged, sent to DLQ, offset committed,
  consumer continues.
* Manual offset commit — only after successful insert or DLQ publish.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import uuid

from .. import metadata

log = logging.getLogger("mrp.streaming.consumer")

try:
    from confluent_kafka import Consumer, KafkaError, Producer
    _HAS_KAFKA = True
except ImportError:
    Consumer = Producer = KafkaError = None
    _HAS_KAFKA = False


DLQ_SUFFIX = ".dlq"


class RenderConsumer:
    def __init__(
        self,
        bootstrap: str,
        topic: str,
        group_id: str,
        dlq_topic: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ):
        if not _HAS_KAFKA:
            raise RuntimeError("confluent-kafka not installed")

        self._topic = topic
        self._dlq_topic = dlq_topic or (topic + DLQ_SUFFIX)
        self._max_retries = max_retries
        self._backoff_base = backoff_base

        self._consumer = Consumer({
            "bootstrap.servers": bootstrap,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self._consumer.subscribe([topic])

        self._dlq = Producer({
            "bootstrap.servers": bootstrap,
            "enable.idempotence": True,
        })

        self._running = True
        self._stats = {"ok": 0, "dlq": 0, "retries": 0, "skipped": 0}

    def stop(self, *_):
        log.info("stop requested")
        self._running = False

    def _to_dlq(self, raw: bytes, error: str, attempts: int, cid: str) -> None:
        payload = {
            "correlation_id": cid,
            "original_topic": self._topic,
            "error": error,
            "attempts": attempts,
            "raw": raw.decode("utf-8", errors="replace"),
            "failed_at": time.time(),
        }
        self._dlq.produce(self._dlq_topic,
                          value=json.dumps(payload).encode("utf-8"))
        self._dlq.poll(0)
        self._stats["dlq"] += 1
        log.warning("cid=%s -> DLQ (%s, attempts=%d)", cid, error, attempts)

    def _insert_with_retry(self, event: dict, cid: str) -> None:
        last: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                metadata.insert_event(event)
                return
            except Exception as e:
                last = e
                self._stats["retries"] += 1
                wait = self._backoff_base * (2 ** (attempt - 1))
                log.warning("cid=%s attempt=%d/%d failed: %s (retry in %.2fs)",
                            cid, attempt, self._max_retries, e, wait)
                if attempt < self._max_retries:
                    time.sleep(wait)
        assert last is not None
        raise last

    def run(self, max_messages: int | None = None, timeout: float = 1.0) -> dict:
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

                cid = uuid.uuid4().hex[:12]
                raw = msg.value()

                try:
                    event = json.loads(raw.decode("utf-8"))
                    for req in ("render_id", "formula_id", "formula_hash",
                                "params_json", "width", "height",
                                "runtime_ms", "checksum", "storage_uri",
                                "preview_uri", "bytes_full", "bytes_preview"):
                        if req not in event:
                            raise ValueError(f"missing field: {req}")
                except Exception as e:
                    self._to_dlq(raw, f"parse: {e}", 1, cid)
                    self._consumer.commit(msg)
                    self._stats["skipped"] += 1
                    n += 1
                    if max_messages and n >= max_messages:
                        break
                    continue

                try:
                    self._insert_with_retry(event, cid)
                    self._consumer.commit(msg)
                    self._stats["ok"] += 1
                    log.info("cid=%s render_id=%s formula=%s",
                             cid, event["render_id"], event["formula_id"])
                except Exception as e:
                    self._to_dlq(raw, f"insert: {e}", self._max_retries, cid)
                    self._consumer.commit(msg)
                    self._stats["skipped"] += 1

                n += 1
                if max_messages and n >= max_messages:
                    break
        finally:
            self._consumer.close()
            self._dlq.flush(5.0)
        return self._stats


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
    topic     = os.environ.get("KAFKA_TOPIC", "render.events")
    group     = os.environ.get("KAFKA_GROUP", "mrp-consumer")
    dlq       = os.environ.get("KAFKA_DLQ_TOPIC")
    retries   = int(os.environ.get("KAFKA_MAX_RETRIES", "3"))

    c = RenderConsumer(bootstrap, topic, group,
                       dlq_topic=dlq, max_retries=retries)
    signal.signal(signal.SIGINT, c.stop)
    signal.signal(signal.SIGTERM, c.stop)

    log.info("consuming %s from %s (group=%s, dlq=%s)",
             topic, bootstrap, group, dlq or topic + DLQ_SUFFIX)
    stats = c.run()
    log.info("stats: %s", stats)
    sys.exit(0)


if __name__ == "__main__":
    main()
