locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_cognito_user_pool" "main" {
  name = "${local.name_prefix}-users"

  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${local.name_prefix}-web"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

resource "aws_s3_bucket" "web" {
  bucket = "${local.name_prefix}-web"
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket = aws_s3_bucket.web.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "notes" {
  name         = "${local.name_prefix}-notes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_secretsmanager_secret" "gmail_oauth" {
  name = "${local.name_prefix}/gmail-oauth"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/contextpad/${var.environment}/api"
  retention_in_days = 30
}
