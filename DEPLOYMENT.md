# AWS Deployment Guide - GDPR Obfuscator

Complete step-by-step guide for deploying GDPR Obfuscator to AWS Lambda.

---

## Prerequisites

- AWS Account
- AWS CLI installed
- Terraform >= 1.5.0
- Python 3.11

---

## Step 1: Configure AWS Credentials

### 1.1: Install AWS CLI
```bash
# macOS
brew install awscli

# Or download from https://aws.amazon.com/cli/
```

### 1.2: Create IAM User

1. Go to **AWS Console** → **IAM** → **Users** → **Create user**
2. User name: `gdpr-deployer`
3. **Permissions**: Attach policies directly
4. Add these policies:
   - `AmazonS3FullAccess`
   - `AWSLambda_FullAccess`
   - `IAMFullAccess`
   - `SecretsManagerReadWrite`
   - `CloudWatchLogsFullAccess`
5. Click **Create user**

### 1.3: Create Access Key

1. Click on created user → **Security credentials**
2. **Create access key** → Choose **CLI** → Next
3. **Download .csv file** ⚠️ Save securely!

### 1.4: Configure AWS CLI
```bash
aws configure

# Enter downloaded credentials:
AWS Access Key ID: AKIA...
AWS Secret Access Key: wJalr...
Default region name: eu-west-2
Default output format: json
```

### 1.5: Verify Setup
```bash
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDA...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/gdpr-deployer"
# }
```

✅ If you see your Account ID - credentials work!

---

## Step 2: Build Lambda Package
```bash
# Make build script executable
chmod +x scripts/build_lambda.sh

# Build package
./scripts/build_lambda.sh

# Expected output:
# Lambda package size: 10 MB
# Package size OK
# Lambda package 'function.zip' is ready.
```

✅ Check package exists:
```bash
ls -lh function.zip
# -rw-r--r--  1 user  staff    10M Jan 19 03:00 function.zip
```

---

## Step 3: Create Artifacts Bucket

Terraform cannot create the bucket it uploads to, so create it manually first.
```bash
# Choose UNIQUE bucket name (S3 names are globally unique!)
export ARTIFACTS_BUCKET="gdpr-artifacts-YOUR-NAME-12345"

# Create bucket
aws s3 mb s3://$ARTIFACTS_BUCKET --region eu-west-2

# Expected: make_bucket: gdpr-artifacts-YOUR-NAME-12345
```

### Upload Lambda Package
```bash
# Upload function.zip
aws s3 cp function.zip s3://$ARTIFACTS_BUCKET/releases/function.zip

# Verify
aws s3 ls s3://$ARTIFACTS_BUCKET/releases/
# Expected: 2025-01-19 ... function.zip
```

✅ Package uploaded!

---

## Step 4: Configure Terraform (3 min)
```bash
cd terraform

# Copy example config
cp terraform.tfvars.example terraform.tfvars

# Edit variables
nano terraform.tfvars
```

**Update with YOUR unique bucket names:**
```hcl
region                = "eu-west-2"
name                  = "gdpr-obfuscator"
input_bucket_name     = "gdpr-input-YOUR-NAME-12345"      # CHANGE!
output_bucket_name    = "gdpr-output-YOUR-NAME-12345"     # CHANGE!
artifacts_bucket_name = "gdpr-artifacts-YOUR-NAME-12345"  # From Step 3
secret_name           = "GDPR/ObfuscatorKey"
lambda_zip_key        = "releases/function.zip"
```

**Important:** Bucket names must be **globally unique**. Add your name + random numbers.

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## Step 5: Deploy Infrastructure (5 min)

### 5.1: Initialize Terraform
```bash
terraform init

# Expected output:
# Terraform has been successfully initialized!
```

### 5.2: Review Plan
```bash
terraform plan

# Expected output:
# Plan: 15 to add, 0 to change, 0 to destroy
```

Review what will be created:
- Lambda function
- S3 buckets (input, output)
- Secrets Manager secret
- IAM roles and policies
- CloudWatch Logs

### 5.3: Apply Changes
```bash
terraform apply

# Type: yes
```

**Deployment time:** 2-3 minutes

