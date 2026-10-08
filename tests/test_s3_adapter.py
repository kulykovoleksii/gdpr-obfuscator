import io

import pytest
from botocore.stub import ANY, Stubber

# import the function and the client from your module
from gdpr_obfuscator import s3_adapter

SAMPLE_CSV = (
    "id,full_name,email,phone\n"
    "1,Alice,alice@example.com,111\n"
    "2,Bob,bob@example.com,222\n"
)


def test_process_s3_csv_to_bytes(monkeypatch):
    # give env key for obfuscator
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")

    # Prepare stubbed S3 client response: Body as BytesIO
    client = s3_adapter.s3  # this is the boto3 client used by the module
    stub = Stubber(client)

    # S3 get_object response with Body as BytesIO
    response = {"Body": io.BytesIO(SAMPLE_CSV.encode("utf-8"))}
    expected_params = {"Bucket": "my-bucket", "Key": "path/to/file.csv"}
    stub.add_response("get_object", response, expected_params)

    stub.activate()
    try:
        result = s3_adapter.process_s3_csv_to_bytes(
            "s3://my-bucket/path/to/file.csv",
            sensitive_fields=["email", "phone"],
            primary_key_field="id",
        )
    finally:
        stub.deactivate()

    # result is bytes
    assert isinstance(result, (bytes, bytearray))
    txt = result.decode("utf-8")
    # original emails and phones should not be present
    assert "alice@example.com" not in txt
    assert "bob@example.com" not in txt
    assert "111" not in txt
    assert "222" not in txt
    # header and id should remain
    assert "id" in txt
    assert "Alice" in txt


def test_process_and_upload_puts_obfuscated_file(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    client = s3_adapter.s3
    stub = Stubber(client)
    stub.add_response(
        "get_object",
        {"Body": io.BytesIO(SAMPLE_CSV.encode("utf-8"))},
        {"Bucket": "in-bucket", "Key": "raw/data.csv"},
    )
    stub.add_response(
        "put_object",
        {},
        {"Bucket": "out-bucket", "Key": "obf/data.csv", "Body": ANY},
    )

    stub.activate()
    try:
        s3_adapter.process_and_upload(
            source_s3_uri="s3://in-bucket/raw/data.csv",
            target_s3_uri="s3://out-bucket/obf/data.csv",
            sensitive_fields=["email"],
            mode="mask",
        )
    finally:
        stub.deactivate()

    stub.assert_no_pending_responses()


def test_parse_s3_uri():
    assert s3_adapter.parse_s3_uri("s3://bucket/a/b.csv") == ("bucket", "a/b.csv")
    with pytest.raises(ValueError):
        s3_adapter.parse_s3_uri("https://bucket/a.csv")


def test_unknown_extension_requires_explicit_format():
    with pytest.raises(ValueError, match="Cannot auto-detect format"):
        s3_adapter.process_s3_file_to_bytes("s3://bucket/data.xml", ["email"])


def test_not_implemented_format_is_reported(monkeypatch):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    client = s3_adapter.s3
    stub = Stubber(client)
    stub.add_response(
        "get_object",
        {"Body": io.BytesIO(b"[]")},
        {"Bucket": "bucket", "Key": "data.json"},
    )

    stub.activate()
    try:
        with pytest.raises(NotImplementedError, match="Format 'json'"):
            s3_adapter.process_s3_file_to_bytes("s3://bucket/data.json", ["email"])
    finally:
        stub.deactivate()
