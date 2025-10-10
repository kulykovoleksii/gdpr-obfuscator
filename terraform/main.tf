terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
  }
}

provider "aws" {
  region = var.region
}

# --- S3 buckets ---
resource "aws_s3_bucket" "input" {
  bucket = var.input_bucket_name
}

resource "aws_s3_bucket_server_side_encryption_configuration" "input" {
  bucket = aws_s3_bucket.input.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "output" {
  bucket = var.output_bucket_name
}

resource "aws_s3_bucket_server_side_encryption_configuration" "output" {
  bucket = aws_s3_bucket.output.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# --- Secrets Manager secret for HMAC key ---
resource "aws_secretsmanager_secret" "obf_key" {
  name        = var.secret_name
  description = "HMAC key for GDPR Obfuscator"
}

# Generate a random value on first apply
resource "random_password" "hmac" {
  length  = 64
  special = false
}

resource "aws_secretsmanager_secret_version" "obf_key_v" {
  secret_id     = aws_secretsmanager_secret.obf_key.id
  secret_string = random_password.hmac.result
}

# --- IAM role for Lambda ---
data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

# Logging policy
data "aws_iam_policy_document" "logs" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

# S3 and Secrets permissions
data "aws_iam_policy_document" "app" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.input.arn}/*"]
  }
  
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.output.arn}/*"]
  }
  
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.obf_key.arn]
  }
}

resource "aws_iam_policy" "logs" {
  name   = "${var.name}-logs"
  policy = data.aws_iam_policy_document.logs.json
}

resource "aws_iam_policy" "app" {
  name   = "${var.name}-app"
  policy = data.aws_iam_policy_document.app.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.logs.arn
}

resource "aws_iam_role_policy_attachment" "app" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.app.arn
}

# --- S3 bucket for artifacts ---
resource "aws_s3_bucket" "artifacts" {
  bucket = var.artifacts_bucket_name
}

# --- Lambda function ---
resource "aws_lambda_function" "gdpr_obfuscator" {
  function_name = var.name
  role          = aws_iam_role.lambda.arn
  handler       = "gdpr_obfuscator.lambda_entry.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512

  s3_bucket = aws_s3_bucket.artifacts.id
  s3_key    = var.lambda_zip_key

  environment {
    variables = {
      LOG_LEVEL              = "INFO"
      OBFUSCATOR_SECRET_NAME = aws_secretsmanager_secret.obf_key.name
    }
  }
}