output "bucket_name" { value = aws_s3_bucket.renders.bucket }
output "db_endpoint" { value = aws_db_instance.meta.endpoint }
output "db_name" { value = aws_db_instance.meta.db_name }
output "log_group_prefix" { value = "/mrp" }
output "connection_hint" {
  value = "psql \"host=${aws_db_instance.meta.address} port=5432 user=mrp dbname=mrp\""
}
