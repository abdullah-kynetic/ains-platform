# Lean single-host environment profile: one EC2 t4g.micro runs Caddy, the API,
# the receipt worker and PostgreSQL 16. Use a separate name, bucket and state
# file for testing and production; never point both environments at the same
# resources. No RDS, NAT, load balancer or Secrets Manager is provisioned by
# this low-cost profile. Runtime secrets live in SSM Parameter Store
# SecureStrings; no secret value enters Terraform state.
terraform {
  required_version = ">= 1.7"
  # Local state; pass a per-account path at init, e.g.
  # terraform init -backend-config=path=$HOME/ains-state/<account-id>/terraform.tfstate
  backend "local" {}
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "Kien"
      Environment = var.environment
    }
  }
}
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" { state = "available" }
data "aws_ssm_parameter" "ami" { name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64" }

locals {
  account_id        = data.aws_caller_identity.current.account_id
  ops_bucket        = "${var.bucket_name}-ops"
  param_prefix      = "/${var.name}"
  build_from_source = var.app_image == ""
  image             = local.build_from_source ? "ains-api:local" : var.app_image
  api_domain        = var.api_domain != "" ? var.api_domain : "${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
  bundle_key        = local.build_from_source && var.source_bundle_path != "" ? "releases/${filemd5(var.source_bundle_path)}.tar.gz" : ""
  trail_arn         = "arn:aws:cloudtrail:${var.region}:${local.account_id}:trail/${var.name}"
}

# --- Network: one public subnet, no NAT -------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.42.0.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
}
resource "aws_internet_gateway" "main" { vpc_id = aws_vpc.main.id }
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
resource "aws_security_group" "app" {
  name   = "${var.name}-app"
  vpc_id = aws_vpc.main.id
  # PostgreSQL listens on localhost only; no 5432 or SSH ingress.
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# --- S3: documents + one ops bucket (access logs, CloudTrail, DB backups, releases)
resource "aws_s3_bucket" "documents" {
  bucket              = var.bucket_name
  object_lock_enabled = true # free; no default retention rule is set
}
resource "aws_s3_bucket" "ops" {
  bucket        = local.ops_bucket
  force_destroy = false
}
locals {
  buckets = { documents = aws_s3_bucket.documents.id, ops = aws_s3_bucket.ops.id }
}
resource "aws_s3_bucket_public_access_block" "all" {
  for_each                = local.buckets
  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_versioning" "ops" {
  bucket = aws_s3_bucket.ops.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_kms_key" "documents" {
  count                   = var.s3_sse == "aws:kms" ? 1 : 0
  description             = "Kien document encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}
resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = local.buckets
  bucket   = each.value
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = each.key == "documents" ? var.s3_sse : "AES256"
      kms_master_key_id = each.key == "documents" && var.s3_sse == "aws:kms" ? aws_kms_key.documents[0].arn : null
    }
    bucket_key_enabled = each.key == "documents" && var.s3_sse == "aws:kms"
  }
}
resource "aws_s3_bucket_object_lock_configuration" "documents" {
  bucket              = aws_s3_bucket.documents.id
  object_lock_enabled = "Enabled"
  depends_on          = [aws_s3_bucket_versioning.documents]
}
resource "aws_s3_bucket_lifecycle_configuration" "ops" {
  bucket = aws_s3_bucket.ops.id
  rule {
    id     = "expire-logs"
    status = "Enabled"
    filter { prefix = "logs/" }
    expiration { days = var.log_retention_days }
  }
  rule {
    id     = "expire-trail"
    status = "Enabled"
    filter { prefix = "AWSLogs/" }
    expiration { days = var.log_retention_days }
  }
  rule {
    id     = "expire-db-backups"
    status = "Enabled"
    filter { prefix = "backups/" }
    expiration { days = var.backup_retention_days }
  }
  rule {
    id     = "expire-releases"
    status = "Enabled"
    filter { prefix = "releases/" }
    expiration { days = 90 }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = var.noncurrent_version_days }
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
  depends_on = [aws_s3_bucket_versioning.documents]
}
resource "aws_s3_bucket_logging" "documents" {
  bucket        = aws_s3_bucket.documents.id
  target_bucket = aws_s3_bucket.ops.id
  target_prefix = "logs/documents/"
  depends_on    = [aws_s3_bucket_policy.ops]
}
resource "aws_s3_bucket_policy" "ops" {
  bucket = aws_s3_bucket.ops.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.ops.arn, "${aws_s3_bucket.ops.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } },
    { Effect = "Allow", Principal = { Service = "logging.s3.amazonaws.com" }, Action = "s3:PutObject", Resource = "${aws_s3_bucket.ops.arn}/logs/documents/*", Condition = { ArnEquals = { "aws:SourceArn" = aws_s3_bucket.documents.arn }, StringEquals = { "aws:SourceAccount" = local.account_id } } },
    { Effect = "Allow", Principal = { Service = "cloudtrail.amazonaws.com" }, Action = "s3:GetBucketAcl", Resource = aws_s3_bucket.ops.arn, Condition = { StringEquals = { "aws:SourceArn" = local.trail_arn } } },
    { Effect = "Allow", Principal = { Service = "cloudtrail.amazonaws.com" }, Action = "s3:PutObject", Resource = "${aws_s3_bucket.ops.arn}/AWSLogs/${local.account_id}/*", Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control", "aws:SourceArn" = local.trail_arn } } }
  ] })
}
resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.documents.arn, "${aws_s3_bucket.documents.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }
  ] })
}

