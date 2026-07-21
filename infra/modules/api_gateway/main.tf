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

# Method configuration for ANY requests on proxy path
resource "aws_api_gateway_method" "proxy_method" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

# Lambda integration with API Gateway proxy resource
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id             = aws_api_gateway_rest_api.serverless_api.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
}

# Root ANY method (for the base URL path)
resource "aws_api_gateway_method" "root_method" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  resource_id   = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

# Lambda integration with API Gateway root resource
resource "aws_api_gateway_integration" "lambda_integration_root" {
  rest_api_id             = aws_api_gateway_rest_api.serverless_api.id
  resource_id             = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method             = aws_api_gateway_method.root_method.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.lambda_invoke_arn
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
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.serverless_api.execution_arn}/*/*"
}
