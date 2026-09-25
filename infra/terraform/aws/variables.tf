variable "region" {
  type    = string
  default = "us-east-1"
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

variable "tags" {
  type = map(string)
  default = {
    Project   = "mrp"
    ManagedBy = "terraform"
  }
}

variable "renderer_image" {
  type        = string
  description = "Container image URI for the AWS Batch renderer"
  default     = "public.ecr.aws/docker/library/python:3.11-slim"
}
