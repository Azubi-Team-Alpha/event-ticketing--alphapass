variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region for the deployment"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Deployment environment (e.g. dev, prod)"
}

variable "notification_email" {
  type        = string
  default     = "admin@alphapass.com"
  description = "Email address for notifications, budget alerts, and alarms"
}

variable "secret_key" {
  type        = string
  sensitive   = true
  description = "JWT signing secret key for the Lambda backend"
}
