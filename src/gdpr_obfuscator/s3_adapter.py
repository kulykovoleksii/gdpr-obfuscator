"""
S3 adapter with multi-format support (auto-detection from filename).
"""

from io import BytesIO
import boto3
from typing import List, Optional, Any
import logging

from .obfuscator import obfuscate_stream
from .format_adapters import detect_format_from_filename

logger = logging.getLogger(__name__)
s3 = boto3.client("s3")


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """
    Parse S3 URI into bucket and key.

    Args:
        uri: S3 URI like 's3://bucket-name/path/to/file.csv'

    Returns:
        Tuple of (bucket_name, key_path)
    """
    if not uri.startswith("s3://"):
        raise ValueError("S3 URI must start with s3://")

    without_prefix = uri[5:]
    bucket, _, key = without_prefix.partition("/")

    return bucket, key


def process_s3_file_to_bytes(
    s3_uri: str,
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    file_format: Optional[str] = None,
    s3_client: Optional[Any] = None,
    mode: str = "token",
    mask_token: str = "***",
) -> bytes:
    """
    Download file from S3, obfuscate it, and return bytes.

    Args:
        s3_uri: S3 URI (e.g., 's3://bucket/file.csv')
        sensitive_fields: List of fields to obfuscate
        primary_key_field: Name of primary key field
        file_format: Format hint ('csv', 'json', 'jsonl', 'parquet').
                    If None, auto-detect from filename.
        s3_client: Optional boto3 S3 client (for testing)

    Returns:
        Obfuscated file as bytes

    Raises:
        NotImplementedError: If format is not yet implemented (JSON, Parquet)

    Example:
        # CSV (works)
        result = process_s3_file_to_bytes(
            's3://my-bucket/data.csv',
            sensitive_fields=['email', 'phone']
        )

        # JSON (raises NotImplementedError)
        result = process_s3_file_to_bytes(
            's3://my-bucket/data.json',
            sensitive_fields=['email']
        )
    """
    client = s3_client or s3
    bucket, key = parse_s3_uri(s3_uri)

    # Auto-detect format if not specified
    if file_format is None:
        try:
            file_format = detect_format_from_filename(key)
            logger.info("Auto-detected format from filename: %s", file_format)
        except ValueError as e:
            raise ValueError(
                f"Cannot auto-detect format from {key}. "
                "Please specify file_format parameter explicitly."
            ) from e

    logger.info("Downloading s3://%s/%s (format: %s)", bucket, key, file_format)

    # Download file from S3
    resp = client.get_object(Bucket=bucket, Key=key)  # type: ignore[union-attr]
    input_stream = resp["Body"]

    # Process through obfuscator
    output_bytes = BytesIO()

    try:
        obfuscate_stream(
            input_stream=input_stream,
            output_stream=output_bytes,
            sensitive_fields=sensitive_fields,
            file_format=file_format,
            primary_key_field=primary_key_field,
            mode=mode,
            mask_token=mask_token,
        )
    except NotImplementedError as e:
        logger.error("Format not yet implemented: %s", file_format)
        raise NotImplementedError(
            f"Format '{file_format}' is not yet implemented. "
            f"Currently only CSV is supported. "
            f"Original error: {e}"
        ) from e

    result = output_bytes.getvalue()

    logger.info(
        "Obfuscation complete: input_size=%d, output_size=%d bytes",
        resp.get("ContentLength", 0),
        len(result),
    )

    return result


def process_and_upload(
    source_s3_uri: str,
    target_s3_uri: str,
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    file_format: Optional[str] = None,
    s3_client: Optional[Any] = None,
    mode: str = "token",
    mask_token: str = "***",
) -> None:
    """
    Process S3 file and upload obfuscated result to another S3 location.

    Args:
        source_s3_uri: Source file S3 URI
        target_s3_uri: Destination S3 URI for obfuscated file
        sensitive_fields: List of fields to obfuscate
        primary_key_field: Name of primary key field
        file_format: Format hint. If None, auto-detect from source filename.
        s3_client: Optional boto3 S3 client (for testing)

    Raises:
        NotImplementedError: If format is not yet implemented (JSON, Parquet)

    Example:
        # CSV (works)
        process_and_upload(
            source_s3_uri='s3://input-bucket/raw/data.csv',
            target_s3_uri='s3://output-bucket/obfuscated/data.csv',
            sensitive_fields=['email', 'ssn']
        )
    """
    client = s3_client or s3
    target_bucket, target_key = parse_s3_uri(target_s3_uri)

    logger.info("Processing: %s -> %s", source_s3_uri, target_s3_uri)

    # Process the file (may raise NotImplementedError)
    obfuscated_bytes = process_s3_file_to_bytes(
        s3_uri=source_s3_uri,
        sensitive_fields=sensitive_fields,
        primary_key_field=primary_key_field,
        file_format=file_format,
        s3_client=client,
        mode=mode,
        mask_token=mask_token,
    )

    # Upload to target location
    client.put_object(  # type: ignore[union-attr]
        Bucket=target_bucket, Key=target_key, Body=obfuscated_bytes
    )

    logger.info(
        "Upload complete: s3://%s/%s (%d bytes)",
        target_bucket,
        target_key,
        len(obfuscated_bytes),
    )


# Keep legacy function for backward compatibility
def process_s3_csv_to_bytes(
    s3_uri: str,
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    s3_client: Optional[Any] = None,
    mode: str = "token",
    mask_token: str = "***",
) -> bytes:
    """
    Legacy CSV-specific function for backward compatibility.

    This is a wrapper around process_s3_file_to_bytes with format='csv'.
    Kept to avoid breaking existing code.
    """
    return process_s3_file_to_bytes(
        s3_uri=s3_uri,
        sensitive_fields=sensitive_fields,
        primary_key_field=primary_key_field,
        file_format="csv",
        s3_client=s3_client,
        mode=mode,
        mask_token=mask_token,
    )
