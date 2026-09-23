from __future__ import annotations
from datetime import datetime, timedelta
import sys
sys.path.insert(0, "/opt/airflow/src")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

from mrp.models import RenderSpec
from mrp.renderer import render
from mrp import storage, metadata

DAG_ID = "math_render_pipeline"
default_args = {"retries": 2, "retry_delay": timedelta(minutes=1)}

SWEEP = [
    {"formula_id": "polar_loom",    "params": {"rings": 16, "twist": 1.8, "decay": 2.4, "fold": 1.0}},
    {"formula_id": "polar_loom",    "params": {"rings": 28, "twist": 2.7, "decay": 2.1, "fold": 1.15}},
    {"formula_id": "polar_loom",    "params": {"rings": 48, "twist": 3.6, "decay": 1.8, "fold": 1.3}},
    {"formula_id": "harmonic_grid", "params": {"nx": 6, "ny": 4, "phase": 0.0, "skew": 0.0, "mix": 0.5}},
    {"formula_id": "harmonic_grid", "params": {"nx": 10, "ny": 6, "phase": 0.3, "skew": 0.4, "mix": 0.7}},
]

def _render_sweep():
    metadata.init_db()
    for item in SWEEP:
        spec = RenderSpec(formula_id=item["formula_id"], width=1600, height=1200,
                          params=item["params"])
        r, full, prev = render(spec)
        r.storage_uri, r.preview_uri = storage.put(r.render_id, full, prev)
        metadata.insert(r)
        metadata.write_parquet(r)

with DAG(
    dag_id=DAG_ID, schedule="@daily",
    start_date=datetime(2025, 1, 1), catchup=False,
    default_args=default_args, tags=["mrp", "render"],
) as dag:
    t_sweep = PythonOperator(task_id="render_sweep", python_callable=_render_sweep)
    t_dq    = BashOperator(task_id="data_quality",
                           bash_command="cd /opt/airflow && python data_quality/run_checks.py")
    t_dbt   = BashOperator(task_id="dbt_run",
                           bash_command="cd /opt/airflow/dbt && dbt run --profiles-dir .")
    t_sweep >> t_dq >> t_dbt
