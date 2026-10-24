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
  mock_resource "aws_db_instance" {
    defaults = { master_user_secret = [{ secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:synthetic-master", secret_status = "active", kms_key_id = "synthetic" }] }
  }
}
variables {
  bucket_name = "synthetic-ains-documents"
  api_domain  = "api.example.test"
  app_image   = "ghcr.io/synthetic/ains@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  portal_url  = "https://portal.example.test"
  email_from  = "synthetic@example.test"
  secret_arns = {
    SESSION_SECRET = "arn:aws:secretsmanager:us-east-1:123456789012:secret:synthetic-session"
    DATABASE_URL   = "arn:aws:secretsmanager:us-east-1:123456789012:secret:synthetic-database"
    RESEND_API_KEY = "arn:aws:secretsmanager:us-east-1:123456789012:secret:synthetic-email"
  }
}
run "private_database_and_retention" {
  command = plan
  assert {
    condition     = !aws_db_instance.main.publicly_accessible && aws_db_instance.main.storage_encrypted && aws_db_instance.main.backup_retention_period == 7
    error_message = "Database must remain private, encrypted and backed up."
  }
  assert {
    condition     = aws_s3_bucket.documents.object_lock_enabled && aws_s3_bucket_versioning.all["documents"].versioning_configuration[0].status == "Enabled"
    error_message = "Document storage must support immutable versions."
  }
  assert {
    condition     = length(aws_iam_access_key.app) == 0
    error_message = "EC2 must default to role credentials."
  }
  assert {
    condition     = strcontains(aws_instance.app.user_data, "--entrypoint python") && strcontains(aws_instance.app.user_data, "--forwarded-allow-ips=*")
    error_message = "Worker must avoid concurrent migrations; localhost proxy must forward client IP."
  }
}
run "kms_retention_settings" {
  command = plan
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
