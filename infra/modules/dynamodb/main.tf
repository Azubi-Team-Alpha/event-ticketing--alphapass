resource "aws_dynamodb_table" "events" {
  name         = "alphapass-events-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "EventID"

  attribute {
    name = "EventID"
    type = "S"
  }
  attribute {
    name = "organizer_id"
    type = "S"
  }
  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "organizer_id-index"
    hash_key        = "organizer_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
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
  attribute {
    name = "email"
    type = "S"
  }
  attribute {
    name = "verification_token"
    type = "S"
  }
  attribute {
    name = "reset_token"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "verification_token-index"
    hash_key        = "verification_token"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "reset_token-index"
    hash_key        = "reset_token"
    projection_type = "ALL"
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
  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
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
  attribute {
    name = "event_id"
    type = "S"
  }
  attribute {
    name = "guest_email"
    type = "S"
  }

  global_secondary_index {
    name            = "event_id-index"
    hash_key        = "event_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "guest_email-index"
    hash_key        = "guest_email"
    projection_type = "ALL"
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
  attribute {
    name = "ticket_code"
    type = "S"
  }
  attribute {
    name = "order_id"
    type = "S"
  }
  attribute {
    name = "attendee_email"
    type = "S"
  }

  global_secondary_index {
    name            = "ticket_code-index"
    hash_key        = "ticket_code"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "order_id-index"
    hash_key        = "order_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "attendee_email-index"
    hash_key        = "attendee_email"
    projection_type = "ALL"
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
  attribute {
    name = "event_id"
    type = "S"
  }

  global_secondary_index {
    name            = "event_id-index"
    hash_key        = "event_id"
    projection_type = "ALL"
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
  attribute {
    name = "ticket_id"
    type = "S"
  }
  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "ticket_id-index"
    hash_key        = "ticket_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    projection_type = "ALL"
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
  attribute {
    name = "ticket_id"
    type = "S"
  }

  global_secondary_index {
    name            = "ticket_id-index"
    hash_key        = "ticket_id"
    projection_type = "ALL"
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
  attribute {
    name = "organizer_id"
    type = "S"
  }

  global_secondary_index {
    name            = "organizer_id-index"
    hash_key        = "organizer_id"
    projection_type = "ALL"
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
