variable "region"               { type = string }
variable "name"                 { type = string } # e.g. "gdpr-obfuscator"
variable "input_bucket_name"    { type = string }
variable "output_bucket_name"   { type = string }
variable "artifacts_bucket_name"{ type = string }
variable "secret_name"          { type = string } # e.g. "GDPR/ObfuscatorKey"
variable "lambda_zip_key"       { type = string } # path inside artifacts bucket
