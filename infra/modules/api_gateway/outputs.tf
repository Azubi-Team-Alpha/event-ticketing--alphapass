output "api_endpoint" {
  value       = aws_api_gateway_stage.stage.invoke_url
  description = "Base URL of the serverless REST API Gateway stage"
}
