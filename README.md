# GDPR Obfuscator

A production-ready tool for obfuscating personally identifiable information (PII) in data files stored on AWS S3.

## Current Implementation Status

| Format | Status | Notes |
|--------|--------|-------|
| **CSV** | ✅ Implemented | Fully functional, tested, production-ready |
| **JSON** | 🔄 Planned | Architecture ready, implementation pending |
| **JSONL** | 🔄 Planned | Architecture ready, implementation pending |
| **Parquet** | 🔄 Planned | Architecture ready, implementation pending |

**MVP Focus**: CSV format (fully working)  
**Architecture**: Designed for multi-format support using adapter pattern

---

## What is this

This tool creates a copy of CSV files and replaces personal data with safe, deterministic tokens using HMAC-SHA256. The obfuscated data is suitable for analytics while maintaining GDPR compliance.

### Key Features

- ✅ **Deterministic obfuscation**: Same input always produces same token (allows joins)
- ✅ **Streaming processing**: Low memory footprint, handles large files
- ✅ **AWS-native**: Designed for Lambda, ECS, or EC2 deployment
- ✅ **Security-first**: No credentials in code, uses AWS Secrets Manager
- ✅ **Well-tested**: Unit tests with >90% coverage, security scans
- ✅ **PEP-8 compliant**: Linted with flake8, type-checked with mypy

---

## How This Works (Simple Steps)

1. Download CSV from S3 (or open local file)
2. For each row, replace sensitive columns with HMAC token
3. Save result as bytes (ready for S3 upload) or to local file

**Example (Token mode - default):**
```
Input:  id=1, email=alice@example.com, phone=555-1234
Output: id=1, email=a3f2e1d4c5b6a789, phone=b6a7891c2d3e4f50
```

**Example (Mask mode):**
```
Input:  id=1, email=alice@example.com, phone=555-1234
Output: id=1, email=***, phone=***
```

---

## Quick Start

### 1. Setup Local Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

### 2. Generate Secret Key

```bash
# Generate a secure random key
export OBFUSCATOR_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Verify it's set
echo $OBFUSCATOR_KEY
```

### 3. Run CLI (Local Testing)

```bash
# Token mode (default) - deterministic HMAC tokens
python -m gdpr_obfuscator.cli \
  --input data.csv \
  --output data.obf.csv \
  --fields email,phone \
  --pk id

# Mask mode - fixed string (***) for all values
python -m gdpr_obfuscator.cli \
  --input data.csv \
  --output data.masked.csv \
  --fields email,phone \
  --pk id \
  --mask

# Custom mask token
python -m gdpr_obfuscator.cli \
  --input data.csv \
  --output data.masked.csv \
  --fields email,phone \
  --pk id \
  --mask \
  --mask-token "REDACTED"
```

**CLI Arguments:**
- `--input`: Input file path (required)
- `--output`: Output file path (required)
- `--fields`: Comma-separated list of sensitive fields (required)
- `--pk`: Primary key field name (default: `id`)
- `--format`: File format - `csv`, `json`, `jsonl`, `parquet` (default: auto-detect)
- `--mask`: Use fixed mask instead of deterministic tokens
- `--mask-token`: Custom mask string (default: `***`)
- `--token-length`: Length of hex tokens in token mode (default: 16)

---

## File Format Support

### CSV Format (✅ Implemented)

**Input Example** (`data.csv`):
```csv
id,full_name,email,phone
1,Alice Smith,alice@example.com,555-1234
2,Bob Jones,bob@example.com,555-5678
```

**Command (Token mode - default):**
```bash
python -m gdpr_obfuscator.cli \
  --input data.csv \
  --output data.obf.csv \
  --fields email,phone
```

**Output Example** (`data.obf.csv`):
```csv
id,full_name,email,phone
1,Alice Smith,a3f2e1d4c5b6a789,b6a7891c2d3e4f50
2,Bob Jones,c5d6e7f8a9b0c1d2,d3e4f5a6b7c8d9e0
```

**Command (Mask mode):**
```bash
python -m gdpr_obfuscator.cli \
  --input data.csv \
  --output data.masked.csv \
  --fields email,phone \
  --mask
```

**Output Example** (`data.masked.csv`):
```csv
id,full_name,email,phone
1,Alice Smith,***,***
2,Bob Jones,***,***
```

### JSON Format (🔄 Planned)

**Architecture is ready**. When implemented, will support:

