"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from app.models import (
    AnalysisRequest,
    AnalyzedVulnerability,
    RetrievedContext,
    ScanParsingResult,
    VulnerabilityFinding,
)


class TestVulnerabilityFinding:
    """Test VulnerabilityFinding model."""

    def test_minimal_valid_finding(self):
        """Test creating a minimal valid finding."""
        finding = VulnerabilityFinding(
            id="A01:2021",
            source="owasp"
        )

        assert finding.id == "A01:2021"
        assert finding.source == "owasp"
        assert finding.title is None
        assert finding.description is None

    def test_complete_finding(self):
        """Test creating a complete finding with all fields."""
        finding = VulnerabilityFinding(
            id="T1059.001",
            source="mitre",
            title="PowerShell",
            description="Adversaries may abuse PowerShell commands and scripts..."
        )

        assert finding.id == "T1059.001"
        assert finding.source == "mitre"
        assert finding.title == "PowerShell"
        assert finding.description.startswith("Adversaries may abuse")

    def test_string_stripping(self):
        """Test that whitespace is stripped from string fields."""
        finding = VulnerabilityFinding(
            id="  A01:2021  ",
            source="  owasp  ",
            title="  Broken Access Control  "
        )

        assert finding.id == "A01:2021"
        assert finding.source == "owasp"
        assert finding.title == "Broken Access Control"

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError) as exc_info:
            VulnerabilityFinding(source="owasp")  # Missing id

        assert "id" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            VulnerabilityFinding(id="A01:2021")  # Missing source

        assert "source" in str(exc_info.value)

    def test_source_validation(self):
        """Test source field validation."""
        # Valid sources
        for source in ["owasp", "mitre", "cve", "custom"]:
            finding = VulnerabilityFinding(id="TEST-001", source=source)
            assert finding.source == source

        # Invalid source
        with pytest.raises(ValidationError) as exc_info:
            VulnerabilityFinding(id="TEST-001", source="invalid")

        assert "String should match pattern" in str(exc_info.value)

    def test_empty_id_validation(self):
        """Test that empty ID is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VulnerabilityFinding(id="", source="owasp")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_description_length_validation(self):
        """Test description length limits."""
        # Valid description
        finding = VulnerabilityFinding(
            id="TEST-001",
            source="owasp",
            description="A" * 1000
        )
        assert len(finding.description) == 1000

        # Too long description
        with pytest.raises(ValidationError) as exc_info:
            VulnerabilityFinding(
                id="TEST-001",
                source="owasp",
                description="A" * 6000
            )

        assert "String should have at most 5000 characters" in str(exc_info.value)

    def test_serialization_round_trip(self):
        """Test serialization and deserialization."""
        original = VulnerabilityFinding(
            id="CVE-2023-1234",
            source="cve",
            title="Example Vulnerability",
            description="This is a test vulnerability."
        )

        # Convert to dict and back
        data = original.model_dump()
        recreated = VulnerabilityFinding.model_validate(data)

        assert recreated == original


class TestRetrievedContext:
    """Test RetrievedContext model."""

    def test_minimal_context(self):
        """Test creating minimal retrieved context."""
        finding = VulnerabilityFinding(id="A01:2021", source="owasp")
        context = RetrievedContext(finding=finding)

        assert context.finding == finding
        assert context.retrieved_chunks == []
        assert context.source_urls == []
        assert context.similarity_scores == []
        assert context.retrieval_query is None

    def test_complete_context(self):
        """Test creating complete retrieved context."""
        finding = VulnerabilityFinding(id="T1059", source="mitre")
        context = RetrievedContext(
            finding=finding,
            retrieved_chunks=["Chunk 1", "Chunk 2", "Chunk 3"],
            source_urls=["https://example.com/1", "https://example.com/2"],
            similarity_scores=[0.95, 0.87, 0.72],
            retrieval_query="command injection techniques"
        )

        assert len(context.retrieved_chunks) == 3
        assert len(context.source_urls) == 2
        assert len(context.similarity_scores) == 3
        assert context.retrieval_query == "command injection techniques"

    def test_list_length_limits(self):
        """Test list length validation."""
        finding = VulnerabilityFinding(id="A01:2021", source="owasp")

        # Too many chunks
        with pytest.raises(ValidationError) as exc_info:
            RetrievedContext(
                finding=finding,
                retrieved_chunks=["chunk"] * 25
            )

        assert "List should have at most 20 items" in str(exc_info.value)

        # Too many URLs
        with pytest.raises(ValidationError) as exc_info:
            RetrievedContext(
                finding=finding,
                source_urls=["http://example.com"] * 15
            )

        assert "List should have at most 10 items" in str(exc_info.value)


class TestAnalyzedVulnerability:
    """Test AnalyzedVulnerability model."""

    def test_minimal_valid_analysis(self):
        """Test creating minimal valid analysis."""
        analysis = AnalyzedVulnerability(
            vulnerability_id="A01:2021",
            title="Broken Access Control",
            summary="A" * 50,  # Min length
            severity_assessment="B" * 30,  # Min length
            technical_details="C" * 50,  # Min length
            prevention_strategies="D" * 50,  # Min length
            detection_methods="E" * 30,  # Min length
            suggested_next_step="F" * 20  # Min length
        )

        assert analysis.vulnerability_id == "A01:2021"
        assert analysis.title == "Broken Access Control"
        assert analysis.source_urls == []
        assert analysis.confidence_score is None

    def test_complete_analysis(self):
        """Test creating complete analysis with all fields."""
        analysis = AnalyzedVulnerability(
            vulnerability_id="T1059",
            title="Command and Scripting Interpreter",
            summary="Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.",
            severity_assessment="This is a high-severity technique commonly used in post-exploitation activities.",
            technical_details="This technique involves the abuse of legitimate command-line interfaces and scripting engines.",
            prevention_strategies="Implement application control policies and monitor command-line activity.",
            detection_methods="Monitor process execution and command-line arguments for suspicious activity.",
            suggested_next_step="Would you like me to analyze the specific sub-techniques of T1059?",
            source_urls=["https://attack.mitre.org/techniques/T1059/"],
            confidence_score=0.95
        )

        assert analysis.vulnerability_id == "T1059"
        assert analysis.confidence_score == 0.95
        assert len(analysis.source_urls) == 1

    def test_field_length_validation(self):
        """Test field length validation."""
        base_data = {
            "vulnerability_id": "A01:2021",
            "title": "Test",
            "summary": "A" * 100,
            "severity_assessment": "B" * 50,
            "technical_details": "C" * 100,
            "prevention_strategies": "D" * 100,
            "detection_methods": "E" * 50,
            "suggested_next_step": "F" * 50
        }

        # Test minimum length validation
        with pytest.raises(ValidationError) as exc_info:
            AnalyzedVulnerability(
                **{**base_data, "summary": "Too short"}
            )

        assert "String should have at least 50 characters" in str(exc_info.value)

        # Test maximum length validation
        with pytest.raises(ValidationError) as exc_info:
            AnalyzedVulnerability(
                **{**base_data, "title": "A" * 250}
            )

        assert "String should have at most 200 characters" in str(exc_info.value)

    def test_confidence_score_validation(self):
        """Test confidence score range validation."""
        base_data = {
            "vulnerability_id": "A01:2021",
            "title": "Test",
            "summary": "A" * 100,
            "severity_assessment": "B" * 50,
            "technical_details": "C" * 100,
            "prevention_strategies": "D" * 100,
            "detection_methods": "E" * 50,
            "suggested_next_step": "F" * 50
        }

        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            analysis = AnalyzedVulnerability(**{**base_data, "confidence_score": score})
            assert analysis.confidence_score == score

        # Invalid scores
        for score in [-0.1, 1.1, 2.0]:
            with pytest.raises(ValidationError) as exc_info:
                AnalyzedVulnerability(**{**base_data, "confidence_score": score})

            assert "Input should be less than or equal to 1" in str(exc_info.value) or \
                   "Input should be greater than or equal to 0" in str(exc_info.value)


class TestScanParsingResult:
    """Test ScanParsingResult model."""

    def test_minimal_result(self):
        """Test creating minimal parsing result."""
        result = ScanParsingResult(
            total_findings=0,
            successful_findings=0
        )

        assert result.findings == []
        assert result.parsing_errors == []
        assert result.total_findings == 0
        assert result.successful_findings == 0
        assert result.scan_file_type is None

    def test_complete_result(self):
        """Test creating complete parsing result."""
        findings = [
            VulnerabilityFinding(id="A01:2021", source="owasp"),
            VulnerabilityFinding(id="T1059", source="mitre")
        ]

        result = ScanParsingResult(
            findings=findings,
            parsing_errors=["Error parsing line 5", "Unknown format at line 10"],
            total_findings=5,
            successful_findings=2,
            scan_file_type="nmap"
        )

        assert len(result.findings) == 2
        assert len(result.parsing_errors) == 2
        assert result.total_findings == 5
        assert result.successful_findings == 2
        assert result.scan_file_type == "nmap"

    def test_negative_counts_validation(self):
        """Test that negative counts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScanParsingResult(
                total_findings=-1,
                successful_findings=0
            )

        assert "Input should be greater than or equal to 0" in str(exc_info.value)


