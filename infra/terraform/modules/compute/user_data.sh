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