```json
[
  {"id": 1, "name": "Alice", "email": "alice@example.com"},
  {"id": 2, "name": "Bob", "email": "bob@example.com"}
]
```

**Usage (when implemented):**
```bash
python -m gdpr_obfuscator.cli \
  --input data.json \
  --output data.obf.json \
  --fields email \
  --format json
```

**Current behavior**: Raises `NotImplementedError` with helpful message:
```
NotImplementedError: JSON format support is not yet implemented.
Currently only CSV format is supported.
See EXTENSION_PLAN.md for implementation details.
```

### JSONL Format (🔄 Planned)

Line-delimited JSON for large streaming datasets.

### Parquet Format (🔄 Planned)

Columnar format, requires `pyarrow` dependency.

---

## Architecture

### Multi-Format Support via Adapter Pattern

```
┌─────────────────────┐
│  Input File         │
│  (CSV/JSON/Parquet) │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────┐
│  Format Detection        │
│  - Auto-detect extension │
│  - Or explicit parameter │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Format Adapter          │
│  ┌────────────────────┐  │
│  │ CSVAdapter    ✅   │  │
│  │ JSONAdapter   🔄   │  │
│  │ ParquetAdapter 🔄  │  │
│  └────────────────────┘  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Core Obfuscation        │
│  obfuscate_value()       │
│  - HMAC-SHA256           │
│  - Deterministic tokens  │
└──────────┬───────────────┘
           │
           ▼
┌─────────────────────┐
│  Output File        │
│  (same format)      │
└─────────────────────┘
```

**Key Design Principles:**
1. **Separation of concerns**: Format handling separate from obfuscation logic
2. **Open/Closed principle**: Open for extension (new formats), closed for modification (core logic)
3. **Backward compatibility**: Existing CSV functions continue to work unchanged

---

## Project Structure

```
gdpr-obfuscator/
├── src/gdpr_obfuscator/
│   ├── __init__.py
│   ├── obfuscator.py           # Core HMAC obfuscation logic
│   ├── format_adapters.py      # Adapter pattern for formats
│   ├── s3_adapter.py            # S3 download/upload
│   ├── handler.py               # Integration wrapper
│   ├── lambda_entry.py          # AWS Lambda handler
│   └── cli.py                   # Command-line interface
├── tests/
│   ├── test_obfuscator.py       # Core logic tests
│   ├── test_format_adapters.py  # Format adapter tests
│   ├── test_s3_adapter.py       # S3 integration tests
│   └── test_handler.py          # Handler tests
├── terraform/                   # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── scripts/
│   └── build_lambda.sh          # Build Lambda deployment package
├── tools/
│   └── generate_test_data.py    # Generate large CSV for testing
├── requirements-dev.txt         # Development dependencies
├── requirements-runtime.txt     # Runtime dependencies (minimal)
├── pytest.ini
├── pyproject.toml
├── README.md                    # This file
└── EXTENSION_PLAN.md            # Detailed implementation plan for formats
```

---

## Running Tests

```bash
# Run all tests with coverage
pytest -v --cov=gdpr_obfuscator --cov-report=term-missing

# Run specific test file
pytest tests/test_obfuscator.py -v

# Run with detailed output
pytest -vv

# Check format adapter behavior
pytest tests/test_format_adapters.py -v
```

**Test Coverage:** >90% for core modules

---

## Security & Quality

### Security Scanning

```bash
# Run all security checks
make security

# Individual scans
bandit -r src -c .bandit           # Code security scan
pip-audit --skip-editable          # Dependency vulnerabilities
```

### Code Quality

```bash
# Linting
flake8 src tests

# Type checking
mypy src

# Format code
black src tests
```

### CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push:
- ✅ Unit tests with coverage
- ✅ Linting (flake8)
- ✅ Type checking (mypy)
- ✅ Security scans (bandit, pip-audit)
- ✅ Lambda package build and size check

---

## AWS Deployment

### Lambda Deployment

```bash
# Build Lambda package
./scripts/build_lambda.sh

# Output: function.zip (~10MB for MVP)
```

### Terraform Deployment

```bash
cd terraform

# Copy example config
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars

# Deploy infrastructure
terraform init
terraform plan
terraform apply
```

**What gets deployed:**
- Lambda function with Python 3.11 runtime
- Input/output S3 buckets with encryption
- Secrets Manager secret for HMAC key
- IAM roles with least-privilege permissions
- CloudWatch logs

### Lambda Invocation

