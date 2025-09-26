# GDPR Obfuscator (short usage)

## What is this

This tool make a copy of CSV file and replace personal data with safe tokens.
It use HMAC with secret key. The output is not the real data. It is good for analysis when you need not to see real persons.

:TODO
* Designed for streaming processing (low memory) and easy AWS deployment (Lambda / ECS / EC2).
* MVP supports CSV; design is extensible to JSON/Parquet.
* Deterministic obfuscation allows linking anonymised records by primary key while preventing direct re-identification.

## Requirements

* Python 3.10+ (or 3.11)
* `pip install -r requirements.txt` (see file)

## Setup (local)

1. create virtual env:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. set secret key (example):

```bash
export OBFUSCATOR_KEY="paste_a_long_secret_here"
```

You can create a secret by python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Run local (simple)

Use CLI to process local CSV:

```bash
python -m gdpr_obfuscator.cli --input data.csv --output data.obf.csv --fields email,phone --pk id
```

* `--fields` is comma list of columns to obfuscate.
* `--pk` is primary key column name (default `id`).

## Tests

Run tests with pytest:

```bash
pytest -q
```

In tests we use a fake key (this is ok). For real use do not put key in code.

## Generate test data

To make sample CSV (default 1_000_000 rows):

```bash
python tools/generate_test_data.py 1000000
```

For quick test use smaller number like `10000`.

## Security notes

* Do not commit `OBFUSCATOR_KEY` to git.
* In production use AWS Secrets Manager or Parameter Store. Lambda or ECS should read secret at runtime.
* If you need non-deterministic tokens (no joins), change HMAC to add random salt.

## S3 usage (short)

There is adapter for S3 (s3_adapter). It can:

* download object from `s3://bucket/key`
* obfuscate content
* return bytes ready to upload

In production you must give the process permission to read S3 and read secret.

## Contact
