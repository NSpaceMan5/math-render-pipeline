output "bucket_name" { value = aws_s3_bucket.renders.bucket }
output "db_endpoint" { value = aws_db_instance.meta.endpoint }
output "db_name" { value = aws_db_instance.meta.db_name }
output "log_group_prefix" { value = "/mrp" }
output "connection_hint" {
  value = "psql \"host=${aws_db_instance.meta.address} port=5432 user=mrp dbname=mrp\""
}

output "batch_job_queue" {
  value       = aws_batch_job_queue.renderer.name
  description = "Submit jobs with: aws batch submit-job --job-queue <name>"
}

output "batch_job_definition" {
  value       = aws_batch_job_definition.renderer.name
  description = "Job definition ARN/name for the renderer"
}

output "db_dsn_secret_arn" {
  value       = aws_secretsmanager_secret.db_dsn.arn
  description = "Secrets Manager ARN holding POSTGRES_DSN"
}
