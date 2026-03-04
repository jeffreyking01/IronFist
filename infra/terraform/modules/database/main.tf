resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%^&*()-_=+[]{}|;:,.<>?"
}

resource "aws_db_subnet_group" "main" {
  name       = "ironfist-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = { Name = "ironfist-${var.environment}-db-subnet-group" }
}

resource "aws_security_group" "db" {
  name        = "ironfist-${var.environment}-db-sg"
  description = "RDS PostgreSQL - app server only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_sg_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "ironfist-${var.environment}-db-sg" }
}

resource "aws_db_parameter_group" "main" {
  name   = "ironfist-${var.environment}-pg16"
  family = "postgres16"
  parameter {
    name  = "log_connections"
    value = "1"
  }
  parameter {
    name  = "log_disconnections"
    value = "1"
  }
  tags = { Name = "ironfist-${var.environment}-pg16" }
}

resource "aws_db_instance" "main" {
  identifier        = "ironfist-${var.environment}-db"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  deletion_protection     = false
  skip_final_snapshot     = true
  parameter_group_name    = aws_db_parameter_group.main.name

  tags = { Name = "ironfist-${var.environment}-db" }
}

terraform {
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
