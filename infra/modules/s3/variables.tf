variable "environment" {
  type        = string
  description = "Deployment environment (e.g. dev, prod)"
}

variable "bucket_name" {
  type        = string
  default     = "alphapass.alphateam.live"
  description = "Name of the S3 bucket for static website hosting (must match domain name for direct CNAME binding)"
}

variable "cors_allowed_origins" {
  type        = list(string)
  default     = ["*"]
  description = "Allowed origins for S3 bucket CORS policy"
}
