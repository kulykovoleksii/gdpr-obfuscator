"""Core obfuscation logic (streaming CSV)."""

import csv
import hmac
import hashlib
import os
import logging
from typing import List, IO

logger = logging.getLogger(__name__)
KEY_ENV = "OBFUSCATOR_KEY"

def _get_key() -> bytes:
    key = os.getenv(KEY_ENV)
    if not key:
        raise RuntimeError(f"Obfuscator key missing. Set {KEY_ENV} environment variable.")
    return key.encode("utf-8")


def obfuscate_value(
    key: bytes,
    primary_value: str,
    field_name: str,
    length: int = 16,
    mode: str = "token",
    mask_token: str = "***",
) -> str:
    """
    Return obfuscated representation for a single field.
    - mode='token' : deterministic HMAC hex truncated to `length`.
    - mode='mask'  : return fixed mask string (mask_token).
    """
    if mode == "mask":
        return mask_token

    # default: deterministic HMAC token
    if primary_value is None:
        primary_value = ""
    hm = hmac.new(key, digestmod=hashlib.sha256)
    hm.update(primary_value.encode("utf-8"))
    hm.update(b"|")
    hm.update(field_name.encode("utf-8"))
    return hm.hexdigest()[:length]


def obfuscate_csv_stream(
    input_stream: IO[str],
    output_stream: IO[str],
    sensitive_fields: List[str],
    primary_key_field: str = "id",
    key: bytes | None = None,
    csv_dialect: str = "excel",
    mode: str = "token",
    mask_token: str = "***",
    token_length: int = 16,
) -> None:
    """
    Stream CSV and replace sensitive fields.
    - mode: 'token' (default) or 'mask'
    - mask_token: string used when mode == 'mask'
    - token_length: length of hex token when mode == 'token'
    """
    if key is None:
        key = _get_key()

    reader = csv.DictReader(input_stream, dialect=csv_dialect)
    if not reader.fieldnames:
        raise ValueError("CSV input has no header row")
    fieldnames = reader.fieldnames
    if not fieldnames:
        raise ValueError("CSV input has no header row (DictReader returned None)")
    writer = csv.DictWriter(output_stream, fieldnames=fieldnames, dialect=csv_dialect)
    writer.writeheader()

    count = 0
    for row in reader:
        count += 1
        pk = row.get(primary_key_field, "")
        for f in sensitive_fields:
            if f not in row:
                continue
            row[f] = obfuscate_value(
                key,
                pk,
                f,
                length=token_length,
                mode=mode,
                mask_token=mask_token,
            )
        writer.writerow(row)

    logger.info("Finished obfuscation, total rows processed: %d", count)
