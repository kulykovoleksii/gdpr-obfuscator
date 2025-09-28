"""Core obfuscation logic (streaming CSV)."""

from typing import Iterable, List, IO
import csv
import hmac
import hashlib
import os


# Key environment variable name
KEY_ENV = "OBFUSCATOR_KEY"


def _get_key() -> bytes:
    key = os.getenv(KEY_ENV)
    if not key:
        raise RuntimeError(
            f"Obfuscator key missing. Set {KEY_ENV} environment variable."
        )
    return key.encode("utf-8")


def obfuscate_value(
    key: bytes, primary_value: str, field_name: str, length: int = 16
) -> str:
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
) -> None:
    """
    Read CSV from input_stream and write an obfuscated copy to output_stream.
    - `sensitive_fields` are the column names to obfuscate.
    - `primary_key_field` is the unique id column used to create deterministic tokens.
    - `key` if provided overrides environment variable.
    """
    if key is None:
        key = _get_key()

    reader = csv.DictReader(input_stream, dialect=csv_dialect)
    writer = csv.DictWriter(
        output_stream, fieldnames=reader.fieldnames, dialect=csv_dialect
    )
    writer.writeheader()

    for row in reader:
        pk = row.get(primary_key_field, "")
        for f in sensitive_fields:
            if f not in row:
                # skip missing columns gracefully
                continue
            # produce obfuscated value; keep same length as short hex
            row[f] = obfuscate_value(key, pk, f)
        writer.writerow(row)

