output "api_endpoint" {
  value       = module.api_gateway.api_endpoint
  description = "Base URL of the serverless REST API Gateway stage"
}

output "dynamodb_table_events" {
  value = module.dynamodb.events_table_name
}

output "dynamodb_table_registrations" {
  value = module.dynamodb.registrations_table_name
}

output "frontend_bucket_name" {
  value       = module.s3.bucket_name
  description = "S3 bucket name hosting the static website assets"
}

output "frontend_website_endpoint" {
  value       = module.s3.website_endpoint
  description = "Public HTTP S3 Website endpoint URL"
}

output "frontend_url" {
  value       = module.s3.site_url
  description = "Publicly accessible HTTP URL of the deployed frontend"
}

output "lambda_function_name" {
  value       = module.lambda.function_name
  description = "The name of the deployed AWS Lambda backend function"
}

