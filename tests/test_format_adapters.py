"""
Tests for format adapter pattern and stub implementations.
"""

import pytest
from io import BytesIO

from gdpr_obfuscator.format_adapters import (
    get_adapter,
    detect_format_from_filename,
    list_supported_formats,
    CSVAdapter,
    JSONAdapter,
    ParquetAdapter,
)


def test_csv_adapter_exists():
    """CSV adapter should be implemented and working."""
    adapter = get_adapter("csv")
    assert isinstance(adapter, CSVAdapter)


def test_json_adapter_raises_not_implemented():
    """JSON adapter should exist but raise NotImplementedError."""
    adapter = get_adapter("json")
    assert isinstance(adapter, JSONAdapter)

    # Attempting to use it should raise NotImplementedError
    with pytest.raises(NotImplementedError) as exc_info:
        adapter.process_stream(
            input_stream=BytesIO(b"{}"),
            output_stream=BytesIO(),
            sensitive_fields=["email"],
            primary_key_field="id",
            obfuscate_fn=lambda pk, field: "token",
        )

    assert "not yet implemented" in str(exc_info.value).lower()
    assert "csv" in str(exc_info.value).lower()  # Should mention CSV is supported


def test_jsonl_adapter_raises_not_implemented():
    """JSONL adapter should exist but raise NotImplementedError."""
    adapter = get_adapter("jsonl")
    assert isinstance(adapter, JSONAdapter)

    with pytest.raises(NotImplementedError):
        adapter.process_stream(
            input_stream=BytesIO(b"{}"),
            output_stream=BytesIO(),
            sensitive_fields=["email"],
            primary_key_field="id",
            obfuscate_fn=lambda pk, field: "token",
        )


def test_parquet_adapter_raises_not_implemented():
    """Parquet adapter should exist but raise NotImplementedError."""
    adapter = get_adapter("parquet")
    assert isinstance(adapter, ParquetAdapter)

    with pytest.raises(NotImplementedError) as exc_info:
        adapter.process_stream(
            input_stream=BytesIO(b"PARQUET"),
            output_stream=BytesIO(),
            sensitive_fields=["ssn"],
            primary_key_field="id",
            obfuscate_fn=lambda pk, field: "token",
        )

    assert "not yet implemented" in str(exc_info.value).lower()
    assert "pyarrow" in str(exc_info.value).lower()  # Should mention dependency


def test_get_adapter_invalid_format():
    """Getting adapter for invalid format should raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        get_adapter("xml")

    assert "unsupported format" in str(exc_info.value).lower()
    assert "xml" in str(exc_info.value)


def test_detect_format_from_filename_csv():
    """Should detect CSV from .csv extension."""
    assert detect_format_from_filename("data.csv") == "csv"
    assert detect_format_from_filename("/path/to/file.CSV") == "csv"
    assert detect_format_from_filename("my-data.v2.csv") == "csv"


def test_detect_format_from_filename_json():
    """Should detect JSON from .json extension."""
    assert detect_format_from_filename("data.json") == "json"
    assert detect_format_from_filename("users.JSON") == "json"


def test_detect_format_from_filename_jsonl():
    """Should detect JSONL from .jsonl or .ndjson extension."""
    assert detect_format_from_filename("data.jsonl") == "jsonl"
    assert detect_format_from_filename("stream.ndjson") == "jsonl"


def test_detect_format_from_filename_parquet():
    """Should detect Parquet from .parquet or .pq extension."""
    assert detect_format_from_filename("data.parquet") == "parquet"
    assert detect_format_from_filename("table.pq") == "parquet"
    assert detect_format_from_filename("big.PARQUET") == "parquet"


def test_detect_format_from_filename_unsupported():
    """Should raise ValueError for unsupported extensions."""
    with pytest.raises(ValueError) as exc_info:
        detect_format_from_filename("data.xml")

    assert "cannot detect format" in str(exc_info.value).lower()
    assert "xml" in str(exc_info.value)


def test_detect_format_from_filename_no_extension():
    """Should raise ValueError when no extension present."""
    with pytest.raises(ValueError):
        detect_format_from_filename("datafile")


def test_list_supported_formats():
    """Should list all formats with their implementation status."""
    formats = list_supported_formats()

    assert formats["csv"] == "implemented"
    assert formats["json"] == "planned"
    assert formats["jsonl"] == "planned"
    assert formats["parquet"] == "planned"

    # Verify CSV is the only implemented format
    implemented = [k for k, v in formats.items() if v == "implemented"]
    assert implemented == ["csv"]


def test_csv_adapter_processes_correctly(monkeypatch):
    """CSV adapter should process data correctly (integration test)."""
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")

    csv_data = b"id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n"

    input_stream = BytesIO(csv_data)
    output_stream = BytesIO()

    adapter = CSVAdapter()

    def mock_obfuscate(pk_value: str, field_name: str) -> str:
        return f"OBFUSCATED_{field_name}_{pk_value}"

    count = adapter.process_stream(
        input_stream=input_stream,
        output_stream=output_stream,
        sensitive_fields=["email"],
        primary_key_field="id",
        obfuscate_fn=mock_obfuscate,
    )

    assert count == 2  # Two rows processed

    output_text = output_stream.getvalue().decode("utf-8")
    assert "OBFUSCATED_email_1" in output_text
    assert "OBFUSCATED_email_2" in output_text
    assert "alice@example.com" not in output_text
    assert "bob@example.com" not in output_text
    assert "Alice" in output_text  # Name should not be obfuscated
    assert "Bob" in output_text
