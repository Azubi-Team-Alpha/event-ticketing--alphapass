# Generate a zip package of the backend code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../backend"
  output_path = "${path.module}/lambda.zip"
  excludes = [
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "test.db",
    "tests",
    "README.md",
    "TESTING.md",
    "alembic",
    "alembic.ini",
    "requirements-dev.txt",
    ".env"
  ]
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "alphapass-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy allowing DynamoDB access, CloudWatch Logging, SNS publishing, SES sending, and S3 access
resource "aws_iam_policy" "lambda_policy" {
  name        = "alphapass-lambda-policy-${var.environment}"
  description = "Permissions required for AlphaPass ticketing serverless API"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logging
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      # DynamoDB Access – all AlphaPass tables
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:DescribeTable",
          "dynamodb:TransactWriteItems"
        ]
        Resource = [
          "arn:aws:dynamodb:*:*:table/alphapass-*",
          "arn:aws:dynamodb:*:*:table/alphapass-*/index/*"
        ]
      },
      # SNS Publishing
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_topic_arn
      },
      # SES Email sending
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      # S3 Access for QR codes and ticket assets
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::alphapass-*/*"
      }
    ]
  })
}

# Attach IAM Policy to Role
resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# The Lambda Function
resource "aws_lambda_function" "api_backend" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "alphapass-backend-api-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 512

  environment {
    variables = {
      ENV                          = var.environment
      SECRET_KEY                   = var.secret_key
      EVENTS_TABLE                 = var.events_table_name
      REGISTRATIONS_TABLE          = var.registrations_table_name
      ORGANIZERS_TABLE             = var.organizers_table_name
      ADMINS_TABLE                 = var.admins_table_name
      ORDERS_TABLE                 = var.orders_table_name
      TICKETS_TABLE                = var.tickets_table_name
      PROMO_CODES_TABLE            = var.promo_codes_table_name
      RESALE_LISTINGS_TABLE        = var.resale_listings_table_name
      TRANSFERS_TABLE              = var.transfers_table_name
      PAYOUTS_TABLE                = var.payouts_table_name
      PLATFORM_SETTINGS_TABLE      = var.platform_settings_table_name
      AUDIT_LOGS_TABLE             = var.audit_logs_table_name
      EVENT_CATEGORIES_TABLE       = var.event_categories_table_name
      CONFIRMATION_TOPIC           = var.sns_topic_arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attach
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.api_backend.function_name}"
  retention_in_days = 7
}
