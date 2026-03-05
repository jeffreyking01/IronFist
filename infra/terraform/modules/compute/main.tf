# ── IAM ROLE ───────────────────────────────────────────────────────────────────
# Allows the EC2 instance to read from Secrets Manager — no hardcoded creds
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

# SSM Session Manager — lets you shell into the instance without opening SSH port
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name = "ironfist-${var.environment}-app-profile"
  role = aws_iam_role.app.name
}

# ── SECURITY GROUP ─────────────────────────────────────────────────────────────
resource "aws_security_group" "app" {
  name        = "ironfist-${var.environment}-app-sg"
  description = "App server — inbound from ALB only, outbound to RDS and internet"
  vpc_id      = var.vpc_id

  # Only accept traffic from the ALB
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [var.alb_sg_id]
    description     = "FastAPI from ALB only"
  }

  # HTTPS inbound for CMDB agent (posts to /api/cmdb/ingest)
  # Agent comes in via ALB — this rule is here for clarity/documentation
  # No direct inbound needed; ALB handles it

  # Allow all outbound (to RDS, NAT → internet for API calls)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "ironfist-${var.environment}-app-sg" }
}

# ── AMI ────────────────────────────────────────────────────────────────────────
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

# ── EC2 INSTANCE ───────────────────────────────────────────────────────────────
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

  # Bootstrap script — installs Docker and Docker Compose on first boot
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    environment = var.environment
    secrets_arn = var.secrets_arn
  }))

  tags = { Name = "ironfist-${var.environment}-app" }
}

# ── ALB TARGET GROUP ATTACHMENT ────────────────────────────────────────────────
resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = var.alb_target_group_arn
  target_id        = aws_instance.app.id
  port             = 8000
}
