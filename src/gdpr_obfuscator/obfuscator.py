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
        raise RuntimeError(f"Obfuscator key missing. Set ${KEY_ENV} environment variable.")
    return key.encode("utf-8")

def obfuscate_value(key: bytes, primary_value: str, field_name: str, length: int = 16) -> str:
    if primary_value is None:
        primary_value = ""
    hm = hmac.new(key, digestmod=hashlib.sha256)
    hm.update(primary_value.encode("utf-8"))
    hm.update(b"|")
    hm.update(field_name.encode("utf-8"))
    return hm.hexdigest()[:length]