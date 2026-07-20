output "topic_arn" {
  value       = aws_sns_topic.confirmations.arn
  description = "The ARN of the notifications SNS topic"
}
