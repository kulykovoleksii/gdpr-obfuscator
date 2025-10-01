import io
from botocore.stub import Stubber

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
