variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, prod)"
}

variable "cors_allowed_origins" {
  type        = list(string)
  default     = ["*"]
  description = "Allowed origins for S3 bucket CORS policy"
}

variable "custom_bucket_name" {
  type        = string
  default     = ""
  description = "Optional explicit bucket name (must match domain name if using direct CNAME)"
}