class TestAnalysisRequest:
    """Test AnalysisRequest model."""

    def test_minimal_request(self):
        """Test creating minimal analysis request."""
        request = AnalysisRequest()

        assert request.vulnerability_ids == []
        assert request.scan_content is None
        assert request.include_technical_details is True
        assert request.include_prevention_strategies is True
        assert request.max_findings_to_analyze == 10

    def test_ids_only_request(self):
        """Test request with only vulnerability IDs."""
        request = AnalysisRequest(
            vulnerability_ids=["A01:2021", "T1059", "CVE-2023-1234"]
        )

        assert len(request.vulnerability_ids) == 3
        assert request.scan_content is None

    def test_scan_content_request(self):
        """Test request with scan content."""
        request = AnalysisRequest(
            scan_content="<xml>scan results here</xml>",
            include_technical_details=False,
            max_findings_to_analyze=5
        )

        assert request.scan_content == "<xml>scan results here</xml>"
        assert request.include_technical_details is False
        assert request.max_findings_to_analyze == 5

    def test_validation_limits(self):
        """Test validation limits."""
        # Too many vulnerability IDs
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(vulnerability_ids=["ID"] * 60)

        assert "List should have at most 50 items" in str(exc_info.value)

        # Invalid max_findings range
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(max_findings_to_analyze=0)

        assert "Input should be greater than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(max_findings_to_analyze=150)

        assert "Input should be less than or equal to 100" in str(exc_info.value)


