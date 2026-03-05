output "vpc_id"             { value = aws_vpc.main.id }
output "public_subnet_ids"  { value = [aws_subnet.public.id, aws_subnet.public_2.id] }
output "private_subnet_ids" { value = [aws_subnet.private.id] }
output "nat_instance_id"    { value = aws_instance.nat.id }
