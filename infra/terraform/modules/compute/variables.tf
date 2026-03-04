variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "alb_sg_id" { type = string }
variable "alb_target_group_arn" { type = string }
variable "secrets_arn" { type = string }
variable "key_name" { type = string }

variable "instance_type" {
  type    = string
  default = "t3.small"
}
