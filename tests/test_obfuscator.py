import io
import pytest
import csv
import string
from gdpr_obfuscator.obfuscator import obfuscate_value, obfuscate_csv_stream


def test_obfuscate_value_is_deterministic():
    key = b"testkey"
    a = obfuscate_value(key, "123", "email")
    b = obfuscate_value(key, "123", "email")
    assert a == b
    assert len(a) == 16


def test_obfuscate_value_changes_with_field():
    key = b"testkey"
    a = obfuscate_value(key, "123", "email")
    b = obfuscate_value(key, "123", "phone")
    assert a != b


def test_csv_obfuscation_replaces_sensitive_fields(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    input_csv = "id,full_name,email,phone\n1,John Doe,john@example.com,5551234\n2,Jane Doe,jane@example.com,5555678\n"

    inp = io.StringIO(input_csv)
    out = io.StringIO()

    obfuscate_csv_stream(
        inp, out, sensitive_fields=["email", "phone"], primary_key_field="id"
    )

    out.seek(0)
    result_text = out.read()

    # raw PII should not be in output
    assert "john@example.com" not in result_text
    assert "jane@example.com" not in result_text
    assert "5551234" not in result_text
    assert "5555678" not in result_text

    # parse CSV and check obfuscated token format (hex, length 16)
    out.seek(0)
    reader = csv.DictReader(io.StringIO(result_text))
    rows = list(reader)
    assert len(rows) == 2

    hex_chars = set(string.hexdigits.lower())
    for row in rows:
        # email and phone should be replaced with 16-hex chars
        email_token = row.get("email", "")
        phone_token = row.get("phone", "")
        assert len(email_token) == 16
        assert all(ch in hex_chars for ch in email_token.lower())
        assert len(phone_token) == 16
        assert all(ch in hex_chars for ch in phone_token.lower())

    # tokens for different primary keys should be different (basic check)
    assert rows[0]["email"] != rows[1]["email"]
    assert rows[0]["phone"] != rows[1]["phone"]


def test_csv_obfuscation_handles_missing_field(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    input_csv = "id,name\n1,John\n2,Jane\n"
    inp = io.StringIO(input_csv)
    out = io.StringIO()

    obfuscate_csv_stream(
        inp, out, sensitive_fields=["nonexistent_field"], primary_key_field="id"
    )

    out.seek(0)
    result = out.read()
    assert "John" in result
    assert "Jane" in result


def test_mask_mode_applies(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    inp = io.StringIO("id,email\n1,a@x.com\n")
    out = io.StringIO()
    obfuscate_csv_stream(inp, out, sensitive_fields=["email"], primary_key_field="id", key=b"testkey", mode="mask", mask_token="***")
    out.seek(0)
    txt = out.read()
    assert "***" in txt
    assert "a@x.com" not in txt
