output "function_name" {
  value       = aws_lambda_function.api_backend.function_name
  description = "The name of the Lambda function"
}

output "function_arn" {
  value       = aws_lambda_function.api_backend.arn
  description = "The ARN of the Lambda function"
}

output "invoke_arn" {
  value       = aws_lambda_function.api_backend.invoke_arn
  description = "The invocation ARN of the Lambda function"
}