**Event format (Token mode - default):**
```json
{
  "s3_uri": "s3://input-bucket/data.csv",
  "fields": ["email", "phone", "ssn"],
  "primary_key": "id",
  "target_s3_uri": "s3://output-bucket/data.obf.csv"
}
```

**Event format (Mask mode):**
```json
{
  "s3_uri": "s3://input-bucket/data.csv",
  "fields": ["email", "phone", "ssn"],
  "primary_key": "id",
  "target_s3_uri": "s3://output-bucket/data.masked.csv",
  "mode": "mask"
}
```

**Event format (Custom mask token):**
```json
{
  "s3_uri": "s3://input-bucket/data.csv",
  "fields": ["email", "phone"],
  "primary_key": "id",
  "target_s3_uri": "s3://output-bucket/data.redacted.csv",
  "mode": "mask",
  "mask_token": "REDACTED"
}
```

**Event Parameters:**
- `s3_uri` (required): Source file S3 URI
- `fields` (required): Array of sensitive field names
- `primary_key` (optional): Primary key field, default: `"id"`
- `target_s3_uri` (optional): Destination S3 URI for output
- `mode` (optional): `"token"` (default) or `"mask"`
- `mask_token` (optional): Custom mask string, default: `"***"`

**Response:**
```json
{
  "status": "ok",
  "uploaded": true,
  "target": "s3://output-bucket/data.obf.csv"
}
```

**Testing Lambda locally:**
```bash
# Token mode (default)
cat > test-event-token.json << 'EOF'
{
  "s3_uri": "s3://input-bucket/data.csv",
  "fields": ["email", "phone"],
  "primary_key": "id",
  "target_s3_uri": "s3://output-bucket/data.obf.csv"
}
EOF

aws lambda invoke \
  --function-name gdpr-obfuscator \
  --payload file://test-event-token.json \
  --cli-binary-format raw-in-base64-out \
  --region eu-west-2 \
  response.json

# Mask mode
cat > test-event-mask.json << 'EOF'
{
  "s3_uri": "s3://input-bucket/data.csv",
  "fields": ["email", "phone"],
  "primary_key": "id",
  "target_s3_uri": "s3://output-bucket/data.masked.csv",
  "mode": "mask"
}
EOF

aws lambda invoke \
  --function-name gdpr-obfuscator \
  --payload file://test-event-mask.json \
  --cli-binary-format raw-in-base64-out \
  --region eu-west-2 \
  response.json
```

---

## Generate Test Data

```bash
# Generate 1 million rows (for performance testing)
python tools/generate_test_data.py 1000000

# Generate smaller dataset for quick tests
python tools/generate_test_data.py 10000
```

Output: `data.csv` with columns: `id`, `full_name`, `email`, `phone`, `address`, `age`

---

## Performance

### Benchmarks (Tested on MacBook Pro M1)

| Rows | File Size | Processing Time | Throughput |
|------|-----------|-----------------|------------|
| 10,000 | 805 KB | 0.22s | ~45,000 rows/sec |
| 100,000 | 8.2 MB | 0.69s | ~145,000 rows/sec |

**Test command:**
```bash
# Generate test data
python tools/generate_test_data.py 100000

# Benchmark obfuscation
time python -m gdpr_obfuscator.cli \
  --input data.csv \
  --output data.obf.csv \
  --fields email,phone \
  --pk id
```

**Memory usage:**
- Streaming processing: O(1) memory
- Peak memory: ~50MB (constant, regardless of file size)
- No loading entire file into memory

**Lambda configuration:**
- Memory: 512MB
- Timeout: 60 seconds
- Runtime: Python 3.11
- Expected processing: ~1M rows in <10 seconds

---

## Multi-Format Extension

### Current Status

The codebase is **architecturally ready** for JSON and Parquet formats using the adapter pattern. The core obfuscation logic (`obfuscate_value()`) is format-agnostic.

**What's implemented:**
- ✅ Format adapter interface (`FormatAdapter` abstract base class)
- ✅ CSV adapter (fully functional)
- ✅ JSON adapter (stub with clear error message)
- ✅ Parquet adapter (stub with clear error message)
- ✅ Format auto-detection from filename
- ✅ Tests for adapter pattern and stubs

**What's needed for JSON:**
- Implement `JSONAdapter.process_stream()` using Python's `json` module
- Support both JSON arrays and JSONL (line-delimited) formats
- Add tests for JSON processing
- Update documentation

