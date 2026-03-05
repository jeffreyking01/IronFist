output "db_endpoint" { value = aws_db_instance.main.endpoint }
output "db_password" { value = random_password.db.result; sensitive = true }
output "db_sg_id"    { value = aws_security_group.db.id }
