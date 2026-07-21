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
  default     = "admin@ticket-hub.com"
  description = "Email address for notifications, budget alerts, and alarms"
}

variable "cloudfront_price_class" {
  type        = string
  default     = "PriceClass_100"
  description = "CloudFront price class for the frontend distribution"
}

variable "frontend_domain_aliases" {
  type        = list(string)
  default     = []
  description = "Custom domain names (CNAMEs) for the frontend CloudFront distribution"
}

variable "frontend_acm_certificate_arn" {
  type        = string
  default     = null
  description = "ACM certificate ARN (us-east-1) for the frontend custom domain, if any"
}