**What's needed for Parquet:**
- Add `pyarrow` dependency (~30MB)
- Implement `ParquetAdapter.process_stream()`
- Handle Lambda deployment (layer or container image)
- Add tests for Parquet processing

**Detailed implementation plan**: See [EXTENSION_PLAN.md](EXTENSION_PLAN.md)

**Estimated effort**: 3-5 days for both JSON and Parquet

---

## API Usage Examples

### Python API (Library Usage)

```python
from gdpr_obfuscator import s3_adapter
import os

# Set secret key
os.environ['OBFUSCATOR_KEY'] = 'your-secret-key'

# Token mode (default) - Process S3 CSV and upload result
s3_adapter.process_and_upload(
    source_s3_uri='s3://input-bucket/data.csv',
    target_s3_uri='s3://output-bucket/data.obf.csv',
    sensitive_fields=['email', 'phone', 'ssn'],
    primary_key_field='user_id'
)

# Mask mode - Replace with fixed string
s3_adapter.process_and_upload(
    source_s3_uri='s3://input-bucket/data.csv',
    target_s3_uri='s3://output-bucket/data.masked.csv',
    sensitive_fields=['email', 'phone'],
    primary_key_field='user_id',
    mode='mask'
)

# Custom mask token
s3_adapter.process_and_upload(
    source_s3_uri='s3://input-bucket/data.csv',
    target_s3_uri='s3://output-bucket/data.redacted.csv',
    sensitive_fields=['email', 'phone'],
    primary_key_field='user_id',
    mode='mask',
    mask_token='REDACTED'
)

# Or get bytes without uploading
result_bytes = s3_adapter.process_s3_file_to_bytes(
    s3_uri='s3://bucket/data.csv',
    sensitive_fields=['email'],
    primary_key_field='id',
    mode='token'  # or 'mask'
)
```

### Local File Processing

```python
from gdpr_obfuscator.obfuscator import obfuscate_stream
import os

os.environ['OBFUSCATOR_KEY'] = 'your-secret-key'

# Token mode (default)
with open('input.csv', 'rb') as fin, open('output.csv', 'wb') as fout:
    obfuscate_stream(
        input_stream=fin,
        output_stream=fout,
        sensitive_fields=['email', 'phone'],
        file_format='csv',
        primary_key_field='id'
    )

# Mask mode
with open('input.csv', 'rb') as fin, open('masked.csv', 'wb') as fout:
    obfuscate_stream(
        input_stream=fin,
        output_stream=fout,
        sensitive_fields=['email', 'phone'],
        file_format='csv',
        primary_key_field='id',
        mode='mask'
    )

# Custom mask token
with open('input.csv', 'rb') as fin, open('redacted.csv', 'wb') as fout:
    obfuscate_stream(
        input_stream=fin,
        output_stream=fout,
        sensitive_fields=['email', 'phone'],
        file_format='csv',
        primary_key_field='id',
        mode='mask',
        mask_token='REDACTED'
    )
```

---

## Security Notes

### Key Management

**Development/Testing:**
```bash
export OBFUSCATOR_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

**Production (AWS):**
- Store key in AWS Secrets Manager
- Lambda reads from Secrets Manager at runtime
- IAM role grants `secretsmanager:GetSecretValue` permission
- Key is never logged or exposed

### Important Security Rules

1. ❌ **NEVER** commit `OBFUSCATOR_KEY` to git
2. ❌ **NEVER** log sensitive data or tokens
3. ✅ **ALWAYS** use Secrets Manager in production
4. ✅ **ALWAYS** use IAM roles (no access keys)
5. ✅ **ALWAYS** enable S3 bucket encryption

### Obfuscation Modes

**Token mode (default):**
- **What it does**: Generates deterministic HMAC-SHA256 tokens
- **Properties**: Same input → same token (allows joins across datasets)
- **Format**: 16-character hex string (e.g., `a3f2e1d4c5b6a789`)
- **Use case**: When you need to join obfuscated datasets or track records across files
- **Example**:
  ```
  alice@example.com → a3f2e1d4c5b6a789
  bob@example.com   → c5d6e7f8a9b0c1d2
  alice@example.com → a3f2e1d4c5b6a789  (same token!)
  ```

**Mask mode:**
- **What it does**: Replaces all values with a fixed string
- **Properties**: No determinism, cannot reverse or join
- **Format**: Fixed string (default: `***`, customizable)
- **Use case**: Maximum privacy when joins are not needed
- **Example**:
  ```
  alice@example.com → ***
  bob@example.com   → ***
  alice@example.com → ***
  ```

**When to use each mode:**
- **Use Token mode** if you need to:
  - Join obfuscated data across multiple files
  - Track the same user/entity across datasets
  - Maintain referential integrity

- **Use Mask mode** if you need to:
  - Completely hide the data
  - Don't need to join or track entities
  - Want maximum simplicity

**CLI Examples:**
```bash
# Token mode (default)
python -m gdpr_obfuscator.cli --input data.csv --output data.obf.csv --fields email,phone

