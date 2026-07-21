variable "environment" {
  type        = string
  description = "The deployment environment (e.g. dev, prod)"
}

variable "notification_email" {
  type        = string
  description = "Email address to subscribe to the SNS topic for notifications"
}
