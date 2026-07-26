resource "aws_api_gateway_rest_api" "serverless_api" {
  name        = "alphapass-serverless-api-${var.environment}"
  description = "API Gateway endpoint routing to AlphaPass Lambda backend"

  binary_media_types = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp"
  ]

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

# --- Dedicated OPTIONS Method for Proxy Path (Preflight CORS 0ms Mock) ---
resource "aws_api_gateway_method" "options_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_proxy_integration" {
  rest_api_id          = aws_api_gateway_rest_api.serverless_api.id
  resource_id          = aws_api_gateway_resource.proxy.id
  http_method          = aws_api_gateway_method.options_proxy.http_method
  type                 = "MOCK"
  passthrough_behavior = "WHEN_NO_MATCH"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_proxy_response" {
  rest_api_id = aws_api_gateway_rest_api.serverless_api.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.options_proxy.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_proxy_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.serverless_api.id
  resource_id = aws_api_gateway_resource.proxy.id
  http_method = aws_api_gateway_method.options_proxy.http_method
  status_code = aws_api_gateway_method_response.options_proxy_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept,Origin'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE,PATCH'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [
    aws_api_gateway_integration.options_proxy_integration
  ]
}

# --- Dedicated OPTIONS Method for Root Path (Preflight CORS 0ms Mock) ---
resource "aws_api_gateway_method" "options_root" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  resource_id   = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_root_integration" {
  rest_api_id          = aws_api_gateway_rest_api.serverless_api.id
  resource_id          = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method          = aws_api_gateway_method.options_root.http_method
  type                 = "MOCK"
  passthrough_behavior = "WHEN_NO_MATCH"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_root_response" {
  rest_api_id = aws_api_gateway_rest_api.serverless_api.id
  resource_id = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method = aws_api_gateway_method.options_root.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_root_integration_response" {
  rest_api_id = aws_api_gateway_rest_api.serverless_api.id
  resource_id = aws_api_gateway_rest_api.serverless_api.root_resource_id
  http_method = aws_api_gateway_method.options_root.http_method
  status_code = aws_api_gateway_method_response.options_root_response.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept,Origin'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE,PATCH'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [
    aws_api_gateway_integration.options_root_integration
  ]
}

# --- API Gateway Deployment ---
resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda_integration,
    aws_api_gateway_integration.lambda_integration_root,
    aws_api_gateway_integration_response.options_proxy_integration_response,
    aws_api_gateway_integration_response.options_root_integration_response
  ]

  rest_api_id = aws_api_gateway_rest_api.serverless_api.id

  triggers = {
    redeployment = sha256(jsonencode([
      aws_api_gateway_rest_api.serverless_api.binary_media_types,
      aws_api_gateway_resource.proxy.id,
      aws_api_gateway_method.proxy_method.id,
      aws_api_gateway_integration.lambda_integration.id,
      aws_api_gateway_integration_response.options_proxy_integration_response.id,
      aws_api_gateway_integration_response.options_root_integration_response.id
    ]))
  }

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

# Default throttling to protect Lambda from traffic spikes
resource "aws_api_gateway_method_settings" "throttle" {
  rest_api_id = aws_api_gateway_rest_api.serverless_api.id
  stage_name  = aws_api_gateway_stage.stage.stage_name
  method_path = "*/*"

  settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

# Permission to allow API Gateway to invoke Lambda
resource "aws_lambda_permission" "apigw_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.serverless_api.execution_arn}/*/*"
}

# Gateway Response for 4XX with CORS Headers
resource "aws_api_gateway_gateway_response" "response_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'*'"
  }
}

# Gateway Response for 5XX with CORS Headers
resource "aws_api_gateway_gateway_response" "response_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'*'"
  }
}

# Gateway Response for UNAUTHORIZED (401) with CORS Headers
resource "aws_api_gateway_gateway_response" "response_unauthorized" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  response_type = "UNAUTHORIZED"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'*'"
  }
}

# Gateway Response for ACCESS_DENIED (403) with CORS Headers
resource "aws_api_gateway_gateway_response" "response_access_denied" {
  rest_api_id   = aws_api_gateway_rest_api.serverless_api.id
  response_type = "ACCESS_DENIED"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'*'"
  }
}
