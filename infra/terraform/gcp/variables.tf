variable "project_id" {
  type        = string
  description = "GCP project ID (not the same as var.project)"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "project" {
  type    = string
  default = "mrp"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "renders_retention_days" {
  type    = number
  default = 365
}

variable "labels" {
  type = map(string)
  default = {
    project   = "mrp"
    managedby = "terraform"
  }
}
