variable "environment" {
  type        = string
  description = "The deployment environment"
}

variable "events_table_name" {
  type        = string
  description = "Name of the events DynamoDB table"
}

variable "events_table_arn" {
  type        = string
  description = "ARN of the events DynamoDB table"
}

variable "registrations_table_name" {
  type        = string
  description = "Name of the registrations DynamoDB table"
}

variable "registrations_table_arn" {
  type        = string
  description = "ARN of the registrations DynamoDB table"
}

variable "sns_topic_arn" {
  type        = string
  description = "ARN of the notifications SNS topic"
}
