"""Tests for the vulnerability ID parser module."""

import pytest

from app.parser import (
    extract_vulnerability_ids,
    extract_vulnerability_ids_with_context,
    MITRE_PATTERN,
    OWASP_PATTERN,
    CVE_PATTERN
)
from app.models import VulnerabilityFinding


class TestRegexPatterns:
    """Test the regex patterns for vulnerability IDs."""

    def test_mitre_pattern_basic(self):
        """Test MITRE pattern matches basic technique IDs."""
        text = "Found T1059 and T1055 techniques"
        matches = MITRE_PATTERN.findall(text)
        assert matches == ["T1059", "T1055"]

    def test_mitre_pattern_subtechniques(self):
        """Test MITRE pattern matches sub-techniques."""
        text = "T1059.001 and T1055.012 are sub-techniques"
        matches = MITRE_PATTERN.findall(text)
        assert matches == ["T1059.001", "T1055.012"]

    def test_mitre_pattern_boundaries(self):
        """Test MITRE pattern respects word boundaries."""
        text = "ValidT1059 T1059valid xT1059x T1059"
        matches = MITRE_PATTERN.findall(text)
        assert matches == ["T1059"]  # Only the standalone one

    def test_mitre_pattern_case_insensitive(self):
        """Test MITRE pattern is case-insensitive."""
        text = "t1059 T1059 t1059.001"
        matches = MITRE_PATTERN.findall(text.upper())
        assert len(matches) == 3

    def test_owasp_pattern_basic(self):
        """Test OWASP pattern matches basic IDs."""
        text = "A01:2021 and A10:2021 vulnerabilities"
        matches = OWASP_PATTERN.findall(text)
        assert matches == ["A01:2021", "A10:2021"]

    def test_owasp_pattern_api(self):
        """Test OWASP pattern matches API variants."""
        text = "API1:2023 and API10:2023 are API-specific"
        matches = OWASP_PATTERN.findall(text)
        assert matches == ["API1:2023", "API10:2023"]

    def test_owasp_pattern_boundaries(self):
        """Test OWASP pattern respects word boundaries."""
        text = "xA01:2021x A01:2021 (A02:2021)"
        matches = OWASP_PATTERN.findall(text)
        assert matches == ["A01:2021", "A02:2021"]

    def test_cve_pattern(self):
        """Test CVE pattern matches CVE IDs."""
        text = "CVE-2023-12345 and CVE-2024-0001 found"
        matches = CVE_PATTERN.findall(text)
        assert matches == ["CVE-2023-12345", "CVE-2024-0001"]


class TestExtractVulnerabilityIds:
    """Test the main extraction function."""

    def test_extract_empty_text(self):
        """Test extraction from empty text."""
        assert extract_vulnerability_ids("") == []
        assert extract_vulnerability_ids(None) == []

    def test_extract_single_type(self):
        """Test extraction of a single vulnerability type."""
        text = "Found A01:2021 and A02:2021"
        findings = extract_vulnerability_ids(text)

        assert len(findings) == 2
        assert findings[0].id == "A01:2021"
        assert findings[0].source == "owasp"
        assert findings[1].id == "A02:2021"

    def test_extract_mixed_types(self):
        """Test extraction of mixed vulnerability types."""
        text = "Scan found A01:2021, T1059, CVE-2023-12345, and T1059.001"
        findings = extract_vulnerability_ids(text)

        assert len(findings) == 4
        ids = [f.id for f in findings]
        assert "A01:2021" in ids
        assert "T1059" in ids
        assert "T1059.001" in ids
        assert "CVE-2023-12345" in ids

        # Check sources
        sources = {f.id: f.source for f in findings}
        assert sources["A01:2021"] == "owasp"
        assert sources["T1059"] == "mitre"
        assert sources["CVE-2023-12345"] == "cve"

    def test_deduplication(self):
        """Test that duplicate IDs are removed."""
        text = "A01:2021 appears twice: A01:2021. Also T1059 and T1059."
        findings = extract_vulnerability_ids(text)

        assert len(findings) == 2
        assert findings[0].id == "A01:2021"
        assert findings[1].id == "T1059"

    def test_preserve_order(self):
        """Test that original order is preserved."""
        text = "First T1059, then A01:2021, then CVE-2023-0001, finally T1055"
        findings = extract_vulnerability_ids(text)

        ids = [f.id for f in findings]
        assert ids == ["T1059", "A01:2021", "CVE-2023-0001", "T1055"]

    def test_case_normalization(self):
        """Test that IDs are normalized to uppercase."""
        text = "Found t1059, a01:2021, and cve-2023-0001"
        findings = extract_vulnerability_ids(text)

        ids = [f.id for f in findings]
        assert ids == ["T1059", "A01:2021", "CVE-2023-0001"]

    def test_punctuation_tolerance(self):
        """Test extraction with various punctuation."""
        text = """
        - A01:2021 (Broken Access Control)
        - T1059: Command Execution
        - [CVE-2023-12345]
        - "T1055.001"
        """
        findings = extract_vulnerability_ids(text)

        assert len(findings) == 4
        ids = [f.id for f in findings]
        assert "A01:2021" in ids
        assert "T1059" in ids
        assert "CVE-2023-12345" in ids
        assert "T1055.001" in ids

    def test_no_false_positives(self):
        """Test that similar patterns don't create false positives."""
        text = """
        T1000000 is not valid (too many digits)
        A100:2021 is not valid (3 digits)
        NOTCVE-2023-1 is not valid
        T10a9 is not valid (letter in number)
        """
        findings = extract_vulnerability_ids(text)

        assert len(findings) == 0

    def test_complex_real_world_text(self):
        """Test with complex real-world scan output."""
        text = """
        ## Security Scan Results

        Critical findings:
        1. Broken Access Control (A01:2021) detected in /api/users
        2. Injection vulnerability similar to A03:2021 patterns
        3. Possible MITRE ATT&CK technique T1059 (Command and Scripting Interpreter)
           - Sub-technique T1059.001 (PowerShell) confirmed
        4. CVE-2023-12345 library vulnerability

        Also found: A01:2021 (duplicate), T1055, API1:2023
        """
        findings = extract_vulnerability_ids(text)

        ids = [f.id for f in findings]
        # A01:2021 appears twice but should be deduplicated
        assert ids.count("A01:2021") == 1
        assert "A03:2021" in ids
        assert "T1059" in ids
        assert "T1059.001" in ids
        assert "CVE-2023-12345" in ids
        assert "T1055" in ids
        assert "API1:2023" in ids


