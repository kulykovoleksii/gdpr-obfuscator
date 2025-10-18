"""S3 adapter: download CSV from S3, obfuscate it and upload back to S3."""

from io import BytesIO, TextIOWrapper
import boto3
from typing import List, Optional
import logging

from .obfuscator import obfuscate_csv_stream

logger = logging.getLogger(__name__)
s3 = boto3.client("s3")


def parse_s3_uri(uri: str):
    assert uri.startswith("s3://"), "s3 uri must start with s3://"
    without = uri[5:]
    bucket, _, key = without.partition("/")
    return bucket, key


def process_s3_csv_to_bytes(
    s3_uri: str,
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    s3_client: Optional[object] = None,
) -> bytes:
    """
    Download CSV from s3_uri,
    obfuscate it and return bytes suitable for put_object.
    This streams the object using a TextIOWrapper
    so we avoid building a large string.
    """
    client = s3_client or s3
    bucket, key = parse_s3_uri(s3_uri)
    logger.info("Downloading s3://%s/%s", bucket, key)
    resp = client.get_object(Bucket=bucket, Key=key)
    body = resp["Body"]  # StreamingBody

    text_stream = TextIOWrapper(body, encoding="utf-8")

    out_bytes = BytesIO()
    with TextIOWrapper(out_bytes, encoding="utf-8", write_through=True) as out_text:
        obfuscate_csv_stream(
            input_stream=text_stream,
            output_stream=out_text,
            sensitive_fields=sensitive_fields,
            primary_key_field=primary_key_field,
        )

        out_text.flush()
        result = out_bytes.getvalue()

    logger.info("Obfuscation complete, output size=%d bytes", len(result))
    return result


def process_and_upload(
    source_s3_uri: str,
    target_s3_uri: str,
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    s3_client: Optional[object] = None,
) -> None:
    """
    Convenience: process source S3 CSV
    and upload obfuscated bytes to target S3 URI.
    """
    client = s3_client or s3
    bucket_t, key_t = parse_s3_uri(target_s3_uri)
    logger.info("Processing %s -> %s", source_s3_uri, target_s3_uri)
    data_bytes = process_s3_csv_to_bytes(
        s3_uri=source_s3_uri,
        sensitive_fields=sensitive_fields,
        primary_key_field=primary_key_field,
        s3_client=client,
    )
    client.put_object(Bucket=bucket_t, Key=key_t, Body=data_bytes)
    logger.info("Uploaded obfuscated file to s3://%s/%s", bucket_t, key_t)
