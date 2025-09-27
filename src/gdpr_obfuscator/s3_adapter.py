from io import StringIO
import boto3
from typing import List
from .obfuscator import obfuscate_csv_stream

s3 = boto3.client("s3")

def parse_s3_uri(uri: str):
    assert uri.startswith("s3://"), "s3 uri must start with s3://"
    without = uri[5:]
    bucket, _, key = without.partition("/")
    return bucket, key

def process_s3_csv_to_bytes(s3_uri: str, sensitive_fields: List[str], primary_key_field: str = "id") -> bytes:
    bucket, key = parse_s3_uri(s3_uri)
    resp = s3.get_object(Bucket=bucket, Key=key)
    text = resp["Body"].read().decode("utf-8")
    in_stream = StringIO(text)
    out_stream = StringIO()
    obfuscate_csv_stream(in_stream, out_stream, sensitive_fields, primary_key_field)
    out_stream.seek(0)
    return out_stream.getvalue().encode("utf-8")
