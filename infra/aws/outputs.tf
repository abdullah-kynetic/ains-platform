output "api_ip" { value = aws_eip.app.public_ip }
output "api_url" { value = "https://${var.api_domain}" }
output "database_endpoint" { value = aws_db_instance.main.address }
output "database_admin_secret_arn" { value = aws_db_instance.main.master_user_secret[0].secret_arn }
output "documents_bucket" { value = aws_s3_bucket.documents.id }
output "instance_id" { value = aws_instance.app.id }
output "app_access_key_id" {
  value     = try(aws_iam_access_key.app[0].id, null)
  sensitive = true
}
# Access-key secret deliberately has no CLI output; prefer the instance role.
