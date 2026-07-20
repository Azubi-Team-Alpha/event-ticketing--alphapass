variable "environment" {
  type        = string
  description = "The deployment environment"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function to monitor"
}

variable "sns_topic_arn" {
  type        = string
  description = "ARN of the SNS topic to send error alerts to"
}