class TestModelIntegration:
    """Test model integration and compatibility."""

    def test_finding_in_context(self):
        """Test using VulnerabilityFinding within RetrievedContext."""
        finding = VulnerabilityFinding(
            id="A01:2021",
            source="owasp",
            title="Broken Access Control"
        )

        context = RetrievedContext(
            finding=finding,
            retrieved_chunks=["Access control is critical..."],
            similarity_scores=[0.95]
        )

        assert context.finding.id == "A01:2021"
        assert context.finding.title == "Broken Access Control"

    def test_json_serialization_compatibility(self):
        """Test that all models can be serialized to JSON."""
        import json

        # Test each model type
        finding = VulnerabilityFinding(id="A01:2021", source="owasp")
        finding_json = json.dumps(finding.model_dump())
        assert "A01:2021" in finding_json

        context = RetrievedContext(finding=finding)
        context_json = json.dumps(context.model_dump())
        assert "A01:2021" in context_json

        analysis = AnalyzedVulnerability(
            vulnerability_id="A01:2021",
            title="Test",
            summary="A" * 100,
            severity_assessment="B" * 50,
            technical_details="C" * 100,
            prevention_strategies="D" * 100,
            detection_methods="E" * 50,
            suggested_next_step="F" * 50
        )
        analysis_json = json.dumps(analysis.model_dump())
        assert "A01:2021" in analysis_json

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden in all models."""
        with pytest.raises(ValidationError) as exc_info:
            VulnerabilityFinding(
                id="A01:2021",
                source="owasp",
                extra_field="not allowed"
            )

        assert "Extra inputs are not permitted" in str(exc_info.value)