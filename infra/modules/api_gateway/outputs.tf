output "api_endpoint" {
  value       = aws_api_gateway_stage.stage.invoke_url
  description = "Base URL of the serverless REST API Gateway stage"
}

output "api_gateway_id" {
  value       = aws_api_gateway_rest_api.serverless_api.id
  description = "REST API Gateway ID"
}
