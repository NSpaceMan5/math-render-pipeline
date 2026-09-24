from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import typer

from . import metadata, storage
from .evaluators import registry
from .models import RenderSpec
from .observability import init_tracing, setup_logging
from .renderer import render

app = typer.Typer(add_completion=False)


def _bootstrap_observability() -> None:
    setup_logging()
    init_tracing("mrp-cli")


def _maybe_publish(result) -> None:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP")
    if not bootstrap:
        return
    try:
        from .streaming import TOPIC, RenderProducer, event_from_result
    except Exception:
        return
    topic = os.environ.get("KAFKA_TOPIC", TOPIC)
    producer = RenderProducer(bootstrap, topic)
    producer.publish(event_from_result(result).model_dump())
    producer.flush()


@app.command("formulas")
def list_formulas():
    _bootstrap_observability()
    for name in registry.available():
        typer.echo(f"- {name}  defaults={registry.defaults(name)}")


@app.command("run")
def run(
    formula: str = typer.Option("polar_loom"),
    width: int = typer.Option(1600),
    height: int = typer.Option(1200),
    params: str = typer.Option("{}"),
    stream: bool = typer.Option(False),
):
    _bootstrap_observability()
    metadata.init_db()
    spec = RenderSpec(formula_id=formula, width=width, height=height,
                      params=json.loads(params))
    result, full, prev = render(spec)
    result.storage_uri, result.preview_uri = storage.put(result.render_id, full, prev)
    metadata.insert(result)
    pq_path = metadata.write_parquet(result)
    typer.echo(json.dumps(result.model_dump(), indent=2))
    typer.echo(f"parquet: {pq_path}")
    if stream:
        os.environ.setdefault("KAFKA_BOOTSTRAP", "localhost:9092")
        _maybe_publish(result)
        typer.echo("published to render.events")


@app.command("batch")
def batch(csv: Path = typer.Option(..., exists=True)):
    _bootstrap_observability()
    metadata.init_db()
    df = pd.read_csv(csv)
    for _, row in df.iterrows():
        spec = RenderSpec(
            formula_id=row["formula_id"],
            width=int(row["width"]),
            height=int(row["height"]),
            params=json.loads(row["params_json"]) if pd.notna(row["params_json"]) else {},
        )
        r, full, prev = render(spec)
        r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
        metadata.insert(r)
        metadata.write_parquet(r)
        typer.echo(f"[ok] {r.render_id}  {r.runtime_ms} ms  {r.bytes_full} B")


@app.command("produce")
def produce(
    csv: Path = typer.Option(..., exists=True),
    bootstrap: str = typer.Option("localhost:9092", envvar="KAFKA_BOOTSTRAP"),
    topic: str = typer.Option("render.events", envvar="KAFKA_TOPIC"),
):
    _bootstrap_observability()
    from .streaming import RenderProducer, event_from_result
    metadata.init_db()
    producer = RenderProducer(bootstrap, topic)
    df = pd.read_csv(csv)
    for _, row in df.iterrows():
        spec = RenderSpec(
            formula_id=row["formula_id"],
            width=int(row["width"]),
            height=int(row["height"]),
            params=json.loads(row["params_json"]) if pd.notna(row["params_json"]) else {},
        )
        r, full, prev = render(spec)
        r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
        producer.publish(event_from_result(r).model_dump())
        typer.echo(f"[publish] {r.render_id}  {r.formula_id}")
    producer.flush()
    typer.echo("done")


@app.command("consume")
def consume(
    bootstrap: str = typer.Option("localhost:9092", envvar="KAFKA_BOOTSTRAP"),
    topic: str = typer.Option("render.events", envvar="KAFKA_TOPIC"),
    group: str = typer.Option("mrp-consumer", envvar="KAFKA_GROUP"),
    max_messages: int = typer.Option(0),
):
    _bootstrap_observability()
    from .streaming import RenderConsumer
    c = RenderConsumer(bootstrap, topic, group)
    n = c.run(max_messages=max_messages or None)
    typer.echo(f"consumed {n} events")


if __name__ == "__main__":
    app()
