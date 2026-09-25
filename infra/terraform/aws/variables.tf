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