### 5.4: Verify Outputs
```bash
terraform output

# Expected:
# artifacts_bucket = "gdpr-artifacts-YOUR-NAME-12345"
# input_bucket = "gdpr-input-YOUR-NAME-12345"
# lambda_name = "gdpr-obfuscator"
# output_bucket = "gdpr-output-YOUR-NAME-12345"
# secret_arn = "arn:aws:secretsmanager:..."
```

✅ **Deployment complete!**

---

## Step 6: Test Deployment (5 min)

### 6.1: Generate Test Data
```bash
# Return to project root
cd ..

# Generate small test file (100 rows)
python tools/generate_test_data.py 100

# Check file
head -5 data.csv
```

### 6.2: Upload to Input Bucket
```bash
# Replace with YOUR bucket name!
aws s3 cp data.csv s3://gdpr-input-YOUR-NAME-12345/test-input.csv

# Verify
aws s3 ls s3://gdpr-input-YOUR-NAME-12345/
```

### 6.3: Create Lambda Event

Create `test-event.json`:
```bash
cat > test-event.json << 'EOF'
{
  "s3_uri": "s3://gdpr-input-YOUR-NAME-12345/test-input.csv",
  "fields": ["email", "phone"],
  "primary_key": "id",
  "target_s3_uri": "s3://gdpr-output-YOUR-NAME-12345/test-output.csv"
}
EOF
```

⚠️ **Replace bucket names with YOUR actual names!**

### 6.4: Invoke Lambda
```bash
aws lambda invoke \
  --function-name gdpr-obfuscator \
  --payload file://test-event.json \
  --region eu-west-2 \
  response.json

# Check response
cat response.json
```

**Expected response:**
```json
{"status": "ok", "uploaded": true, "target": "s3://gdpr-output-YOUR-NAME-12345/test-output.csv"}
```

✅ Lambda executed successfully!

### 6.5: Verify Output
```bash
# Download obfuscated file
aws s3 cp s3://gdpr-output-YOUR-NAME-12345/test-output.csv output.csv

# Check result
head -10 output.csv
```

**Expected output:**
```csv
id,full_name,email,phone,address,age
1,User1 Test,a3f2e1d4c5b6a789,b6a7891c2d3e4f50,1 Baker St...
```

✅ **Email and phone are replaced with hex tokens!**

---

## Monitoring & Debugging

### View CloudWatch Logs
```bash
# Stream logs in real-time
aws logs tail /aws/lambda/gdpr-obfuscator --follow --region eu-west-2
```

**Or in AWS Console:**
1. CloudWatch → Log groups
2. `/aws/lambda/gdpr-obfuscator`

### Check Lambda Metrics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=gdpr-obfuscator \
  --start-time 2025-01-19T00:00:00Z \
  --end-time 2025-01-19T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region eu-west-2
```

### Verify Secret
```bash
# Check secret exists (don't print value in production!)
aws secretsmanager describe-secret \
  --secret-id GDPR/ObfuscatorKey \
  --region eu-west-2
```

---

## Troubleshooting

### Error: "Bucket name already exists"

**Problem:** S3 bucket names are globally unique across all AWS accounts.

**Solution:**
```bash
# Edit terraform.tfvars with MORE unique names:
input_bucket_name = "gdpr-input-yourname-abc123xyz"
output_bucket_name = "gdpr-output-yourname-abc123xyz"
```

Then re-run:
```bash
terraform apply
```

### Error: "AccessDenied" when invoking Lambda

**Problem:** Lambda role lacks S3 permissions.

**Solution:**
```bash
# Verify IAM policies attached
aws iam list-attached-role-policies \
  --role-name gdpr-obfuscator-lambda-role

# Should show policies for S3, Secrets Manager, etc.
# If missing, re-run:
terraform apply
```

### Error: "Function not found"

**Problem:** function.zip was not uploaded or Lambda creation failed.

**Solution:**
```bash
# Check if ZIP exists in S3
aws s3 ls s3://gdpr-artifacts-YOUR-NAME-12345/releases/

# If missing, re-upload:
aws s3 cp function.zip s3://gdpr-artifacts-YOUR-NAME-12345/releases/function.zip