# First management-events trail per account is free. Data events are opt-in (billed).
resource "aws_cloudtrail" "main" {
  name                          = var.name
  s3_bucket_name                = aws_s3_bucket.ops.id
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
  dynamic "event_selector" {
    for_each = var.trail_document_data_events ? [1] : []
    content {
      read_write_type           = "All"
      include_management_events = true
      data_resource {
        type   = "AWS::S3::Object"
        values = ["${aws_s3_bucket.documents.arn}/"]
      }
    }
  }
  depends_on = [aws_s3_bucket_policy.ops]
}

# --- Release bundle (built on the instance; no registry) ---------------------
resource "aws_s3_object" "source" {
  count  = local.build_from_source && var.source_bundle_path != "" ? 1 : 0
  bucket = aws_s3_bucket.ops.id
  key    = local.bundle_key
  source = var.source_bundle_path
  etag   = filemd5(var.source_bundle_path)
}

# --- IAM: instance role only (no static keys) --------------------------------
resource "aws_iam_role" "app" {
  name               = "${var.name}-app"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy" "app" {
  role = aws_iam_role.app.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:PutObjectRetention"], Resource = "${aws_s3_bucket.documents.arn}/firms/*" },
    { Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.ops.arn}/backups/*" },
    { Effect = "Allow", Action = ["s3:GetObject"], Resource = "${aws_s3_bucket.ops.arn}/releases/*" },
    { Effect = "Allow", Action = ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath", "ssm:PutParameter"], Resource = ["arn:aws:ssm:${var.region}:${local.account_id}:parameter${local.param_prefix}", "arn:aws:ssm:${var.region}:${local.account_id}:parameter${local.param_prefix}/*"] }
  ], var.s3_sse == "aws:kms" ? [{ Effect = "Allow", Action = ["kms:Decrypt", "kms:GenerateDataKey"], Resource = aws_kms_key.documents[0].arn }] : []) })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_instance_profile" "app" { role = aws_iam_role.app.name }

# --- Compute ------------------------------------------------------------------
resource "aws_eip" "app" {
  domain = "vpc"
  tags   = { Name = var.name }
}
resource "aws_instance" "app" {
  ami                         = data.aws_ssm_parameter.ami.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = false
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  credit_specification { cpu_credits = "standard" } # never bill unlimited-mode surplus credits
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }
  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_gb
    encrypted   = true
  }
  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    region       = var.region
    image        = local.image
    domain       = local.api_domain
    param_prefix = local.param_prefix
    ops_bucket   = aws_s3_bucket.ops.id
    source_uri   = local.build_from_source ? "s3://${aws_s3_bucket.ops.id}/${local.bundle_key}" : ""
    environment  = jsonencode({ STORAGE_BACKEND = "s3", S3_BUCKET = var.bucket_name, AWS_REGION = var.region, S3_SSE = var.s3_sse, S3_KMS_KEY_ID = var.s3_sse == "aws:kms" ? aws_kms_key.documents[0].arn : "", S3_RETENTION_DAYS = tostring(var.retention_days), S3_RETENTION_MODE = var.retention_mode, SESSION_COOKIE_SECURE = "true", CORS_ORIGINS = var.portal_url, PORTAL_URL = var.portal_url, EMAIL_FROM = var.email_from, SENTRY_ENVIRONMENT = var.environment })
  })
  user_data_replace_on_change = true
  tags                        = { Name = var.name }
  depends_on                  = [aws_iam_role_policy.app, aws_s3_object.source]
  lifecycle {
    precondition {
      condition     = var.app_image != "" || var.source_bundle_path != ""
      error_message = "Set app_image or provide a .tar.gz source_bundle_path when building on the instance."
    }
  }
}
resource "aws_eip_association" "app" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.app.id
}
