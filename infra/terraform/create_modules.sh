#!/bin/bash
# Run from inside infra/terraform/
# Creates all module files in one shot.
set -euo pipefail

mkdir -p modules/vpc modules/alb modules/database modules/secrets modules/compute

# ══════════════════════════════════════════════════════════════════════════════
# VPC MODULE
# ══════════════════════════════════════════════════════════════════════════════
cat > modules/vpc/variables.tf << 'EOF'
variable "environment" { type = string }
variable "vpc_cidr"    { type = string }
EOF

cat > modules/vpc/outputs.tf << 'EOF'
output "vpc_id"             { value = aws_vpc.main.id }
output "public_subnet_ids"  { value = [aws_subnet.public.id, aws_subnet.public_2.id] }
output "private_subnet_ids" { value = [aws_subnet.private.id] }
output "nat_instance_id"    { value = aws_instance.nat.id }
EOF

cat > modules/vpc/main.tf << 'EOF'
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "ironfist-${var.environment}-vpc" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 1)
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags = { Name = "ironfist-${var.environment}-public-1" }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 3)
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true
  tags = { Name = "ironfist-${var.environment}-public-2" }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 2)
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = { Name = "ironfist-${var.environment}-private-1" }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "ironfist-${var.environment}-igw" }
}

data "aws_ami" "nat" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn-ami-vpc-nat-*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

resource "aws_security_group" "nat" {
  name        = "ironfist-${var.environment}-nat-sg"
  description = "NAT instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_subnet.private.cidr_block]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "ironfist-${var.environment}-nat-sg" }
}

resource "aws_instance" "nat" {
  ami                         = data.aws_ami.nat.id
  instance_type               = "t3.nano"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.nat.id]
  source_dest_check           = false
  associate_public_ip_address = true
  tags = { Name = "ironfist-${var.environment}-nat-instance" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "ironfist-${var.environment}-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_instance.nat.primary_network_interface_id
  }
  tags = { Name = "ironfist-${var.environment}-private-rt" }
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}
EOF

# ══════════════════════════════════════════════════════════════════════════════
# ALB MODULE
# ══════════════════════════════════════════════════════════════════════════════
cat > modules/alb/variables.tf << 'EOF'
variable "environment"       { type = string }
variable "vpc_id"            { type = string }
variable "public_subnet_ids" { type = list(string) }
EOF

cat > modules/alb/outputs.tf << 'EOF'
output "alb_dns_name"     { value = aws_lb.main.dns_name }
output "alb_sg_id"        { value = aws_security_group.alb.id }
output "target_group_arn" { value = aws_lb_target_group.app.arn }
EOF

cat > modules/alb/main.tf << 'EOF'
resource "aws_security_group" "alb" {
  name        = "ironfist-${var.environment}-alb-sg"
  description = "ALB inbound HTTP/HTTPS"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "ironfist-${var.environment}-alb-sg" }
}

resource "aws_lb" "main" {
  name               = "ironfist-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = { Name = "ironfist-${var.environment}-alb" }
}

resource "aws_lb_target_group" "app" {
  name     = "ironfist-${var.environment}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/api/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = { Name = "ironfist-${var.environment}-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "tls_private_key" "self_signed" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "self_signed" {
  private_key_pem = tls_private_key.self_signed.private_key_pem
  subject {
    common_name  = "ironfist.dev.local"
    organization = "IronFist Dev"
  }
  validity_period_hours = 8760
  allowed_uses = ["key_encipherment", "digital_signature", "server_auth"]
}

resource "aws_acm_certificate" "self_signed" {
  private_key      = tls_private_key.self_signed.private_key_pem
  certificate_body = tls_self_signed_cert.self_signed.cert_pem
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.self_signed.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

terraform {
  required_providers {
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}
EOF

# ══════════════════════════════════════════════════════════════════════════════
# DATABASE MODULE
# ══════════════════════════════════════════════════════════════════════════════
cat > modules/database/variables.tf << 'EOF'
variable "environment"        { type = string }
variable "vpc_id"             { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "app_sg_id"          { type = string }
variable "db_name"            { type = string }
variable "db_username"        { type = string }
EOF

cat > modules/database/outputs.tf << 'EOF'
output "db_endpoint" { value = aws_db_instance.main.endpoint }
output "db_password" {
  value     = random_password.db.result
  sensitive = true
}
output "db_sg_id" { value = aws_security_group.db.id }
EOF

cat > modules/database/main.tf << 'EOF'
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
  description = "RDS PostgreSQL — app server only"
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
EOF

# ══════════════════════════════════════════════════════════════════════════════
# SECRETS MODULE
# ══════════════════════════════════════════════════════════════════════════════
cat > modules/secrets/variables.tf << 'EOF'
variable "environment"  { type = string }
variable "db_password"  {
  type      = string
  sensitive = true
}
variable "db_endpoint"  { type = string }
variable "db_name"      { type = string }
variable "db_username"  { type = string }
EOF

cat > modules/secrets/outputs.tf << 'EOF'
output "secrets_arn"  { value = aws_secretsmanager_secret.app.arn }
output "secrets_name" { value = aws_secretsmanager_secret.app.name }
EOF

cat > modules/secrets/main.tf << 'EOF'
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
EOF

# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE MODULE
# ══════════════════════════════════════════════════════════════════════════════
cat > modules/compute/variables.tf << 'EOF'
variable "environment"           { type = string }
variable "vpc_id"                { type = string }
variable "private_subnet_ids"    { type = list(string) }
variable "public_subnet_ids"     { type = list(string) }
variable "alb_sg_id"             { type = string }
variable "alb_target_group_arn"  { type = string }
variable "secrets_arn"           { type = string }
variable "instance_type"         { type = string; default = "t3.small" }
variable "key_name"              { type = string }
EOF

cat > modules/compute/outputs.tf << 'EOF'
output "app_instance_id" { value = aws_instance.app.id }
output "app_private_ip"  { value = aws_instance.app.private_ip }
output "app_sg_id"       { value = aws_security_group.app.id }
EOF

cat > modules/compute/user_data.sh << 'EOF'
#!/bin/bash
set -euxo pipefail

dnf update -y
dnf install -y docker git awscli amazon-ssm-agent

systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

DOCKER_COMPOSE_VERSION="v2.27.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

mkdir -p /opt/ironfist
chown ec2-user:ec2-user /opt/ironfist

echo "IRONFIST_ENV=${environment}" > /opt/ironfist/.env.bootstrap
echo "SECRETS_ARN=${secrets_arn}"  >> /opt/ironfist/.env.bootstrap

echo "Bootstrap complete."
EOF

cat > modules/compute/main.tf << 'EOF'
resource "aws_iam_role" "app" {
  name = "ironfist-${var.environment}-app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "secrets_read" {
  name = "ironfist-${var.environment}-secrets-read"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
      Resource = [var.secrets_arn]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name = "ironfist-${var.environment}-app-profile"
  role = aws_iam_role.app.name
}

resource "aws_security_group" "app" {
  name        = "ironfist-${var.environment}-app-sg"
  description = "App server — inbound from ALB only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [var.alb_sg_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "ironfist-${var.environment}-app-sg" }
}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = var.private_subnet_ids[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name
  key_name               = var.key_name

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 20
    encrypted             = true
    delete_on_termination = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    environment = var.environment
    secrets_arn = var.secrets_arn
  }))

  tags = { Name = "ironfist-${var.environment}-app" }
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = var.alb_target_group_arn
  target_id        = aws_instance.app.id
  port             = 8000
}
EOF

echo ""
echo "✓ All module files created."
echo ""
echo "Next steps:"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"
