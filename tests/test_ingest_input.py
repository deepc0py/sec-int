"""Tests for the scan input handler module."""

import json
import pytest

from app.ingest_input import (
    handle_scan_input,
    InvalidScanInputError,
    _redact_secrets
)


class TestRedactSecrets:
    """Test secret redaction functionality."""

    def test_redact_dict_with_secrets(self):
        """Test redacting secrets from dictionary."""
        data = {
            "api_key": "sk-12345",
            "normal_field": "value",
            "token": "bearer xyz",
            "nested": {
                "password": "secret123",
                "safe": "data"
            }
        }

        result = _redact_secrets(data)

        assert result["api_key"] == "***REDACTED***"
        assert result["normal_field"] == "value"
        assert result["token"] == "***REDACTED***"
        assert result["nested"]["password"] == "***REDACTED***"
        assert result["nested"]["safe"] == "data"

    def test_redact_list_with_dicts(self):
        """Test redacting secrets from list of dictionaries."""
        data = [
            {"api_key": "key1"},
            {"normal": "value"},
            {"secret": "hidden"}
        ]

        result = _redact_secrets(data)

        assert result[0]["api_key"] == "***REDACTED***"
        assert result[1]["normal"] == "value"
        assert result[2]["secret"] == "***REDACTED***"

    def test_redact_case_insensitive(self):
        """Test that secret key matching is case-insensitive."""
        data = {
            "API_KEY": "value1",
            "ApiKey": "value2",
            "ACCESS_TOKEN": "value3"
        }

        result = _redact_secrets(data)

        assert result["API_KEY"] == "***REDACTED***"
        assert result["ApiKey"] == "***REDACTED***"
        assert result["ACCESS_TOKEN"] == "***REDACTED***"

    def test_redact_nested_complex(self):
        """Test redacting from deeply nested structures."""
        data = {
            "level1": {
                "level2": {
                    "credentials": "hidden",
                    "data": [
                        {"private_key": "key"},
                        {"public_key": "ok"}
                    ]
                }
            }
        }

        result = _redact_secrets(data)

        assert result["level1"]["level2"]["credentials"] == "***REDACTED***"
        assert result["level1"]["level2"]["data"][0]["private_key"] == "***REDACTED***"
        assert result["level1"]["level2"]["data"][1]["public_key"] == "ok"


class TestHandleScanInput:
    """Test the main scan input handler."""

    def test_handle_string_input(self):
        """Test handling plain string input."""
        input_text = "  Some scan results\nwith whitespace  "
        result = handle_scan_input(input_text)

        assert result == "Some scan results\nwith whitespace"

    def test_handle_dict_input(self):
        """Test handling dictionary input."""
        input_dict = {
            "scan_results": ["A01:2021", "T1059"],
            "api_key": "secret"
        }

        result = handle_scan_input(input_dict)

        # Should be formatted JSON with redacted secrets
        parsed = json.loads(result)
        assert parsed["scan_results"] == ["A01:2021", "T1059"]
        assert parsed["api_key"] == "***REDACTED***"

    def test_normalize_line_endings(self):
        """Test normalization of various line endings."""
        inputs = [
            "line1\r\nline2\rline3\fline4",  # Mixed line endings
            "line1\n\n\n\n\nline2",  # Excessive newlines
            "line1  \nline2  \n  line3"  # Trailing spaces
        ]

        expected = [
            "line1\nline2\nline3\nline4",
            "line1\n\nline2",  # Excessive newlines collapsed to 2
            "line1\nline2\n  line3"  # Leading spaces preserved
        ]

        for input_text, expected_output in zip(inputs, expected):
            assert handle_scan_input(input_text) == expected_output

    def test_empty_input_raises_error(self):
        """Test that empty input raises InvalidScanInputError."""
        with pytest.raises(InvalidScanInputError, match="empty"):
            handle_scan_input("")

        with pytest.raises(InvalidScanInputError, match="empty"):
            handle_scan_input("   \n  \t  ")

    def test_none_input_raises_error(self):
        """Test that None input raises InvalidScanInputError."""
        with pytest.raises(InvalidScanInputError, match="None"):
            handle_scan_input(None)

    def test_unsupported_type_raises_error(self):
        """Test that unsupported types raise InvalidScanInputError."""
        with pytest.raises(InvalidScanInputError, match="Unsupported input type"):
            handle_scan_input(123)

        with pytest.raises(InvalidScanInputError, match="Unsupported input type"):
            handle_scan_input(["list", "input"])

    def test_preserve_unicode(self):
        """Test that Unicode characters are preserved."""
        input_text = "Vulnerability: SQL注入 (A03:2021)"
        result = handle_scan_input(input_text)
        assert "SQL注入" in result

    def test_large_input_warning(self, caplog):
        """Test that large inputs trigger a warning."""
        import logging

        # Create input larger than 1MB
        large_input = "x" * 1_000_001

        with caplog.at_level(logging.WARNING):
            result = handle_scan_input(large_input)

        # Should process but log warning
        assert len(result) == 1_000_001
        assert "Processing large input" in caplog.text

    def test_json_formatting(self):
        """Test that dict input produces properly formatted JSON."""
        input_dict = {
            "findings": ["A01:2021"],
            "nested": {"key": "value"}
        }

        result = handle_scan_input(input_dict)

        # Should be indented JSON
        assert '"findings"' in result
        assert '  "findings"' in result  # Check indentation
        assert '"A01:2021"' in result

    def test_whitespace_normalization(self):
        """Test comprehensive whitespace normalization."""
        input_text = """
        Line with trailing spaces



        Multiple blank lines above
        \tTab character
        Mixed   spaces
        """

        result = handle_scan_input(input_text)

        # Should normalize but preserve structure
        assert "Line with trailing spaces\n" in result
        assert "\n\n" in result  # Multiple newlines collapsed to 2
        assert "\n\n\n" not in result  # No triple newlines
        assert "Mixed   spaces" in result  # Internal spaces preserved


class TestCliTool:
    """Test CLI functionality (integration tests)."""

    def test_cli_with_json_file(self, tmp_path):
        """Test CLI with JSON input file."""
        # Create test JSON file
        test_file = tmp_path / "test.json"
        test_data = {"scan": "results", "api_key": "secret"}
        test_file.write_text(json.dumps(test_data))

        # Import CLI after file creation
        from app.ingest_input import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["--input-file", str(test_file)])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["scan"] == "results"
        assert output["api_key"] == "***REDACTED***"

    def test_cli_with_text_file(self, tmp_path):
        """Test CLI with text input file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Scan found A01:2021\r\nand T1059")

        from app.ingest_input import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["--input-file", str(test_file)])

        assert result.exit_code == 0
        assert "A01:2021" in result.output
        assert "T1059" in result.output
        assert "\r" not in result.output  # Line endings normalized

    def test_cli_with_output_file(self, tmp_path):
        """Test CLI with output file option."""
        input_file = tmp_path / "input.txt"
        output_file = tmp_path / "output.txt"
        input_file.write_text("Test content")

        from app.ingest_input import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--input-file", str(input_file),
            "--output-file", str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists()
        assert output_file.read_text() == "Test content"
        assert "✅" in result.stderr  # Success message to stderr