# Force Lambda update:
cd terraform
terraform apply -replace=aws_lambda_function.gdpr_obfuscator
```

### Lambda Timeout

**Problem:** Processing large file takes >60 seconds.

**Solution:** Increase timeout in `terraform/main.tf`:
```hcl
resource "aws_lambda_function" "gdpr_obfuscator" {
  # ...
  timeout     = 300  # 5 minutes instead of 60 seconds
  memory_size = 1024 # 1GB instead of 512MB
}
```

Then apply:
```bash
terraform apply
```

---

## Security Best Practices

### Secrets Management

✅ **DO:**
- Store HMAC key in Secrets Manager
- Use IAM roles (no hardcoded keys)
- Enable S3 bucket encryption
- Rotate access keys every 90 days

❌ **DON'T:**
- Commit credentials to Git
- Share access keys
- Log sensitive data
- Use root account for deployment

### IAM Permissions

Current deployment uses `*FullAccess` policies for simplicity.

**For production**, create custom policies with least-privilege:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::gdpr-input-*/*",
        "arn:aws:s3:::gdpr-output-*/*"
      ]
    }
  ]
}
```

---

## Cost Estimation

**Monthly costs for light usage:**

- Lambda: $0.00 (Free tier: 1M requests/month)
- S3 Storage: ~$0.01 (few GB)
- S3 Requests: ~$0.01
- Secrets Manager: $0.40/secret
- CloudWatch Logs: ~$0.50

**Total: ~$1-2/month** for development/testing

**Production costs scale with:**
- Number of Lambda invocations
- S3 storage size
- Data transfer

---

## Cleanup (Remove Everything)

When done testing:
```bash
# Delete all files from buckets
aws s3 rm s3://gdpr-input-YOUR-NAME-12345 --recursive
aws s3 rm s3://gdpr-output-YOUR-NAME-12345 --recursive
aws s3 rm s3://gdpr-artifacts-YOUR-NAME-12345 --recursive

# Destroy infrastructure
cd terraform
terraform destroy

# Type: yes

# Expected: All resources destroyed
```

⚠️ **This deletes everything!** Make sure to backup any important data first.

---

## Production Deployment Checklist

Before deploying to production:

- [ ] Use custom IAM policies (not *FullAccess)
- [ ] Enable MFA for AWS account
- [ ] Set up CloudWatch Alarms
- [ ] Configure VPC for Lambda (if needed)
- [ ] Enable S3 versioning
- [ ] Set up backup/disaster recovery
- [ ] Document runbook for incidents
- [ ] Test with production-size data
- [ ] Review security with team
- [ ] Get approval from security/compliance

---

## Next Steps

### Automation

1. **EventBridge** - Auto-trigger on S3 upload
2. **Step Functions** - Multi-step workflows
3. **CI/CD** - GitHub Actions deployment

See example EventBridge rule:
```bash
# Create rule to trigger Lambda on S3 upload
aws events put-rule \
  --name gdpr-obfuscator-trigger \
  --event-pattern '{
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {
      "bucket": {
        "name": ["gdpr-input-YOUR-NAME-12345"]
      }
    }
  }'
```

### Monitoring

Set up CloudWatch Dashboard for:
- Lambda invocations
- Error rates
- Processing duration
- S3 storage metrics

---

## Support

**Issues?** Check:
1. CloudWatch Logs for errors
2. IAM permissions
3. S3 bucket names are unique
4. Terraform state is not corrupted

**For questions:**
- Review README.md
- Check EXTENSION_PLAN.md for future features
- AWS Documentation: https://docs.aws.amazon.com

---

## Summary

You've successfully deployed GDPR Obfuscator to AWS! 🎉

**What's working:**
- ✅ Lambda function processes CSV files
- ✅ S3 buckets with encryption
- ✅ Secrets Manager stores HMAC key
- ✅ PII is replaced with deterministic tokens
- ✅ Complete infrastructure as code

**Architecture:**
```
S3 Input Bucket → Lambda Function → S3 Output Bucket
                      ↓
                Secrets Manager (HMAC key)
                      ↓
                CloudWatch Logs
```

Ready for production after security review and proper IAM policies! 🚀