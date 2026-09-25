terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = var.tags }
}

resource "random_id" "suffix" { byte_length = 3 }

# ---------------- object storage ----------------
resource "aws_s3_bucket" "renders" {
  bucket = "${var.project}-renders-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_versioning" "renders" {
  bucket = aws_s3_bucket.renders.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "renders" {
  bucket = aws_s3_bucket.renders.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "renders" {
  bucket                  = aws_s3_bucket.renders.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "tiering" {
  bucket = aws_s3_bucket.renders.id
  rule {
    id     = "archive-full-renders"
    status = "Enabled"
    filter {
      prefix = "renders/"
    }
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }
    expiration {
      days = var.renders_retention_days
    }
  }
}

# ---------------- metadata database ----------------
resource "aws_db_subnet_group" "meta" {
  name       = "${var.project}-meta-subnets"
  subnet_ids = data.aws_subnets.default.ids
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_db_instance" "meta" {
  identifier              = "${var.project}-meta"
  engine                  = "postgres"
  engine_version          = "16.3"
  instance_class          = "db.t4g.micro"
  allocated_storage       = 20
  storage_encrypted       = true
  db_name                 = "mrp"
  username                = "mrp"
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.meta.name
  skip_final_snapshot     = true
  apply_immediately       = true
  backup_retention_period = 7
}

# ---------------- observability (logs) ----------------
resource "aws_cloudwatch_log_group" "consumer" {
  name              = "/mrp/consumer"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "airflow" {
  name              = "/mrp/airflow"
  retention_in_days = 30
}
