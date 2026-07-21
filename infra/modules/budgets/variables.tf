variable "environment" {
  type        = string
  description = "The deployment environment"
}

variable "notification_email" {
  type        = string
  description = "Email address to send budget breach alerts to"
}
