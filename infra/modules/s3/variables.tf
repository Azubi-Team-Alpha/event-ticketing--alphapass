variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, prod)"
}

variable "bucket_name" {
  type        = string
  default     = "alphapass-frontend-app-dev"
  description = "Name of the S3 bucket for static website hosting"
}

variable "cors_allowed_origins" {
  type        = list(string)
  default     = ["*"]
  description = "Allowed origins for S3 bucket CORS policy"
}
