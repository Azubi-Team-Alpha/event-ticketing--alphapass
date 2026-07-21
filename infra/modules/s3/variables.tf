variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, prod)"
}

variable "price_class" {
  type        = string
  default     = "PriceClass_100"
  description = "CloudFront price class (PriceClass_100 = US/Canada/Europe only, cheapest tier)"
}

variable "domain_aliases" {
  type        = list(string)
  default     = []
  description = "Custom domain names (CNAMEs) to attach to the distribution, e.g. [\"app.alphapass.com\"]. Requires acm_certificate_arn to be set."
}

variable "acm_certificate_arn" {
  type        = string
  default     = null
  description = "ARN of an ACM certificate (must be in us-east-1) for custom domain aliases. Leave null to use the default *.cloudfront.net certificate."
}
