mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b"] }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_ssm_parameter" {
    defaults = { value = "ami-0123456789abcdef0" }
  }
  mock_resource "aws_eip" {
    defaults = { public_ip = "198.51.100.7" }
  }
}
variables {
  bucket_name = "synthetic-ains-documents"
  environment = "testing"
  api_domain  = "api.example.test"
  app_image   = "ghcr.io/synthetic/ains@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  portal_url  = "https://portal.example.test"
  email_from  = "synthetic@example.test"
}
run "lean_single_host" {
  command = apply
  assert {
    condition     = aws_instance.app.instance_type == "t4g.micro" && aws_instance.app.root_block_device[0].volume_size == 20 && aws_instance.app.root_block_device[0].encrypted
    error_message = "Lean profile is one encrypted 20 GB t4g.micro."
  }
  assert {
    condition     = strcontains(aws_instance.app.user_data, "postgresql16-server") && strcontains(aws_instance.app.user_data, "listen_addresses = 'localhost'") && strcontains(aws_instance.app.user_data, "/swapfile")
    error_message = "Postgres must run locally on the host with swap."
  }
  assert {
    condition     = strcontains(aws_instance.app.user_data, "SecureString") && !strcontains(aws_instance.app.user_data, "secretsmanager")
    error_message = "Secrets must use SSM Parameter Store, not Secrets Manager."
  }
  assert {
    condition     = strcontains(aws_instance.app.user_data, "pg_dump") && strcontains(aws_instance.app.user_data, "ains-backup.timer")
    error_message = "Daily database backup to S3 is required."
  }
  assert {
    condition     = strcontains(aws_instance.app.user_data, "--entrypoint python") && strcontains(aws_instance.app.user_data, "--host 127.0.0.1")
    error_message = "Worker must avoid concurrent migrations; API binds loopback only."
  }
  assert {
    condition     = aws_s3_bucket.documents.object_lock_enabled && aws_s3_bucket_versioning.documents.versioning_configuration[0].status == "Enabled"
    error_message = "Document storage must support immutable versions."
  }
  assert {
    condition     = aws_s3_bucket_versioning.ops.versioning_configuration[0].status == "Enabled"
    error_message = "Operational storage must retain versioned recovery artifacts."
  }
  assert {
    condition     = aws_instance.app.tags.Environment == "testing"
    error_message = "The test fixture must be visibly tagged as testing."
  }
  assert {
    condition     = length(aws_cloudtrail.main.event_selector) == 0
    error_message = "Billed CloudTrail data events are off by default."
  }
  assert {
    condition     = alltrue([for rule in aws_security_group.app.ingress : !contains([22, 5432], rule.from_port)])
    error_message = "No SSH or database port may be public."
  }
}
run "kms_retention_settings" {
  command = apply
  variables {
    s3_sse         = "aws:kms"
    retention_days = 365
    retention_mode = "COMPLIANCE"
  }
  assert {
    condition     = length(aws_kms_key.documents) == 1 && aws_kms_key.documents[0].enable_key_rotation
    error_message = "KMS mode needs a rotating encryption key."
  }
}
