output "bucket_name" {
  value       = aws_s3_bucket.frontend.id
  description = "Name of the S3 bucket holding the built static site"
}

output "bucket_arn" {
  value       = aws_s3_bucket.frontend.arn
  description = "ARN of the S3 bucket holding the built static site"
}

output "distribution_id" {
  value       = aws_cloudfront_distribution.frontend.id
  description = "CloudFront distribution ID (used for cache invalidations on deploy)"
}

output "distribution_domain_name" {
  value       = aws_cloudfront_distribution.frontend.domain_name
  description = "CloudFront-assigned domain name, e.g. dxxxxxxxxxx.cloudfront.net"
}

output "site_url" {
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
  description = "Publicly accessible URL of the deployed frontend"
}
