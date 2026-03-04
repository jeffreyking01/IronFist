# Stores all application secrets in a single JSON secret.
# App reads this at startup — no hardcoded credentials anywhere.
# Placeholder values for OpenAI and NVD keys — fill these in via AWS Console
# or with: aws secretsmanager update-secret --secret-id <arn> --secret-string '{...}'

resource "aws_secretsmanager_secret" "app" {
  name                    = "ironfist/${var.environment}/app-secrets"
  description             = "IronFist application secrets — DB, API keys, agent token"
  recovery_window_in_days = 0   # Immediate deletion in dev; set to 30 in prod

  tags = { Name = "ironfist-${var.environment}-secrets" }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id

  secret_string = jsonencode({
    # Database
    db_host     = var.db_endpoint
    db_port     = "5432"
    db_name     = var.db_name
    db_username = var.db_username
    db_password = var.db_password

    # External APIs — fill these in after first apply
    openai_api_key     = "REPLACE_ME"
    nvd_api_key        = "REPLACE_ME"

    # CMDB agent bearer token — generate a strong random string
    # e.g.: openssl rand -hex 32
    cmdb_agent_token   = "REPLACE_ME"
  })
}
