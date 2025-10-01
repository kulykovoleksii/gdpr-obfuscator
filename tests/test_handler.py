import json

from gdpr_obfuscator import handler
import gdpr_obfuscator.s3_adapter as s3_adapter_mod


def test_process_request_calls_adapter(monkeypatch):
    fake_bytes = b"some-bytes"
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")

    # Patch the adapter function on the adapter module
    monkeypatch.setattr(
        s3_adapter_mod, "process_s3_csv_to_bytes", lambda s3_uri, fields, pk: fake_bytes
    )

    payload = json.dumps(
        {"s3_uri": "s3://bucket/file.csv", "fields": ["email"], "primary_key": "id"}
    )

    out = handler.process_request(payload)

    assert isinstance(out, dict)
    assert out["bytes"] == fake_bytes
    assert out["length"] == len(fake_bytes)
