variable "region" {
  type    = string
  default = "us-east-1"
}
variable "name" {
  type    = string
  default = "ains-prod"
}
variable "bucket_name" {
  type = string
}
variable "api_domain" {
  type = string
}
variable "app_image" {
  description = "Public registry ARM64 image pinned by digest"
  type        = string
}
variable "secret_arns" {
  description = "Existing Secrets Manager secret ARNs for runtime environment. Values stay out of Terraform."
  type        = map(string)
  validation {
    condition     = alltrue([for key in ["SESSION_SECRET", "DATABASE_URL", "RESEND_API_KEY"] : contains(keys(var.secret_arns), key)])
    error_message = "Provide SESSION_SECRET, DATABASE_URL and RESEND_API_KEY secret ARNs."
  }
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
variable "create_app_access_key" {
  description = "Optional compatibility credential; EC2 uses its instance role instead. Secret is only in state."
  type        = bool
  default     = false
}
