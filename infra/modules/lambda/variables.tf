variable "environment" {
  type        = string
  description = "The deployment environment"
}

variable "secret_key" {
  type        = string
  sensitive   = true
  description = "JWT signing secret for the backend"
}

variable "sns_topic_arn" {
  type        = string
  description = "ARN of the notifications SNS topic"
}

# ── DynamoDB Table Names ───────────────────────────────────────────────────────

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

variable "organizers_table_name" {
  type        = string
  description = "Name of the organizers DynamoDB table"
}

variable "admins_table_name" {
  type        = string
  description = "Name of the admins DynamoDB table"
}

variable "orders_table_name" {
  type        = string
  description = "Name of the orders DynamoDB table"
}

variable "tickets_table_name" {
  type        = string
  description = "Name of the tickets DynamoDB table"
}

variable "promo_codes_table_name" {
  type        = string
  description = "Name of the promo codes DynamoDB table"
}

variable "resale_listings_table_name" {
  type        = string
  description = "Name of the resale listings DynamoDB table"
}

variable "transfers_table_name" {
  type        = string
  description = "Name of the ticket transfers DynamoDB table"
}

variable "payouts_table_name" {
  type        = string
  description = "Name of the organizer payouts DynamoDB table"
}

variable "platform_settings_table_name" {
  type        = string
  description = "Name of the platform settings DynamoDB table"
}

variable "audit_logs_table_name" {
  type        = string
  description = "Name of the audit logs DynamoDB table"
}

variable "event_categories_table_name" {
  type        = string
  description = "Name of the event categories DynamoDB table"
}
