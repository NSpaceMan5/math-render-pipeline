# Spot renderer on AWS Batch

Renders scale to zero when idle, run on **spot** capacity, and survive
interruptions via job retries. Roughly **-70%** versus on-demand.

## Why spot

The render workload is:

- **Stateless** — every render reads a spec, writes a PNG + metadata, exits.
- **Interruptible** — a killed job can be resubmitted; `render_id` is
  deterministic so re-rendering is idempotent.
- **Batch-friendly** — no live connections, no long-running state.

That is exactly what spot is designed for.

## Architecture
batch_submit.py ──▶ AWS Batch queue ──▶ SPOT compute env ──▶ container
│
├──▶ S3 (PNG)
├──▶ Postgres / RDS (metadata)
└──▶ CloudWatch Logs

The compute environment:

| Property | Value | Why |
|---|---|---|
| Type | `SPOT` | cost |
| Allocation | `SPOT_CAPACITY_OPTIMIZED` | pick least-interrupted pool |
| Instance families | c6i / c6a / c5 / m6i / m6a / m5 | flexibility → fewer interruptions |
| min_vcpus | 0 | scale to zero |
| max_vcpus | 64 | blast-radius cap |
| Retry | 3 attempts | survive spot reclaim |
| Timeout | 3600s | kill runaway renders |

## Cost estimate

| Instance | On-demand | Spot | Saving |
|---|---|---|---|
| c6i.large | $0.085/hr | ~$0.025/hr | **-71%** |
| c5.large  | $0.085/hr | ~$0.026/hr | **-69%** |
| m6i.large | $0.096/hr | ~$0.030/hr | **-69%** |

At 1000 renders × 2 s each = 0.56 CPU-hours:

| Scenario | Compute cost per 1000 renders |
|---|---|
| On-demand | $0.048 |
| Spot | $0.014 |

The cost model in `benchmarks/cost_model.py` uses these numbers.

## Deploy

```bash
cd infra/terraform/aws
terraform init
terraform apply \
  -var db_password=xxx \
  -var renderer_image=<acct>.dkr.ecr.<region>.amazonaws.com/mrp-batch:latest
Outputs:

batch_job_queue      = "mrp-renderer"
batch_job_definition = "mrp-renderer"
db_dsn_secret_arn    = "arn:aws:secretsmanager:...:secret:mrp/postgres-dsn-xxxx"
Build & push the image
bash
docker build -f infra/docker/Dockerfile.batch -t mrp-batch:latest .

aws ecr create-repository --repository-name mrp-batch --region us-east-1
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <acct>.dkr.ecr.us-east-1.amazonaws.com

docker tag mrp-batch:latest <acct>.dkr.ecr.us-east-1.amazonaws.com/mrp-batch:latest
docker push <acct>.dkr.ecr.us-east-1.amazonaws.com/mrp-batch:latest
Submit jobs
bash
# single spec
python scripts/batch_submit.py \
  --job-queue mrp-renderer \
  --job-definition mrp-renderer \
  --spec '{"formula_id":"polar_loom","width":800,"height":600,"params":{"rings":12}}'

# a batch from CSV
python scripts/batch_submit.py \
  --job-queue mrp-renderer \
  --job-definition mrp-renderer \
  --spec-file params/example_params.csv

# dry run — prints the container command without submitting
python scripts/batch_submit.py \
  --job-queue mrp-renderer --job-definition mrp-renderer \
  --spec-file params/example_params.csv --dry-run
Monitor
bash
aws batch list-jobs --job-queue mrp-renderer --job-status RUNNING
aws batch list-jobs --job-queue mrp-renderer --job-status SUCCEEDED
aws logs tail /aws/batch/mrp --follow
Handle spot interruptions
The job definition retries up to 3 times on Host EC2* status reasons
(spot reclaim). Combined with render_id determinism:

Killed job → AWS Batch requeues.

Retry runs mrp run again with the same spec.

formula_hash is identical → PNG bytes are identical → insert_event
dedups on render_id.

No duplicate artifacts, no wasted computation.

Tear down
bash
terraform destroy -var db_password=xxx
