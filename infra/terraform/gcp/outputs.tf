output "bucket_name" { value = google_storage_bucket.renders.name }
output "db_instance" { value = google_sql_database_instance.meta.name }
output "db_connection_name" { value = google_sql_database_instance.meta.connection_name }
output "batch_service_account" { value = google_service_account.batch.email }
output "connection_hint" {
  value = "gcloud sql connect ${google_sql_database_instance.meta.name} --user=mrp"
}
