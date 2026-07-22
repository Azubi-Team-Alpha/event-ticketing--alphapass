
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
  source      = "./modules/lambda"
  environment = var.environment
  secret_key  = var.secret_key

  # All DynamoDB table names
  events_table_name            = module.dynamodb.events_table_name
  events_table_arn             = module.dynamodb.events_table_arn
  registrations_table_name     = module.dynamodb.registrations_table_name
  registrations_table_arn      = module.dynamodb.registrations_table_arn
  organizers_table_name        = module.dynamodb.organizers_table_name
  admins_table_name            = module.dynamodb.admins_table_name
  orders_table_name            = module.dynamodb.orders_table_name
  tickets_table_name           = module.dynamodb.tickets_table_name
  promo_codes_table_name       = module.dynamodb.promo_codes_table_name
  resale_listings_table_name   = module.dynamodb.resale_listings_table_name
  transfers_table_name         = module.dynamodb.transfers_table_name
  payouts_table_name           = module.dynamodb.payouts_table_name
  platform_settings_table_name = module.dynamodb.platform_settings_table_name
  audit_logs_table_name        = module.dynamodb.audit_logs_table_name
  event_categories_table_name  = module.dynamodb.event_categories_table_name

  sns_topic_arn = module.sns.topic_arn
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

# --- Module: Frontend Static Hosting (S3 Direct Website Hosting) ---
module "frontend_hosting" {
  source      = "./modules/s3"
  environment = var.environment
}


