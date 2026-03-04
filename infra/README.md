# IronFist — Infrastructure

Terraform configuration for the IronFist personal AWS dev environment.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.6.0
- AWS CLI configured with your personal account (`aws configure`)
- An EC2 key pair already created in your AWS account (us-east-1)

## Structure

```
infra/
├── bootstrap/
│   └── bootstrap.sh          # Run once — creates S3 state bucket + DynamoDB lock table
└── terraform/
    ├── main.tf                # Root — wires all modules
    ├── variables.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    └── modules/
        ├── vpc/               # VPC, subnets, IGW, NAT instance, route tables
        ├── alb/               # Application Load Balancer, target group, self-signed cert
        ├── database/          # RDS PostgreSQL (db.t3.micro, private subnet)
        ├── secrets/           # Secrets Manager (DB creds, API keys, agent token)
        └── compute/           # EC2 app server, IAM role, security group, bootstrap
```

## First-Time Setup

### Step 1 — Bootstrap state storage (run once only)

```bash
cd infra/bootstrap
chmod +x bootstrap.sh
./bootstrap.sh
```

This creates:
- S3 bucket `ironfist-tfstate` — versioned, encrypted, no public access
- DynamoDB table `ironfist-tfstate-lock` — prevents concurrent applies

### Step 2 — Configure your variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` — at minimum, set your EC2 key pair name:

```hcl
key_name = "your-ec2-keypair-name"
```

> ⚠️ `terraform.tfvars` is gitignored — never commit it.

### Step 3 — Initialize and deploy

```bash
terraform init
terraform plan     # Review what will be created
terraform apply    # Type 'yes' to confirm
```

Apply takes approximately **8–12 minutes** (RDS takes longest).

### Step 4 — Update secrets

After apply, fill in your real API keys in Secrets Manager:

```bash
# Get the secret ARN from Terraform output
terraform output secrets_arn

# Update with your real keys
aws secretsmanager update-secret \
  --secret-id <secrets_arn> \
  --secret-string '{
    "db_host": "<from terraform output>",
    "db_port": "5432",
    "db_name": "ironfist",
    "db_username": "ironfist_admin",
    "db_password": "<from terraform output>",
    "openai_api_key": "sk-...",
    "nvd_api_key": "your-nvd-key",
    "cmdb_agent_token": "<openssl rand -hex 32>"
  }'
```

### Step 5 — Access the app server

The app server is in a private subnet — no public IP. Use SSM Session Manager (no SSH port needed):

```bash
# Get instance ID
terraform output app_instance_id

# Open a shell
aws ssm start-session --target <instance_id>

# Once in:
cd /opt/ironfist
# Deploy app containers here
```

### Step 6 — Access the application

```bash
terraform output alb_dns_name
# → ironfist-dev-alb-123456789.us-east-1.elb.amazonaws.com
```

Open that URL in your browser. You'll see a self-signed cert warning — click through for dev.

---

## Saving Money

**Stop the app server when not developing:**
```bash
aws ec2 stop-instances --instance-ids $(terraform output -raw app_instance_id)

# Start again when needed
aws ec2 start-instances --instance-ids $(terraform output -raw app_instance_id)
```

**Pause RDS when not in use:**
```bash
aws rds stop-db-instance --db-instance-identifier ironfist-dev-db
# Note: AWS auto-restarts RDS after 7 days
```

**Estimated cost with instance stopped:** < $20/month (RDS + ALB + misc)

---

## Tear Down

```bash
terraform destroy
```

> RDS snapshots are skipped (`skip_final_snapshot = true`) in dev. If you want a final backup before destroying, run a manual snapshot first.

---

## GovCloud Migration Notes

When migrating to GovCloud:
1. Replace NAT instance with `aws_nat_gateway` in `modules/vpc/main.tf`
2. Change `region` to `us-gov-east-1`
3. Update `backend` S3 bucket to a GovCloud bucket
4. Update `arn:aws:iam::` → `arn:aws-us-gov:iam::` in IAM policies
5. Add CloudTrail, Config, GuardDuty resources for FedRAMP Moderate controls
6. Set `deletion_protection = true` and `skip_final_snapshot = false` on RDS
