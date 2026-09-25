# Shared conventions

Both `aws/` and `gcp/` follow the same layout and naming:

| Resource | AWS | GCP |
|---|---|---|
| Object storage | S3 bucket | GCS bucket |
| Managed Postgres | RDS PostgreSQL | Cloud SQL PostgreSQL |
| Serverless batch | AWS Batch | Cloud Run Jobs |
| Secret storage | Secrets Manager | Secret Manager |
| Logs | CloudWatch Logs | Cloud Logging |

Variable names are identical across clouds:

    project            # short slug, used as resource name prefix
    region             # cloud region
    db_password        # sensitive
    renders_retention_days   # default 365

Outputs are identical too:

    bucket_name
    db_endpoint
    connection_hint    # one-line command to connect

To swap clouds, change `cd infra/terraform/<cloud>` and rerun
`terraform init && terraform apply`. The application code is cloud-agnostic
(it reads `POSTGRES_DSN`, `S3_ENDPOINT`, `S3_BUCKET` from env).
