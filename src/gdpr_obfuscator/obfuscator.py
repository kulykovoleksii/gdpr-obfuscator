"""
Core obfuscation logic with multi-format support via adapter pattern.
"""

import hmac
import hashlib
import os
import logging
from typing import List, IO, Optional
from io import BytesIO

from .format_adapters import get_adapter

logger = logging.getLogger(__name__)
KEY_ENV = "OBFUSCATOR_KEY"


def _get_key() -> bytes:
    """Retrieve obfuscation key from environment."""
    key = os.getenv(KEY_ENV)
    if not key:
        raise RuntimeError(
            f"Obfuscator key missing. Set {KEY_ENV} environment variable."
        )
    return key.encode("utf-8")


def obfuscate_value(
    key: bytes,
    primary_value: str,
    field_name: str,
    length: int = 16,
    mode: str = "token",
    mask_token: str = "***",  # nosec B107
) -> str:
    """
    Return obfuscated representation for a single field value.

    Args:
        key: Secret key for HMAC
        primary_value: Value of primary key field (for deterministic hashing)
        field_name: Name of the field being obfuscated
        length: Length of hex token (when mode='token')
        mode: 'token' (deterministic HMAC) or 'mask' (fixed string)
        mask_token: String to use when mode='mask'

    Returns:
        Obfuscated string
    """
    if mode == "mask":
        return mask_token

    # Deterministic HMAC-based token
    if primary_value is None:
        primary_value = ""

    hm = hmac.new(key, digestmod=hashlib.sha256)
    hm.update(primary_value.encode("utf-8"))
    hm.update(b"|")
    hm.update(field_name.encode("utf-8"))

    return hm.hexdigest()[:length]


def obfuscate_stream(
    input_stream: IO[bytes],
    output_stream: IO[bytes],
    sensitive_fields: List[str],
    file_format: str = "csv",
    primary_key_field: str = "id",
    key: Optional[bytes] = None,
    mode: str = "token",
    mask_token: str = "***",  # nosec B107
    token_length: int = 16,
) -> int:
    """
    Universal obfuscation function for supported formats.

    Currently implemented: CSV
    Planned: JSON, JSONL, Parquet

    Args:
        input_stream: Binary input stream
        output_stream: Binary output stream
        sensitive_fields: List of field names to obfuscate
        file_format: One of 'csv', 'json', 'jsonl', 'parquet'
        primary_key_field: Name of primary key field
        key: HMAC key (if None, reads from environment)
        mode: 'token' or 'mask'
        mask_token: Fixed string for mask mode
        token_length: Length of hex token for token mode

    Returns:
        Number of records processed

    Raises:
        NotImplementedError: If format is not yet implemented (JSON, Parquet)
        ValueError: If format is not recognized

    Example:
        # CSV (works)
        with open('input.csv', 'rb') as fin, open('output.csv', 'wb') as fout:
            obfuscate_stream(fin, fout, ['email'], file_format='csv')

        # JSON (raises NotImplementedError - not yet implemented)
        with open('input.json', 'rb') as fin, open('output.json', 'wb') as fout:
            obfuscate_stream(fin, fout, ['email'], file_format='json')
    """
    if key is None:
        key = _get_key()

    # Get appropriate adapter for the format
    # This will raise NotImplementedError for JSON/Parquet
    adapter = get_adapter(file_format)

    # Create obfuscation function with closure over key and parameters
    def obfuscate_fn(pk_value: str, field_name: str) -> str:
        return obfuscate_value(
            key=key,
            primary_value=pk_value,
            field_name=field_name,
            length=token_length,
            mode=mode,
            mask_token=mask_token,
        )

    # Delegate to format-specific adapter
    count = adapter.process_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        sensitive_fields=sensitive_fields,
        primary_key_field=primary_key_field,
        obfuscate_fn=obfuscate_fn,
    )

    logger.info(
        "Obfuscation complete: format=%s, records=%d, fields=%s",
        file_format,
        count,
        sensitive_fields,
    )

    return count


# Keep backward compatibility with existing CSV-specific function
def obfuscate_csv_stream(
    input_stream: IO[str],
    output_stream: IO[str],
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    key: Optional[bytes] = None,
    csv_dialect: str = "excel",
    mode: str = "token",
    mask_token: str = "***",  # nosec B107
    token_length: int = 16,
) -> None:
    """
    Legacy CSV-specific function for backward compatibility.

    This wraps text streams in BytesIO and calls the universal obfuscate_stream.
    Kept to avoid breaking existing code that uses this function.
    """
    # Convert text streams to byte streams
    input_bytes = BytesIO(input_stream.read().encode("utf-8"))
    output_bytes = BytesIO()

    obfuscate_stream(
        input_stream=input_bytes,
        output_stream=output_bytes,
        sensitive_fields=sensitive_fields,
        file_format="csv",
        primary_key_field=primary_key_field,
        key=key,
        mode=mode,
        mask_token=mask_token,
        token_length=token_length,
    )

    # Write result back to text stream
    output_stream.write(output_bytes.getvalue().decode("utf-8"))
