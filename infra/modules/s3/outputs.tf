output "bucket_id" {
  value       = aws_s3_bucket.frontend.id
  description = "ID / Name of the S3 bucket holding the built static site"
}

output "bucket_name" {
  value       = aws_s3_bucket.frontend.id
  description = "Name of the S3 bucket holding the built static site"
}

output "bucket_arn" {
  value       = aws_s3_bucket.frontend.arn
  description = "ARN of the S3 bucket holding the built static site"
}

output "website_endpoint" {
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
  description = "Public HTTP S3 Website endpoint URL"
}

output "site_url" {
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
  description = "Publicly accessible HTTP URL of the deployed frontend"
}
