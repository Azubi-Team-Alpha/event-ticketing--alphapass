# ==============================================================================
# ALPHAPASS (TICKET HUB) - SERVERLESS INFRASTRUCTURE FOUNDATION
# ==============================================================================
# This Terraform configuration provisions the AWS resources for the serverless
# Event Registration & Ticketing API as outlined in the project documentation.
#
# Resources created:
#   - DynamoDB Tables (Events & Registrations)
#   - IAM Roles & Policies for AWS Lambda
#   - AWS Lambda Function (Placeholder business logic)
#   - API Gateway (REST API with proxy routing to Lambda)
#   - SNS Topic (for email ticket confirmations)
#   - CloudWatch Log Group & Error Alarms
#   - AWS Budgets (Cost tracking to prevent unexpected charges)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# --- Variables ---
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
  description = "Email address for budget and alarm notifications"
}

# --- Provider ---
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "AlphaPass"
      Environment = var.environment
      Team        = "Team-Alpha"
      ManagedBy   = "Terraform"
    }
  }
}

# ==============================================================================
# 1. DYNAMODB TABLES (Events & Registrations)
# ==============================================================================

# Events Table
resource "aws_dynamodb_table" "events" {
  name         = "alphapass-events-${var.environment}"
  billing_mode = "PAY_PER_REQUEST" # On-Demand pricing (Serverless / Free Tier friendly)
  hash_key     = "EventID"

  attribute {
    name = "EventID"
    type = "S" # String type
  }

  tags = {
    Name = "AlphaPass Events Table"
  }
}

# Registrations & Tickets Table
resource "aws_dynamodb_table" "registrations" {
  name         = "alphapass-registrations-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "RegistrationID"

  attribute {
    name = "RegistrationID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Registrations Table"
  }
}

# ==============================================================================
# 2. SNS TOPIC (Transactional Email confirmations)
# ==============================================================================

resource "aws_sns_topic" "confirmations" {
  name = "alphapass-confirmations-topic-${var.environment}"
}

resource "aws_sns_topic_subscription" "email_sub" {
  topic_arn = aws_sns_topic.confirmations.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# ==============================================================================
# 3. AWS LAMBDA FUNCTION (Business Logic)
# ==============================================================================

# Create a zip package dynamically for a placeholder python handler
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda.zip"
  source {
    content  = <<EOF
import json
import os
import boto3

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    
    # Placeholder routing logic
    path = event.get("path", "/")
    method = event.get("httpMethod", "GET")
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "message": "Welcome to AlphaPass Serverless API!",
            "path": path,
            "method": method,
            "status": "online"
        })
    }
EOF
    filename = "index.py"
  }
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

# IAM Policy allowing DynamoDB access, CloudWatch Logging, and SNS publishing
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
      # DynamoDB Access
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.events.arn,
          aws_dynamodb_table.registrations.arn
        ]
      },
      # SNS Publishing
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.confirmations.arn
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
  timeout          = 15 # 15 seconds
  memory_size      = 256 # 256MB memory

  environment {
    variables = {
      ENV                 = var.environment
      EVENTS_TABLE        = aws_dynamodb_table.events.name
      REGISTRATIONS_TABLE = aws_dynamodb_table.registrations.name
      CONFIRMATION_TOPIC  = aws_sns_topic.confirmations.arn
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_attach
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.api_backend.function_name}"
  retention_in_days = 7 # Automatically cleanup old logs to save costs
}

# ==============================================================================
# 4. API GATEWAY (REST Endpoints)
# ==============================================================================

resource "aws_api_gateway_rest_api" "serverless_api" {
  name        = "alphapass-serverless-api-${var.environment}"
  description = "API Gateway endpoint routing to AlphaPass Lambda backend"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# Proxy Resource for catching all paths
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.serverless_api.id
  parent_id   = aws_api_gateway_rest_api.serverless_api.root_resource_id
  path_part   = "{proxy+}"
}

# Method configuration for ANY requests
resource "aws_api_gateway_method" "proxy_method" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

# Lambda integration with API Gateway
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.serverless_api.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy_method.http_method
  integration_http_method = "POST" # API Gateway calls Lambda via HTTP POST
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_backend.invoke_arn
}

# Root ANY method (for the base URL path e.g., https://api-id.execute-api.region.amazonaws.com/dev)
resource "aws_api_gateway_method" "root_method" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  resource_id   = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration_root" {
  rest_api_id             = aws_api_gateway_rest_api.serverless_api.id
  resource_id             = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method             = aws_api_gateway_method.root_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_backend.invoke_arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda_integration,
    aws_api_gateway_integration.lambda_integration_root
  ]

  rest_api_id = aws_api_gateway_rest_api.serverless_api.id

  lifecycle {
    create_before_destroy = true
  }
}

# Stage definition
resource "aws_api_gateway_stage" "stage" {
  deployment_id = aws_api_gateway_deployment.deployment.id
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  stage_name    = var.environment
}

# Permission to allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "apigw_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_backend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.serverless_api.execution_arn}/*/*"
}

# ==============================================================================
# 5. CLOUDWATCH ALARMS
# ==============================================================================

# Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "alphapass-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300" # 5 minutes
  statistic           = "Sum"
  threshold           = "1" # Trigger if 1 error occurs
  alarm_description   = "Monitors Lambda backend execution errors"
  alarm_actions       = [aws_sns_topic.confirmations.arn]

  dimensions = {
    FunctionName = aws_lambda_function.api_backend.function_name
  }
}

# ==============================================================================
# 6. AWS BUDGET (Cost Tracking / Free Tier Protection)
# ==============================================================================

resource "aws_budgets_budget" "free_tier" {
  name              = "alphapass-free-tier-budget-${var.environment}"
  budget_type       = "COST"
  limit_amount      = "10.0"
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2026-07-20_00:00"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}

# ==============================================================================
# Outputs
# ==============================================================================
output "api_endpoint" {
  value       = aws_api_gateway_stage.stage.invoke_url
  description = "Base URL of the serverless REST API Gateway stage"
}

output "dynamodb_table_events" {
  value = aws_dynamodb_table.events.name
}

output "dynamodb_table_registrations" {
  value = aws_dynamodb_table.registrations.name
}
