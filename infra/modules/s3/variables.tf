variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, prod)"
}

variable "cors_allowed_origins" {
  type        = list(string)
  default     = ["*"]
  description = "Allowed origins for S3 bucket CORS policy"
}
