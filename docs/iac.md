# Infrastructure as Code

Two clouds, one interface. The application reads everything from env vars,
so the only thing that changes between AWS and GCP is the Terraform
directory and the values you plug into `.env`.

    infra/terraform/
    ├── shared/          # conventions, backend example
    ├── aws/             # S3 + RDS + CloudWatch
    └── gcp/             # GCS + Cloud SQL + Secret Manager

## Resource mapping

| Capability | AWS | GCP |
|---|---|---|
| Object storage | S3 | Cloud Storage |
| Tiered archive | `STANDARD_IA → GLACIER_IR` | `NEARLINE → COLDLINE → ARCHIVE` |
| Managed Postgres | RDS `db.t4g.micro` | Cloud SQL `db-f1-micro` |
| Encryption | SSE-S3 (AES256) | Google-managed |
| Secret storage | Secrets Manager | Secret Manager |
| Logs | CloudWatch Logs | Cloud Logging |
| IAM for batch | IAM role + policy | Service account |
| Serverless batch | AWS Batch | Cloud Run Jobs |

## Usage

**AWS**

    cd infra/terraform/aws
    terraform init
    terraform plan  -var db_password=xxx
    terraform apply -var db_password=xxx

Outputs: `bucket_name`, `db_endpoint`, `connection_hint`.

**GCP**

    cd infra/terraform/gcp
    terraform init
    terraform plan  -var project_id=my-gcp-project -var db_password=xxx
    terraform apply -var project_id=my-gcp-project -var db_password=xxx

Outputs: `bucket_name`, `db_instance`, `db_connection_name`,
`batch_service_account`, `connection_hint`.

## Application wiring

After `apply`, populate `.env` from the outputs:

    # AWS
    POSTGRES_DSN=postgresql://mrp:<pw>@<db_endpoint>/mrp
    S3_BUCKET=<bucket_name>
    USE_S3=true

    # GCP
    POSTGRES_DSN=postgresql://mrp:<pw>@<db_connection_name>/mrp
    S3_BUCKET=<bucket_name>          # works with GCS via S3-compatible HMAC
    USE_S3=true

The code path is identical; only the endpoint differs.

## Cost

Estimated monthly cost for a portfolio deployment (idle DB, tiered storage
for ~50 GB of renders):

| Cloud | Compute | DB | Storage | Total |
|---|---|---|---|---|
| AWS | $0 (event-driven) | $13 (db.t4g.micro) | $1.15 (Glacier IR) | **~$14/mo** |
| GCP | $0 | $9.5 (db-f1-micro) | $1.20 (COLDLINE) | **~$11/mo** |

Numbers from public list prices, 2026. Adjust for your region.

## Backend

Both directories support remote state. Copy `shared/backend.tf.example`
into `aws/backend.tf` or `gcp/backend.tf`, uncomment the block, and rerun
`terraform init -migrate-state`.

## Validation

CI runs `terraform fmt -check` and `terraform validate` for both clouds —
no credentials required because validation does not reach the provider
API.

    make iac-fmt
    make iac-validate
