"""Tests for MITRE ATT&CK data ingestion."""

from unittest.mock import Mock, patch

from app.ingestion.ingest_mitre import MitreRecord, load_enterprise_objects


class TestMitreRecord:
    """Test MitreRecord dataclass."""

    def test_mitre_record_creation(self):
        """Test creating a MitreRecord with all fields."""
        record = MitreRecord(
            id="T1059",
            title="Command and Scripting Interpreter",
            description="Adversaries may abuse command and script interpreters...",
            url="https://attack.mitre.org/techniques/T1059/",
            stix_id="attack-pattern--d3df5432-1234-5678-9abc-123456789abc"
        )

        assert record.source == "mitre"
        assert record.id == "T1059"
        assert record.title == "Command and Scripting Interpreter"
        assert record.description.startswith("Adversaries may abuse")
        assert record.url == "https://attack.mitre.org/techniques/T1059/"
        assert record.stix_id == "attack-pattern--d3df5432-1234-5678-9abc-123456789abc"

    def test_mitre_record_defaults(self):
        """Test MitreRecord with default values."""
        record = MitreRecord()

        assert record.source == "mitre"
        assert record.id == ""
        assert record.title == ""
        assert record.description == ""
        assert record.url is None
        assert record.stix_id == ""


class TestLoadEnterpriseObjects:
    """Test the load_enterprise_objects function."""

    @patch("app.ingestion.ingest_mitre.urllib.request.urlopen")
    @patch("app.ingestion.ingest_mitre.tempfile.NamedTemporaryFile")
    @patch("app.ingestion.ingest_mitre.MitreAttackData")
    def test_load_enterprise_objects_with_mock_data(self, mock_mad_class, mock_temp, mock_urlopen):
        """Test loading enterprise objects with mocked MITRE data."""

        # Mock HTTP response
        mock_response = Mock()
        mock_response.read.return_value = b'{"mock": "stix_data"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock temp file
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test.json"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        # Sample STIX technique object
        mock_technique = {
            "id": "attack-pattern--d3df5432-1234-5678-9abc-123456789abc",
            "name": "Command and Scripting Interpreter",
            "description": "Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1059",
                    "url": "https://attack.mitre.org/techniques/T1059/"
                }
            ]
        }

        mock_sub_technique = {
            "id": "attack-pattern--abcd1234-5678-9abc-def0-123456789abc",
            "name": "PowerShell",
            "description": "Adversaries may abuse PowerShell commands and scripts for execution.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1059.001",
                    "url": "https://attack.mitre.org/techniques/T1059/001/"
                }
            ]
        }

        mock_techniques = [mock_technique, mock_sub_technique]

        # Mock the MitreAttackData instance
        mock_mad = Mock()
        mock_mad_class.return_value = mock_mad
        mock_mad.get_techniques.return_value = mock_techniques
        mock_mad.remove_revoked_deprecated.return_value = mock_techniques

        records = load_enterprise_objects()

        # Verify results
        assert len(records) == 2

        # Check first record (technique)
        technique_record = records[0]
        assert technique_record["source"] == "mitre"
        assert technique_record["id"] == "T1059"
        assert technique_record["title"] == "Command and Scripting Interpreter"
        assert "Adversaries may abuse command" in technique_record["description"]
        assert technique_record["url"] == "https://attack.mitre.org/techniques/T1059/"
        assert technique_record["stix_id"] == "attack-pattern--d3df5432-1234-5678-9abc-123456789abc"

        # Check second record (sub-technique)
        sub_technique_record = records[1]
        assert sub_technique_record["source"] == "mitre"
        assert sub_technique_record["id"] == "T1059.001"
        assert sub_technique_record["title"] == "PowerShell"
        assert "PowerShell commands" in sub_technique_record["description"]
        assert sub_technique_record["url"] == "https://attack.mitre.org/techniques/T1059/001/"

    @patch("app.ingestion.ingest_mitre.urllib.request.urlopen")
    @patch("app.ingestion.ingest_mitre.tempfile.NamedTemporaryFile")
    @patch("app.ingestion.ingest_mitre.MitreAttackData")
    def test_load_enterprise_objects_filters_invalid_patterns(self, mock_mad_class, mock_temp, mock_urlopen):
        """Test that invalid patterns are filtered out."""

        # Mock HTTP response
        mock_response = Mock()
        mock_response.read.return_value = b'{"mock": "stix_data"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock temp file
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test.json"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        # Pattern with no MITRE external reference
        invalid_pattern1 = {
            "id": "attack-pattern--invalid1",
            "name": "Invalid Pattern 1",
            "description": "This has no MITRE reference.",
            "external_references": [
                {
                    "source_name": "other-source",
                    "external_id": "OTHER-001",
                    "url": "https://example.com"
                }
            ]
        }

        # Pattern with no external_id
        invalid_pattern2 = {
            "id": "attack-pattern--invalid2",
            "name": "Invalid Pattern 2",
            "description": "This has MITRE reference but no external_id.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "url": "https://attack.mitre.org/techniques/TXXX/"
                }
            ]
        }

        # Pattern with empty name or description
        invalid_pattern3 = {
            "id": "attack-pattern--invalid3",
            "name": "",
            "description": "",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T9999",
                    "url": "https://attack.mitre.org/techniques/T9999/"
                }
            ]
        }

        # Valid pattern for comparison
        valid_pattern = {
            "id": "attack-pattern--valid",
            "name": "Valid Technique",
            "description": "This is a valid technique description.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1234",
                    "url": "https://attack.mitre.org/techniques/T1234/"
                }
            ]
        }

        mock_techniques = [invalid_pattern1, invalid_pattern2, invalid_pattern3, valid_pattern]

        # Mock the MitreAttackData instance
        mock_mad = Mock()
        mock_mad_class.return_value = mock_mad
        mock_mad.get_techniques.return_value = mock_techniques
        mock_mad.remove_revoked_deprecated.return_value = mock_techniques

        records = load_enterprise_objects()

        # Should only return the valid pattern
        assert len(records) == 1
        assert records[0]["id"] == "T1234"
        assert records[0]["title"] == "Valid Technique"

    @patch("app.ingestion.ingest_mitre.urllib.request.urlopen")
    @patch("app.ingestion.ingest_mitre.tempfile.NamedTemporaryFile")
    @patch("app.ingestion.ingest_mitre.MitreAttackData")
    def test_load_enterprise_objects_handles_missing_url(self, mock_mad_class, mock_temp, mock_urlopen):
        """Test handling of patterns without URL in external references."""

        # Mock HTTP response
        mock_response = Mock()
        mock_response.read.return_value = b'{"mock": "stix_data"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock temp file
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test.json"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        pattern_no_url = {
            "id": "attack-pattern--no-url",
            "name": "Technique Without URL",
            "description": "This technique has no URL.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1234"
                    # No URL field
                }
            ]
        }

        # Mock the MitreAttackData instance
        mock_mad = Mock()
        mock_mad_class.return_value = mock_mad
        mock_mad.get_techniques.return_value = [pattern_no_url]
        mock_mad.remove_revoked_deprecated.return_value = [pattern_no_url]

        records = load_enterprise_objects()

        assert len(records) == 1
        assert records[0]["url"] is None

    @patch("app.ingestion.ingest_mitre.urllib.request.urlopen")
    @patch("app.ingestion.ingest_mitre.tempfile.NamedTemporaryFile")
    @patch("app.ingestion.ingest_mitre.MitreAttackData")
    def test_load_enterprise_objects_preserves_unicode(self, mock_mad_class, mock_temp, mock_urlopen):
        """Test that unicode characters in descriptions are preserved."""

        # Mock HTTP response
        mock_response = Mock()
        mock_response.read.return_value = b'{"mock": "stix_data"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Mock temp file
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test.json"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        unicode_pattern = {
            "id": "attack-pattern--unicode-test",
            "name": "Unicode Test Technique",
            "description": "This technique includes unicode: café, résumé, naïve, 中文, 🔒",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T9999",
                    "url": "https://attack.mitre.org/techniques/T9999/"
                }
            ]
        }

        # Mock the MitreAttackData instance
        mock_mad = Mock()
        mock_mad_class.return_value = mock_mad
        mock_mad.get_techniques.return_value = [unicode_pattern]
        mock_mad.remove_revoked_deprecated.return_value = [unicode_pattern]

        records = load_enterprise_objects()

        assert len(records) == 1
        description = records[0]["description"]
        assert "café" in description
        assert "résumé" in description
        assert "naïve" in description
        assert "中文" in description
        assert "🔒" in description
