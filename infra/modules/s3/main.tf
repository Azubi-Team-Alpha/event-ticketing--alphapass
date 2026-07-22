# ==============================================================================
# FRONTEND STATIC WEBSITE HOSTING — S3 Serverless Bucket (No CloudFront)
# ==============================================================================

# --- S3 Bucket for Frontend Static Web Assets ---
resource "aws_s3_bucket" "frontend" {
  bucket        = "alphapass-frontend-${var.environment}"
  force_destroy = true

  tags = {
    Name        = "AlphaPass Frontend Static Site"
    Environment = var.environment
  }
}

# --- S3 Bucket Website Configuration ---
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "404.html"
  }
}

# --- Allow Public Read Access for S3 Static Website Hosting ---
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# --- Bucket Ownership Controls ---
resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# --- Bucket Versioning ---
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

# --- S3 Bucket CORS Configuration ---
resource "aws_s3_bucket_cors_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# --- Public Read Bucket Policy for Website Hosting ---
data "aws_iam_policy_document" "public_read" {
  statement {
    sid       = "PublicReadGetObject"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket     = aws_s3_bucket.frontend.id
  policy     = data.aws_iam_policy_document.public_read.json
  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# --- Upload Frontend Static Website Files to S3 Bucket ---
resource "aws_s3_object" "frontend_files" {
  for_each = fileset("${path.module}/../../../frontend", "**")

  bucket       = aws_s3_bucket.frontend.id
  key          = each.value
  source       = "${path.module}/../../../frontend/${each.value}"
  etag         = filemd5("${path.module}/../../../frontend/${each.value}")
  content_type = lookup(
    {
      "html"  = "text/html",
      "css"   = "text/css",
      "js"    = "application/javascript",
      "png"   = "image/png",
      "jpg"   = "image/jpeg",
      "jpeg"  = "image/jpeg",
      "gif"   = "image/gif",
      "svg"   = "image/svg+xml",
      "ico"   = "image/x-icon",
      "json"  = "application/json",
      "woff"  = "font/woff",
      "woff2" = "font/woff2",
      "ttf"   = "font/ttf",
      "eot"   = "application/vnd.ms-fontobject",
      "otf"   = "font/otf"
    },
    split(".", each.value)[length(split(".", each.value)) - 1],
    "text/html"
  )
}

