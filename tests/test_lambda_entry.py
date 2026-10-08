import json

import gdpr_obfuscator.s3_adapter as s3_adapter_mod
from gdpr_obfuscator import lambda_entry


def test_missing_required_fields_returns_error(monkeypatch):
    monkeypatch.delenv("OBFUSCATOR_SECRET_NAME", raising=False)

    result = lambda_entry.lambda_handler({"s3_uri": "s3://b/f.csv"}, None)

    assert result["status"] == "error"
    assert "fields" in result["message"]


def test_invalid_json_string_returns_error(monkeypatch):
    monkeypatch.delenv("OBFUSCATOR_SECRET_NAME", raising=False)

    result = lambda_entry.lambda_handler("not json", None)

    assert result["status"] == "error"


def test_unknown_mode_returns_error(monkeypatch):
    monkeypatch.delenv("OBFUSCATOR_SECRET_NAME", raising=False)
    event = {"s3_uri": "s3://b/f.csv", "fields": ["email"], "mode": "hash"}

    result = lambda_entry.lambda_handler(event, None)

    assert result["status"] == "error"
    assert "mode" in result["message"]


def test_uploads_when_target_given(monkeypatch):
    monkeypatch.delenv("OBFUSCATOR_SECRET_NAME", raising=False)
    calls = {}
    monkeypatch.setattr(
        s3_adapter_mod, "process_and_upload", lambda **kwargs: calls.update(kwargs)
    )
    event = {
        "s3_uri": "s3://in/f.csv",
        "fields": ["email"],
        "target_s3_uri": "s3://out/f.csv",
        "mode": "mask",
    }

    result = lambda_entry.lambda_handler(json.dumps(event), None)

    assert result == {"status": "ok", "uploaded": True, "target": "s3://out/f.csv"}
    assert calls["mode"] == "mask"
    assert calls["primary_key_field"] == "id"


def test_returns_length_without_target(monkeypatch):
    monkeypatch.delenv("OBFUSCATOR_SECRET_NAME", raising=False)
    monkeypatch.setattr(
        s3_adapter_mod, "process_s3_csv_to_bytes", lambda *args, **kwargs: b"abc"
    )

    result = lambda_entry.lambda_handler(
        {"s3_uri": "s3://in/f.csv", "fields": ["email"]}, None
    )

    assert result == {"status": "ok", "uploaded": False, "length": 3}


def test_processing_failure_returns_error(monkeypatch):
    monkeypatch.delenv("OBFUSCATOR_SECRET_NAME", raising=False)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(s3_adapter_mod, "process_s3_csv_to_bytes", boom)

    result = lambda_entry.lambda_handler(
        {"s3_uri": "s3://in/f.csv", "fields": ["email"]}, None
    )

    assert result == {"status": "error", "message": "processing failed"}


def test_loads_key_from_secrets_manager(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_SECRET_NAME", "my-secret")
    monkeypatch.delenv("OBFUSCATOR_KEY", raising=False)
    monkeypatch.setattr(lambda_entry, "get_secret_string", lambda name: "secret-key")
    monkeypatch.setattr(
        s3_adapter_mod, "process_s3_csv_to_bytes", lambda *args, **kwargs: b""
    )

    lambda_entry.lambda_handler({"s3_uri": "s3://in/f.csv", "fields": ["e"]}, None)

    assert lambda_entry.os.environ["OBFUSCATOR_KEY"] == "secret-key"
