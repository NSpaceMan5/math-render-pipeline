"""
Submit a render job to AWS Batch (spot queue).

Usage:
    python scripts/batch_submit.py --job-queue mrp-renderer \
        --job-definition mrp-renderer \
        --spec '{"formula_id":"polar_loom","width":800,"height":600,"params":{"rings":12}}'

    # Or a batch of specs from a file:
    python scripts/batch_submit.py --job-queue mrp-renderer \
        --job-definition mrp-renderer \
        --spec-file params/example_params.csv

Requires:
    boto3 installed
    AWS credentials with batch:SubmitJob
    IAM role with logs:CreateLogStream, s3:PutObject (see batch.tf)
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def _client(region: str | None = None):
    try:
        import boto3
    except ImportError:
        sys.exit('boto3 not installed. pip install "mrp[aws]"')
    return boto3.client("batch", region_name=region)


def _submit(client, queue: str, job_def: str, name: str,
            overrides: dict | None = None) -> str:
    kwargs = {"jobQueue": queue, "jobName": name, "jobDefinition": job_def}
    if overrides:
        kwargs["containerOverrides"] = overrides
    resp = client.submit_job(**kwargs)
    return resp["jobId"]


def _from_spec(spec: dict) -> dict:
    """Turn a spec dict into container overrides for the renderer job."""
    fid = spec["formula_id"]
    params = json.dumps(spec.get("params", {}))
    w = str(spec.get("width", 1600))
    h = str(spec.get("height", 1200))
    return {
        "command": [
            "mrp", "run",
            "--formula", fid,
            "--width", w,
            "--height", h,
            "--params", params,
        ]
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job-queue", required=True)
    ap.add_argument("--job-definition", required=True)
    ap.add_argument("--region", default=None)
    ap.add_argument("--spec", help="Single JSON spec")
    ap.add_argument("--spec-file",
                    help="CSV path; one job per row (formula_id,width,height,params_json)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jobs: list[dict] = []

    if args.spec:
        jobs.append(json.loads(args.spec))

    if args.spec_file:
        import csv
        with open(args.spec_file) as f:
            for row in csv.DictReader(f):
                jobs.append({
                    "formula_id": row["formula_id"],
                    "width": int(row["width"]),
                    "height": int(row["height"]),
                    "params": json.loads(row["params_json"])
                                  if row.get("params_json") else {},
                })

    if not jobs:
        print("no specs provided (use --spec or --spec-file)")
        return 2

    if args.dry_run:
        for i, spec in enumerate(jobs):
            overrides = _from_spec(spec)
            print(f"[dry-run {i}] command={overrides['command']}")
        return 0

    client = _client(args.region)
    ids: list[str] = []
    for i, spec in enumerate(jobs):
        name = f"mrp-render-{i}-{spec['formula_id']}"
        jid = _submit(client, args.job_queue, args.job_definition,
                      name, overrides=_from_spec(spec))
        ids.append(jid)
        print(f"[submit] {name}  ->  {jid}")

    print(f"\nsubmitted {len(ids)} jobs to {args.job_queue}")
    print("watch with:")
    print(f"  aws batch list-jobs --job-queue {args.job_queue} --job-status RUNNING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
