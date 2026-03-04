terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "ironfist-tfstate"   # created by bootstrap/bootstrap.sh
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "ironfist-tfstate-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "IronFist"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ── VPC ────────────────────────────────────────────────────────────────────────
module "vpc" {
  source      = "./modules/vpc"
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# ── ALB ────────────────────────────────────────────────────────────────────────
module "alb" {
  source            = "./modules/alb"
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
}

# ── DATABASE ───────────────────────────────────────────────────────────────────
module "database" {
  source             = "./modules/database"
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  app_sg_id          = module.compute.app_sg_id
  db_name            = var.db_name
  db_username        = var.db_username
}

# ── SECRETS ────────────────────────────────────────────────────────────────────
module "secrets" {
  source      = "./modules/secrets"
  environment = var.environment
  db_password = module.database.db_password
  db_endpoint = module.database.db_endpoint
  db_name     = var.db_name
  db_username = var.db_username
}

# ── COMPUTE ────────────────────────────────────────────────────────────────────
module "compute" {
  source              = "./modules/compute"
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  public_subnet_ids   = module.vpc.public_subnet_ids
  alb_sg_id           = module.alb.alb_sg_id
  alb_target_group_arn = module.alb.target_group_arn
  secrets_arn         = module.secrets.secrets_arn
  instance_type       = var.app_instance_type
  key_name            = var.key_name
}
