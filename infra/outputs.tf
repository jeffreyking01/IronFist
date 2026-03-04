output "alb_dns_name" {
  description = "ALB DNS name — use this to access IronFist in your browser"
  value       = module.alb.alb_dns_name
}

output "app_instance_id" {
  description = "EC2 instance ID of the app server"
  value       = module.compute.app_instance_id
}

output "app_private_ip" {
  description = "Private IP of the app server"
  value       = module.compute.app_private_ip
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.database.db_endpoint
  sensitive   = true
}

output "secrets_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = module.secrets.secrets_arn
}

output "nat_instance_id" {
  description = "EC2 instance ID of the NAT instance"
  value       = module.vpc.nat_instance_id
}
