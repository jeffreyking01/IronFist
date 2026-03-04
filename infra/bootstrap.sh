#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# IronFist — Terraform State Bootstrap
# Run this ONCE before `terraform init` to create the S3 bucket and
# DynamoDB table that Terraform uses to store and lock state.
#
# Prerequisites:
#   - AWS CLI configured with your personal account credentials
#   - Sufficient IAM permissions (S3, DynamoDB)
#
# Usage:
#   chmod +x bootstrap.sh
#   ./bootstrap.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="us-east-1"
BUCKET="ironfist-tfstate"
DYNAMO_TABLE="ironfist-tfstate-lock"

echo "→ Creating S3 state bucket: $BUCKET"
# us-east-1 does not accept LocationConstraint — other regions do
aws s3api create-bucket \
  --bucket "$BUCKET" \
  --region "$REGION"

echo "→ Enabling versioning on state bucket"
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

echo "→ Enabling AES-256 encryption on state bucket"
aws s3api put-bucket-encryption \
  --bucket "$BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

echo "→ Blocking all public access on state bucket"
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "→ Creating DynamoDB lock table: $DYNAMO_TABLE"
aws dynamodb create-table \
  --table-name "$DYNAMO_TABLE" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

echo ""
echo "✓ Bootstrap complete."
echo ""
echo "Next steps:"
echo "  1. cd infra/terraform"
echo "  2. cp terraform.tfvars.example terraform.tfvars"
echo "  3. Edit terraform.tfvars with your values"
echo "  4. terraform init"
echo "  5. terraform plan"
echo "  6. terraform apply"
