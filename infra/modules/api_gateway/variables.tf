variable "environment" {
  type        = string
  description = "The deployment environment"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function to invoke"
}

variable "lambda_invoke_arn" {
  type        = string
  description = "Invocation ARN of the Lambda function"
}
