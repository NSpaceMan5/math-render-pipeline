from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mrp.models import RenderSpec
from mrp.renderer import render
from mrp import storage, metadata
from mrp.streaming import RenderProducer, RenderConsumer, event_from_result, TOPIC

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC_NAME = os.environ.get("KAFKA_TOPIC", TOPIC)
GROUP = os.environ.get("KAFKA_GROUP", "mrp-consumer-demo")


def main():
    metadata.init_db()
    producer = RenderProducer(BOOTSTRAP, TOPIC_NAME)
    df = pd.read_csv("params/example_params.csv")
    for _, row in df.iterrows():
        spec = RenderSpec(formula_id=row["formula_id"],
                          width=int(row["width"]), height=int(row["height"]),
                          params=json.loads(row["params_json"]))
        r, full, prev = render(spec)
        r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
        producer.publish(event_from_result(r).model_dump())
        print(f"[publish] {r.render_id}  {r.formula_id}  {r.runtime_ms} ms")
    producer.flush()
    print("\n[consumer] starting...")
    c = RenderConsumer(BOOTSTRAP, TOPIC_NAME, GROUP)
    n = c.run(max_messages=len(df))
    print(f"[consumer] done, {n} events ingested")


if __name__ == "__main__":
    main()
