output "lambda_error_alarm_arn" {
  value       = aws_cloudwatch_metric_alarm.lambda_errors.arn
  description = "The ARN of the Lambda error CloudWatch alarm"
}
