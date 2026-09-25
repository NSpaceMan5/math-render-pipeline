terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "random_id" "suffix" { byte_length = 3 }

# ---------------- object storage ----------------
resource "google_storage_bucket" "renders" {
  name                        = "${var.project}-renders-${random_id.suffix.hex}"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning { enabled = true }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age = 90
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      age = 365
    }
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = var.renders_retention_days
    }
  }
}

# ---------------- metadata database ----------------
resource "google_sql_database_instance" "meta" {
  name                = "${var.project}-meta-${random_id.suffix.hex}"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = false

  settings {
    tier              = "db-f1-micro"
    disk_size         = 10
    disk_type         = "PD_HDD"
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false
    }
  }
}

resource "google_sql_database" "mrp" {
  name     = "mrp"
  instance = google_sql_database_instance.meta.name
}

resource "google_sql_user" "mrp" {
  name     = "mrp"
  instance = google_sql_database_instance.meta.name
  password = var.db_password
}

# ---------------- service account for batch jobs ----------------
resource "google_service_account" "batch" {
  account_id   = "${var.project}-batch"
  display_name = "MRP batch runner"
}

resource "google_project_iam_member" "batch_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_storage_bucket_iam_member" "batch_writer" {
  bucket = google_storage_bucket.renders.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.batch.email}"
}

# ---------------- secrets ----------------
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.project}-db-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}
