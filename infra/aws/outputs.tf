output "api_ip" { value = aws_eip.app.public_ip }
output "api_url" { value = "https://${local.api_domain}" }
output "documents_bucket" { value = aws_s3_bucket.documents.id }
output "ops_bucket" { value = aws_s3_bucket.ops.id }
output "instance_id" { value = aws_instance.app.id }
output "parameter_prefix" { value = local.param_prefix }