# Mask mode with default '***'
python -m gdpr_obfuscator.cli --input data.csv --output data.masked.csv --fields email,phone --mask

# Mask mode with custom token
python -m gdpr_obfuscator.cli --input data.csv --output data.redacted.csv --fields email,phone --mask --mask-token "REDACTED"
```

**Lambda Examples:**
```json
// Token mode (default)
{
  "s3_uri": "s3://bucket/data.csv",
  "fields": ["email", "phone"],
  "target_s3_uri": "s3://bucket/data.obf.csv"
}

// Mask mode
{
  "s3_uri": "s3://bucket/data.csv",
  "fields": ["email", "phone"],
  "target_s3_uri": "s3://bucket/data.masked.csv",
  "mode": "mask"
}

// Custom mask
{
  "s3_uri": "s3://bucket/data.csv",
  "fields": ["email", "phone"],
  "target_s3_uri": "s3://bucket/data.redacted.csv",
  "mode": "mask",
  "mask_token": "REDACTED"
}
```

---

## Troubleshooting

### Common Issues

**Issue:** `RuntimeError: Obfuscator key missing`
```bash
# Solution: Set environment variable
export OBFUSCATOR_KEY="your-key-here"
```

**Issue:** `NotImplementedError: JSON format support is not yet implemented`
```bash
# Solution: Use CSV format (or wait for implementation)
# Currently only CSV is supported in MVP
```

**Issue:** Lambda package too large
```bash
# Solution: Check package size
./scripts/build_lambda.sh

# If >50MB, use Lambda Layer or Container Image
```

**Issue:** Tests fail with boto3 errors
```bash
# Solution: Install dev dependencies
pip install -r requirements-dev.txt
```

---

## Contributing

### Adding a New Format

1. Create adapter class in `format_adapters.py`:
   ```python
   class NewFormatAdapter(FormatAdapter):
       def process_stream(self, ...):
           # Implement read/obfuscate/write logic
   ```

2. Register in `get_adapter()` factory
3. Add to `detect_format_from_filename()`
4. Write tests in `tests/test_format_adapters.py`
5. Update documentation

See [EXTENSION_PLAN.md](EXTENSION_PLAN.md) for detailed guide.

---

## Requirements Met

### MVP Requirements (✅ Complete)

- ✅ CSV format support
- ✅ S3 integration (download/upload)
- ✅ HMAC-SHA256 obfuscation
- ✅ Deterministic tokens (primary key based)
- ✅ Configurable sensitive fields
- ✅ Lambda-compatible package (<50MB)
- ✅ Unit tests with >90% coverage
- ✅ PEP-8 compliant
- ✅ Security scans (bandit, pip-audit)
- ✅ No hardcoded credentials
- ✅ Documentation

### Extension Requirements (🔄 Architecturally Ready)

- 🔄 JSON format (stub implemented, architecture ready)
- 🔄 Parquet format (stub implemented, architecture ready)
- ✅ Output format matches input format (by design)
- ✅ Extensible architecture (adapter pattern)

---
## AWS Deployment

For complete step-by-step AWS deployment instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

**Quick start:**
```bash
# 1. Configure AWS credentials
aws configure

# 2. Build Lambda package
./scripts/build_lambda.sh

# 3. Deploy with Terraform
cd terraform
terraform init
terraform apply
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide including:
- IAM user setup
- S3 bucket creation
- Terraform configuration
- Testing and verification
- Troubleshooting

---

## License

Internal project for Northcoders Data Engineering Bootcamp.

---

## Contact

**Author:** Oleksii Kulykov  
**Project:** GDPR Obfuscator MVP  
**Bootcamp:** Northcoders Software Developer / Data Engineering

For questions about extending to JSON/Parquet formats, see [EXTENSION_PLAN.md](EXTENSION_PLAN.md).