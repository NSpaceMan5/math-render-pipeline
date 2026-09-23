from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from . import metadata, storage
from .evaluators import registry
from .models import RenderSpec
from .renderer import render

app = typer.Typer(add_completion=False)


@app.command("formulas")
def list_formulas():
    for name in registry.available():
        typer.echo(f"- {name}  defaults={registry.defaults(name)}")


@app.command("run")
def run(
    formula: str = typer.Option("polar_loom"),
    width: int = typer.Option(1600),
    height: int = typer.Option(1200),
    params: str = typer.Option("{}"),
):
    metadata.init_db()
    spec = RenderSpec(formula_id=formula, width=width, height=height, params=json.loads(params))
    result, full, prev = render(spec)
    result.storage_uri, result.preview_uri = storage.put(result.render_id, full, prev)
    metadata.insert(result)
    pq_path = metadata.write_parquet(result)
    typer.echo(json.dumps(result.model_dump(), indent=2))
    typer.echo(f"parquet: {pq_path}")


@app.command("batch")
def batch(csv: Path = typer.Option(..., exists=True)):
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


if __name__ == "__main__":
    app()
