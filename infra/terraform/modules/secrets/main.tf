resource "aws_secretsmanager_secret" "app" {
  name                    = "ironfist/${var.environment}/app-secrets"
  description             = "IronFist app secrets"
  recovery_window_in_days = 0
  tags                    = { Name = "ironfist-${var.environment}-secrets" }
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    db_host          = var.db_endpoint
    db_port          = "5432"
    db_name          = var.db_name
    db_username      = var.db_username
    db_password      = var.db_password
    openai_api_key   = "REPLACE_ME"
    nvd_api_key      = "REPLACE_ME"
    cmdb_agent_token = "REPLACE_ME"
  })
}
