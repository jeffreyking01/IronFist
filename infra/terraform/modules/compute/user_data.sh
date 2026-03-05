#!/bin/bash
set -euxo pipefail

# ── System update ──────────────────────────────────────────────────────────────
dnf update -y

# ── Install Docker ─────────────────────────────────────────────────────────────
dnf install -y docker git
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ── Install Docker Compose v2 ──────────────────────────────────────────────────
DOCKER_COMPOSE_VERSION="v2.27.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── Install AWS CLI (for Secrets Manager access) ───────────────────────────────
dnf install -y awscli

# ── Install SSM agent (for Session Manager shell access — no SSH port needed) ──
dnf install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# ── Create app directory ───────────────────────────────────────────────────────
mkdir -p /opt/ironfist
chown ec2-user:ec2-user /opt/ironfist

# ── Write environment marker ───────────────────────────────────────────────────
echo "IRONFIST_ENV=${environment}" > /opt/ironfist/.env.bootstrap
echo "SECRETS_ARN=${secrets_arn}"  >> /opt/ironfist/.env.bootstrap

# ── Clone repo (update URL if repo is private — use deploy key or HTTPS token) ─
# Uncomment and update when you're ready to auto-deploy:
# git clone https://github.com/jeffreyking01/IronFist.git /opt/ironfist/app

echo "Bootstrap complete. Docker and dependencies installed."
echo "Next: deploy app via docker compose up from /opt/ironfist"
