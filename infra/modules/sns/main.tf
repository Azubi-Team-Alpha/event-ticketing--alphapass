resource "aws_sns_topic" "confirmations" {
  name = "alphapass-confirmations-topic-${var.environment}"
}

resource "aws_sns_topic_subscription" "email_sub" {
  topic_arn = aws_sns_topic.confirmations.arn
  protocol  = "email"
  endpoint  = var.notification_email
}