class TestExtractWithContext:
    """Test extraction with context functionality."""

    def test_extract_with_context_basic(self):
        """Test basic context extraction."""
        text = "Critical issue: A01:2021 found in authentication module"
        findings = extract_vulnerability_ids_with_context(text, context_chars=32)

        assert len(findings) == 1
        assert findings[0].id == "A01:2021"
        assert "issue: A01:2021" in findings[0].description
        assert "authentication" in findings[0].description

    def test_extract_with_context_boundaries(self):
        """Test context extraction at text boundaries."""
        text = "A01:2021 at start. End with T1059"
        findings = extract_vulnerability_ids_with_context(text, context_chars=10)

        assert len(findings) == 2
        # First finding at start
        assert findings[0].id == "A01:2021"
        assert "A01:2021" in findings[0].description

        # Last finding at end
        assert findings[1].id == "T1059"
        assert "T1059" in findings[1].description
        assert findings[1].description.endswith("...")

    def test_context_whitespace_normalization(self):
        """Test that context whitespace is normalized."""
        text = "Found    A01:2021    with   multiple   spaces"
        findings = extract_vulnerability_ids_with_context(text, context_chars=50)

        assert len(findings) == 1
        # Multiple spaces should be collapsed
        assert "   " not in findings[0].description
        assert "Found A01:2021 with multiple spaces" in findings[0].description


class TestCliTool:
    """Test CLI functionality."""

    def test_cli_basic(self):
        """Test basic CLI functionality."""
        from app.parser import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["--text", "Found A01:2021 and T1059"])

        assert result.exit_code == 0
        assert "A01:2021" in result.output
        assert "T1059" in result.output
        assert "2 unique" in result.output

    def test_cli_with_file(self, tmp_path):
        """Test CLI with file input."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Vulnerabilities: A01:2021, T1059, CVE-2023-0001")

        from app.parser import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["--input-file", str(test_file)])

        assert result.exit_code == 0
        assert "3 unique" in result.output
        assert "A01:2021 (owasp)" in result.output
        assert "T1059 (mitre)" in result.output
        assert "CVE-2023-0001 (cve)" in result.output

    def test_cli_json_output(self):
        """Test CLI with JSON output."""
        from app.parser import cli
        from click.testing import CliRunner
        import json

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--text", "A01:2021",
            "--json"
        ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["id"] == "A01:2021"
        assert data[0]["source"] == "owasp"

    def test_cli_with_context(self):
        """Test CLI with context option."""
        from app.parser import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, [
            "--text", "Critical: A01:2021 in API",
            "--context"
        ])

        assert result.exit_code == 0
        assert "A01:2021" in result.output
        assert "Critical" in result.output  # Context included

    def test_cli_stdin_input(self):
        """Test CLI reading from stdin."""
        from app.parser import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, input="Found T1059 technique")

        assert result.exit_code == 0
        assert "T1059" in result.output

    def test_cli_no_findings(self):
        """Test CLI with text containing no vulnerabilities."""
        from app.parser import cli
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["--text", "No vulnerabilities here"])

        assert result.exit_code == 0
        assert "No vulnerability identifiers found" in result.stderr