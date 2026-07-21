output "events_table_name" {
  value       = aws_dynamodb_table.events.name
  description = "The name of the events table"
}

output "events_table_arn" {
  value       = aws_dynamodb_table.events.arn
  description = "The ARN of the events table"
}

output "registrations_table_name" {
  value       = aws_dynamodb_table.registrations.name
  description = "The name of the registrations table"
}

output "registrations_table_arn" {
  value       = aws_dynamodb_table.registrations.arn
  description = "The ARN of the registrations table"
}

output "organizers_table_name" {
  value       = aws_dynamodb_table.organizers.name
}

output "organizers_table_arn" {
  value       = aws_dynamodb_table.organizers.arn
}

output "admins_table_name" {
  value       = aws_dynamodb_table.admins.name
}

output "admins_table_arn" {
  value       = aws_dynamodb_table.admins.arn
}

output "orders_table_name" {
  value       = aws_dynamodb_table.orders.name
}

output "orders_table_arn" {
  value       = aws_dynamodb_table.orders.arn
}

output "tickets_table_name" {
  value       = aws_dynamodb_table.tickets.name
}

output "tickets_table_arn" {
  value       = aws_dynamodb_table.tickets.arn
}

output "promo_codes_table_name" {
  value       = aws_dynamodb_table.promo_codes.name
}

output "promo_codes_table_arn" {
  value       = aws_dynamodb_table.promo_codes.arn
}

output "resale_listings_table_name" {
  value       = aws_dynamodb_table.resale_listings.name
}

output "resale_listings_table_arn" {
  value       = aws_dynamodb_table.resale_listings.arn
}

output "transfers_table_name" {
  value       = aws_dynamodb_table.transfers.name
}

output "transfers_table_arn" {
  value       = aws_dynamodb_table.transfers.arn
}

output "payouts_table_name" {
  value       = aws_dynamodb_table.payouts.name
}

output "payouts_table_arn" {
  value       = aws_dynamodb_table.payouts.arn
}

output "platform_settings_table_name" {
  value       = aws_dynamodb_table.platform_settings.name
}

output "platform_settings_table_arn" {
  value       = aws_dynamodb_table.platform_settings.arn
}

output "audit_logs_table_name" {
  value       = aws_dynamodb_table.audit_logs.name
}

output "audit_logs_table_arn" {
  value       = aws_dynamodb_table.audit_logs.arn
}

output "event_categories_table_name" {
  value       = aws_dynamodb_table.event_categories.name
}

output "event_categories_table_arn" {
  value       = aws_dynamodb_table.event_categories.arn
}
