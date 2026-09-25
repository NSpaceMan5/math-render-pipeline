"""
Streaming throughput benchmark (no broker required).

Simulates the producer -> consumer path with an in-memory queue so we can
measure the pipeline overhead independently of Kafka.

For a real broker test, use `docker compose up -d redpanda` and set
KAFKA_BOOTSTRAP; the script switches to the actual producer/consumer if
the env var is present.

Usage:
    python -m benchmarks.bench_streaming --n 200
    KAFKA_BOOTSTRAP=localhost:9092 python -m benchmarks.bench_streaming --n 200
"""
from __future__ import annotations

import argparse
import os
import queue
import tempfile
import threading
import time
from pathlib import Path

from benchmarks.common import print_result, save, summarize

FORMULAS = [
    ("polar_loom",    {"rings": 6}),
    ("harmonic_grid", {"nx": 4, "ny": 3}),
    ("moire_grid",    {"f1": 10.0, "f2": 10.4}),
]


def _setup_env(tmp: Path) -> None:
    os.environ["POSTGRES_DSN"]  = f"sqlite:///{tmp / 'bench.sqlite'}"
    os.environ["USE_S3"]        = "false"
    os.environ["ARTIFACT_ROOT"] = str(tmp / "renders")
    os.environ["PARQUET_ROOT"]  = str(tmp / "parquet")


def _run_inmemory(n: int, width: int, height: int):
    """Simulate: producer renders -> queue -> consumer inserts."""
    from mrp import metadata, storage
    from mrp.models import RenderSpec
    from mrp.renderer import render
    from mrp.streaming import event_from_result

    metadata.init_db()
    q: queue.Queue[dict] = queue.Queue(maxsize=64)

    producer_times: list[int] = []
    consumer_times: list[int] = []
    rendered = 0
    consumed = 0

    def produce():
        nonlocal rendered
        for i in range(n):
            fid, params = FORMULAS[i % len(FORMULAS)]
            spec = RenderSpec(formula_id=fid, width=width, height=height,
                              params=params)
            t0 = time.perf_counter()
            r, full, prev = render(spec)
            r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
            ev = event_from_result(r).model_dump()
            producer_times.append(int((time.perf_counter() - t0) * 1000))
            q.put(ev)
            rendered += 1
        q.put(None)

    def consume():
        nonlocal consumed
        while True:
            item = q.get()
            if item is None:
                break
            t0 = time.perf_counter()
            metadata.insert_event(item)
            consumer_times.append(int((time.perf_counter() - t0) * 1000))
            consumed += 1

    t0 = time.perf_counter()
    tp = threading.Thread(target=produce)
    tc = threading.Thread(target=consume)
    tp.start()
    tc.start()
    tp.join()
    tc.join()
    wall = time.perf_counter() - t0

    return {
        "wall_seconds": round(wall, 3),
        "produced": rendered,
        "consumed": consumed,
        "throughput_rps": round(consumed / wall, 2),
        "producer_stats": summarize(producer_times),
        "consumer_stats": summarize(consumer_times),
    }


def _run_kafka(bootstrap: str, n: int, width: int, height: int):
    """Real broker path — requires `docker compose up -d redpanda`."""
    from mrp import metadata, storage
    from mrp.models import RenderSpec
    from mrp.renderer import render
    from mrp.streaming import TOPIC, RenderConsumer, RenderProducer, event_from_result

    metadata.init_db()
    producer = RenderProducer(bootstrap, TOPIC)

    producer_times: list[int] = []
    t0 = time.perf_counter()
    for i in range(n):
        fid, params = FORMULAS[i % len(FORMULAS)]
        spec = RenderSpec(formula_id=fid, width=width, height=height, params=params)
        r, full, prev = render(spec)
        r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
        producer.publish(event_from_result(r).model_dump())
        producer_times.append(r.runtime_ms)
    producer.flush(10.0)
    produce_wall = time.perf_counter() - t0

    consumer = RenderConsumer(bootstrap, TOPIC, "bench-group",
                              dlq_topic=TOPIC + ".dlq", max_retries=2)
    t1 = time.perf_counter()
    stats = consumer.run(max_messages=n, timeout=5.0)
    consume_wall = time.perf_counter() - t1

    return {
        "produce_wall_seconds": round(produce_wall, 3),
        "consume_wall_seconds": round(consume_wall, 3),
        "producer_rps": round(n / produce_wall, 2),
        "consumer_rps": round(stats["ok"] / consume_wall, 2) if consume_wall > 0 else 0,
        "producer_stats": summarize(producer_times),
        "consumer_ok": stats["ok"],
        "consumer_dlq": stats["dlq"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--width", type=int, default=400)
    ap.add_argument("--height", type=int, default=300)
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="mrp_stream_"))
    _setup_env(tmp)

    bootstrap = os.environ.get("KAFKA_BOOTSTRAP")
    mode = "kafka" if bootstrap else "inmemory"

    if mode == "kafka":
        result = _run_kafka(bootstrap, args.n, args.width, args.height)
    else:
        result = _run_inmemory(args.n, args.width, args.height)

    payload = {"benchmark": "streaming", "mode": mode, "n": args.n,
               "width": args.width, "height": args.height, **result}
    save("streaming", payload)
    print_result("streaming", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
