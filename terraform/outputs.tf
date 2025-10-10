output "lambda_name"       { value = aws_lambda_function.gdpr_obfuscator.function_name }
output "input_bucket"      { value = aws_s3_bucket.input.bucket }
output "output_bucket"     { value = aws_s3_bucket.output.bucket }
output "artifacts_bucket"  { value = aws_s3_bucket.artifacts.bucket }
output "secret_arn"        { value = aws_secretsmanager_secret.obf_key.arn }
