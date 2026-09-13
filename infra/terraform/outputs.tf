output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "web_bucket_name" {
  value = aws_s3_bucket.web.bucket
}

output "notes_table_name" {
  value = aws_dynamodb_table.notes.name
}

output "api_log_group_name" {
  value = aws_cloudwatch_log_group.api.name
}
