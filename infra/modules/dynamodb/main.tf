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

resource "aws_dynamodb_table" "organizers" {
  name         = "alphapass-organizers-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "OrganizerID"

  attribute {
    name = "OrganizerID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Organizers Table"
  }
}

resource "aws_dynamodb_table" "admins" {
  name         = "alphapass-admins-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "AdminID"

  attribute {
    name = "AdminID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Admins Table"
  }
}

resource "aws_dynamodb_table" "orders" {
  name         = "alphapass-orders-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "OrderID"

  attribute {
    name = "OrderID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Orders Table"
  }
}

resource "aws_dynamodb_table" "tickets" {
  name         = "alphapass-tickets-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "TicketID"

  attribute {
    name = "TicketID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Tickets Table"
  }
}

resource "aws_dynamodb_table" "promo_codes" {
  name         = "alphapass-promo-codes-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "Code"

  attribute {
    name = "Code"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Promo Codes Table"
  }
}

resource "aws_dynamodb_table" "resale_listings" {
  name         = "alphapass-resale-listings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ListingID"

  attribute {
    name = "ListingID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Resale Listings Table"
  }
}

resource "aws_dynamodb_table" "transfers" {
  name         = "alphapass-transfers-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "TransferID"

  attribute {
    name = "TransferID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Ticket Transfers Table"
  }
}

resource "aws_dynamodb_table" "payouts" {
  name         = "alphapass-payouts-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PayoutID"

  attribute {
    name = "PayoutID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Organizer Payouts Table"
  }
}

resource "aws_dynamodb_table" "platform_settings" {
  name         = "alphapass-platform-settings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "SettingKey"

  attribute {
    name = "SettingKey"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Platform Settings Table"
  }
}

resource "aws_dynamodb_table" "audit_logs" {
  name         = "alphapass-audit-logs-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LogID"

  attribute {
    name = "LogID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Audit Logs Table"
  }
}

resource "aws_dynamodb_table" "event_categories" {
  name         = "alphapass-event-categories-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "CategoryID"

  attribute {
    name = "CategoryID"
    type = "S"
  }

  tags = {
    Name = "AlphaPass Event Categories Table"
  }
}
