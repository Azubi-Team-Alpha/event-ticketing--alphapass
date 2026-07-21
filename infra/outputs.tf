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
