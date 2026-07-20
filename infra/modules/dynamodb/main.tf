resource "aws_dynamodb_table" "events" {
  name         = "alphapass-events-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "EventID"

  attribute {
    name = "EventID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Events Table"
  }
}

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
