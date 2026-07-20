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
