# ----------------------------------------------------------------------------
# AWS Batch — SPOT compute environment for the renderer.
#
# Design
#   * SPOT_CAPACITY_OPTIMIZED across a pool of instance families
#     (c6i/c6a/c5/m6i) — AWS picks the least-interrupted pool.
#   * min_vcpus = 0, desired = 0 — scale to zero when idle.
#   * max_vcpus = 64 — cap blast radius on a runaway queue.
#   * Container reads POSTGRES_DSN, S3_BUCKET, KAFKA_BOOTSTRAP from env.
#   * The job renders a params file (S3 or mounted) and writes PNGs to S3.
#
# Approx cost (us-east-1, 2026)
#   c6i.large on-demand:  $0.085 / hr
#   c6i.large spot:       $0.025 / hr  (-71%)
# ----------------------------------------------------------------------------

# ---- IAM: service role (AWS Batch itself) ----
resource "aws_iam_role" "batch_service" {
  name = "${var.project}-batch-service"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "batch.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service" {
  role       = aws_iam_role.batch_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# ---- IAM: spot fleet role ----
resource "aws_iam_role" "batch_spot_fleet" {
  name = "${var.project}-batch-spot-fleet"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "spotfleet.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "batch_spot_fleet" {
  role       = aws_iam_role.batch_spot_fleet.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

# ---- IAM: EC2 instance role (runs the container) ----
resource "aws_iam_role" "batch_instance" {
  name = "${var.project}-batch-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "batch_instance_ecs" {
  role       = aws_iam_role.batch_instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy" "batch_instance_app" {
  name = "${var.project}-batch-instance-app"
  role = aws_iam_role.batch_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.renders.arn,
          "${aws_s3_bucket.renders.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.consumer.arn}:*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "batch_instance" {
  name = "${var.project}-batch-instance"
  role = aws_iam_role.batch_instance.name
}

# ---- Networking ----
resource "aws_security_group" "batch" {
  name        = "${var.project}-batch"
  description = "Outbound only for batch jobs"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---- Compute environment (SPOT) ----
resource "aws_batch_compute_environment" "spot" {
  compute_environment_name = "${var.project}-spot"
  type                     = "MANAGED"
  state                    = "ENABLED"
  service_role             = aws_iam_role.batch_service.arn

  compute_resources {
    type                = "SPOT"
    allocation_strategy = "SPOT_CAPACITY_OPTIMIZED"

    min_vcpus     = 0
    desired_vcpus = 0
    max_vcpus     = 64

    instance_type = [
      "c6i.large", "c6a.large", "c5.large",
      "m6i.large", "m6a.large", "m5.large",
    ]

    instance_role       = aws_iam_instance_profile.batch_instance.arn
    spot_iam_fleet_role = aws_iam_role.batch_spot_fleet.arn
    security_group_ids  = [aws_security_group.batch.id]
    subnets             = data.aws_subnets.default.ids

    tags = { Name = "${var.project}-spot" }
  }

  depends_on = [
    aws_iam_role_policy_attachment.batch_service,
    aws_iam_role_policy_attachment.batch_spot_fleet,
    aws_iam_role_policy_attachment.batch_instance_ecs,
  ]
}

# ---- Job queue ----
resource "aws_batch_job_queue" "renderer" {
  name                 = "${var.project}-renderer"
  state                = "ENABLED"
  priority             = 1
  compute_environments = [aws_batch_compute_environment.spot.arn]
}

# ---- Job definition ----
resource "aws_batch_job_definition" "renderer" {
  name = "${var.project}-renderer"
  type = "container"

  platform_capabilities = ["EC2"]

  container_properties = jsonencode({
    image = "${var.renderer_image}"

    resourceRequirements = [
      { type = "VCPU", value = "2" },
      { type = "MEMORY", value = "4096" },
    ]

    command = ["mrp", "batch", "--csv", "params/example_params.csv"]

    environment = [
      { name = "USE_S3", value = "true" },
      { name = "S3_BUCKET", value = aws_s3_bucket.renders.bucket },
      { name = "LOG_LEVEL", value = "INFO" },
    ]

    # Secrets injected at runtime from Secrets Manager
    secrets = [
      { name = "POSTGRES_DSN", valueFrom = aws_secretsmanager_secret.db_dsn.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/aws/batch/${var.project}"
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "renderer"
      }
    }

    # SPOT has no persistent storage; force a fresh container each job.
    readonlyRootFilesystem = false
    privileged             = false
  })

  retry_strategy {
    attempts = 3
    evaluate_on_exit {
      action           = "RETRY"
      on_status_reason = "Host EC2*"
    }
    evaluate_on_exit {
      action    = "EXIT"
      on_reason = "*"
    }
  }

  timeout {
    attempt_duration_seconds = 3600
  }
}

# ---- Postgres DSN secret ----
resource "aws_secretsmanager_secret" "db_dsn" {
  name                    = "${var.project}/postgres-dsn"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_dsn" {
  secret_id     = aws_secretsmanager_secret.db_dsn.id
  secret_string = "postgresql://mrp:${var.db_password}@${aws_db_instance.meta.address}:5432/mrp"
}

# ---- Log group for batch ----
resource "aws_cloudwatch_log_group" "batch" {
  name              = "/aws/batch/${var.project}"
  retention_in_days = 30
}
