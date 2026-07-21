# ==============================================================================
# ALPHAPASS (TICKET HUB) - SERVERLESS INFRASTRUCTURE FOUNDATION (MODULARIZED)
# ==============================================================================

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

# --- Module: DynamoDB Tables ---
module "dynamodb" {
  source      = "./modules/dynamodb"
  environment = var.environment
}

# --- Module: SNS Topic and Subscription ---
module "sns" {
  source             = "./modules/sns"
  environment        = var.environment
  notification_email = var.notification_email
}

# --- Module: AWS Lambda backend function ---
module "lambda" {
  source                   = "./modules/lambda"
  environment              = var.environment
  events_table_name        = module.dynamodb.events_table_name
  events_table_arn         = module.dynamodb.events_table_arn
  registrations_table_name = module.dynamodb.registrations_table_name
  registrations_table_arn  = module.dynamodb.registrations_table_arn
  sns_topic_arn            = module.sns.topic_arn
}

# --- Module: API Gateway REST Interface ---
module "api_gateway" {
  source               = "./modules/api_gateway"
  environment          = var.environment
  lambda_function_name = module.lambda.function_name
  lambda_invoke_arn    = module.lambda.invoke_arn
}

# --- Module: CloudWatch Alarms ---
module "cloudwatch" {
  source               = "./modules/cloudwatch"
  environment          = var.environment
  lambda_function_name = module.lambda.function_name
  sns_topic_arn        = module.sns.topic_arn
}

# --- Module: AWS Budget ---
module "budgets" {
  source             = "./modules/budgets"
  environment        = var.environment
  notification_email = var.notification_email
}

# --- Module: Frontend Static Hosting (S3 + CloudFront) ---
module "frontend_hosting" {
  source              = "./modules/frontend_hosting"
  environment         = var.environment
  price_class         = var.cloudfront_price_class
  domain_aliases      = var.frontend_domain_aliases
  acm_certificate_arn = var.frontend_acm_certificate_arn
}
