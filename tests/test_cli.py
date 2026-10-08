import csv

import pytest

from gdpr_obfuscator import cli


@pytest.fixture
def input_csv(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n")
    return path


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_cli_token_mode(monkeypatch, tmp_path, input_csv):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    output = tmp_path / "out.csv"

    cli.main(["--input", str(input_csv), "--output", str(output), "--fields", "email"])

    rows = read_rows(output)
    assert [r["name"] for r in rows] == ["Alice", "Bob"]
    assert all(len(r["email"]) == 16 for r in rows)
    assert "alice@example.com" not in output.read_text()


def test_cli_mask_mode_with_custom_token(monkeypatch, tmp_path, input_csv):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    output = tmp_path / "out.csv"

    cli.main(
        [
            "--input",
            str(input_csv),
            "--output",
            str(output),
            "--fields",
            "email",
            "--mask",
            "--mask-token",
            "REDACTED",
        ]
    )

    assert [r["email"] for r in read_rows(output)] == ["REDACTED", "REDACTED"]


def test_cli_token_length(monkeypatch, tmp_path, input_csv):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    output = tmp_path / "out.csv"

    cli.main(
        [
            "--input",
            str(input_csv),
            "--output",
            str(output),
            "--fields",
            "email",
            "--token-length",
            "8",
        ]
    )

    assert all(len(r["email"]) == 8 for r in read_rows(output))


def test_cli_explicit_format_overrides_extension(monkeypatch, tmp_path):
    monkeypatch.setenv("OBFUSCATOR_KEY", "testkey")
    source = tmp_path / "data.txt"
    source.write_text("id,email\n1,a@x.com\n")
    output = tmp_path / "out.txt"

    cli.main(
        [
            "--input",
            str(source),
            "--output",
            str(output),
            "--fields",
            "email",
            "--format",
            "csv",
        ]
    )

    assert "a@x.com" not in output.read_text()


def test_cli_missing_key_exits(monkeypatch, tmp_path, input_csv):
    monkeypatch.delenv("OBFUSCATOR_KEY", raising=False)

    with pytest.raises(SystemExit):
        cli.main(
            [
                "--input",
                str(input_csv),
                "--output",
                str(tmp_path / "out.csv"),
                "--fields",
                "email",
            ]
        )
