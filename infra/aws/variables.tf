variable "region" {
  type    = string
  default = "us-east-1"
}
variable "environment" {
  description = "Deployment environment. Use separate names, buckets and Terraform state for testing and production."
  type        = string
  default     = "production"
  validation {
    condition     = contains(["testing", "production"], var.environment)
    error_message = "environment must be testing or production."
  }
}
variable "name" {
  type    = string
  default = "kien-production"
}
variable "bucket_name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name)) && !strcontains(var.bucket_name, "..")
    error_message = "bucket_name must be a valid globally unique S3 bucket name."
  }
}
variable "api_domain" {
  description = "API hostname. Empty uses <elastic-ip>.sslip.io so Caddy can obtain a certificate before DNS exists."
  type        = string
  default     = ""
}
variable "app_image" {
  description = "Public registry ARM64 image pinned by digest. Empty builds the image on the instance from source_bundle_path."
  type        = string
  default     = ""
}
variable "source_bundle_path" {
  description = "Local git-archive tarball of the repo, uploaded to the ops bucket and built on the instance when app_image is empty."
  type        = string
  default     = ""
  validation {
    condition     = var.source_bundle_path == "" || endswith(var.source_bundle_path, ".tar.gz")
    error_message = "source_bundle_path must be a .tar.gz produced by git archive."
  }
}
variable "instance_type" {
  description = "t4g.micro (1 GB) by default; t4g.small (2 GB) if memory is tight."
  type        = string
  default     = "t4g.micro"
}
variable "root_volume_gb" {
  type    = number
  default = 20
}
variable "portal_url" {
  type = string
}
variable "email_from" {
  type = string
}
variable "s3_sse" {
  type    = string
  default = "AES256"
  validation {
    condition     = contains(["AES256", "aws:kms"], var.s3_sse)
    error_message = "Choose AES256 or aws:kms."
  }
}
variable "retention_days" {
  type    = number
  default = 0
  validation {
    condition     = var.retention_days >= 0 && floor(var.retention_days) == var.retention_days
    error_message = "Retention days must be a nonnegative integer."
  }
}
variable "retention_mode" {
  type    = string
  default = "GOVERNANCE"
  validation {
    condition     = contains(["GOVERNANCE", "COMPLIANCE"], var.retention_mode)
    error_message = "Choose GOVERNANCE or COMPLIANCE."
  }
}
variable "trail_document_data_events" {
  description = "Record S3 object-level events for documents in CloudTrail (billed per event)."
  type        = bool
  default     = false
}
variable "log_retention_days" {
  description = "Expire S3 access and CloudTrail logs after N days."
  type        = number
  default     = 90
}
variable "backup_retention_days" {
  description = "Expire daily pg_dump backups after N days."
  type        = number
  default     = 14
}
variable "noncurrent_version_days" {
  description = "Expire superseded document versions after N days (locked versions are kept until retention ends)."
  type        = number
  default     = 365
}
