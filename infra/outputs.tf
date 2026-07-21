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
  value       = module.frontend_hosting.bucket_name
  description = "S3 bucket to sync built frontend assets into"
}

output "frontend_distribution_id" {
  value       = module.frontend_hosting.distribution_id
  description = "CloudFront distribution ID (use for cache invalidation on deploy)"
}

output "frontend_url" {
  value       = module.frontend_hosting.site_url
  description = "Publicly accessible URL of the deployed frontend"
}
