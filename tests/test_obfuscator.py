import io
import os
import pytest
from src.gdpr_obfuscator.obfuscator import obfuscate_value, obfuscate_csv_stream


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

    obfuscate_csv_stream(inp, out, sensitive_fields=["email", "phone"], primary_key_field="id")

    out.seek(0)
    result = out.read() 

    assert "john@example.com" not in result
    assert "jane@example.com" not in result
    assert "5551234" not in result
    assert "5555678" not in result


def test_csv_obfuscation_handles_missing_field(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    input_csv = "id,name\n1,John\n2,Jane\n"
    inp = io.StringIO(input_csv)
    out = io.StringIO()

    obfuscate_csv_stream(inp, out, sensitive_fields=["nonexistent_field"], primary_key_field="id")

    out.seek(0)
    result = out.read()
    assert "John" in result
    assert "Jane" in result