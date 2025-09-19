"""Tests for the orchestrator module's scan report analysis functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.models import AnalyzedVulnerability, VulnerabilityFinding
from app.orchestrator import VulnerabilityAnalysisOrchestrator, analyze_scan_report


@pytest.fixture
def mock_dependencies():
    """Create mock agent dependencies."""
    deps = MagicMock()
    deps.pool = MagicMock()
    deps.oai = MagicMock()
    return deps


@pytest.fixture
def mock_agent():
    """Create a mock agent that returns valid AnalyzedVulnerability."""
    agent = AsyncMock()

    def create_mock_result(vuln_id):
        """Create a mock analysis result for a vulnerability ID."""
        return AnalyzedVulnerability(
            vulnerability_id=vuln_id,
            title=f"Mock Title for {vuln_id}",
            summary=f"This is a comprehensive mock summary for vulnerability {vuln_id} that provides detailed information about the nature and impact of this security issue",
            severity_assessment="This vulnerability is considered critical due to its potential for remote code execution and data exfiltration",
            technical_details="The vulnerability exists due to improper input validation in the authentication module, allowing attackers to bypass security controls",
            prevention_strategies="Implement proper input validation, use parameterized queries, apply the principle of least privilege, and regular security audits",
            detection_methods="Monitor authentication logs for anomalies, implement intrusion detection systems",
            suggested_next_step="Would you like more details about implementation strategies?",
            source_urls=[f"https://example.com/{vuln_id}"],
            confidence_score=0.95
        )

    # Configure the mock to return different results based on input
    async def mock_run(prompt, deps=None):
        # Extract vulnerability ID from prompt
        if "A01:2021" in prompt:
            return create_mock_result("A01:2021")
        elif "T1059" in prompt:
            return create_mock_result("T1059")
        elif "CVE-2023-12345" in prompt:
            return create_mock_result("CVE-2023-12345")
        elif "FAIL" in prompt:
            raise Exception("Simulated failure")
        else:
            return create_mock_result("UNKNOWN")

    agent.run.side_effect = mock_run
    return agent


class TestAnalyzeScanReport:
    """Test the analyze_scan_report orchestration function."""

    @pytest.mark.asyncio
    async def test_analyze_text_input(self, mock_dependencies, mock_agent):
        """Test analyzing a text scan report."""
        with patch('app.orchestrator.get_agent', return_value=mock_agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            # Test with text input containing multiple vulnerabilities
            scan_text = """
            Security scan results:
            - Found A01:2021 (Broken Access Control)
            - Detected T1059 command execution
            - CVE-2023-12345 library vulnerability
            """

            results = await orchestrator.analyze_scan_report(scan_text)

            # Verify results
            assert len(results) == 3
            assert results[0].vulnerability_id == "A01:2021"
            assert results[1].vulnerability_id == "T1059"
            assert results[2].vulnerability_id == "CVE-2023-12345"

            # Verify agent was called for each unique ID
            assert mock_agent.run.call_count == 3

    @pytest.mark.asyncio
    async def test_analyze_json_input(self, mock_dependencies, mock_agent):
        """Test analyzing a JSON scan report."""
        with patch('app.orchestrator.get_agent', return_value=mock_agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            # Test with JSON input
            scan_json = {
                "scan_results": "Found vulnerabilities: A01:2021, T1059",
                "api_key": "secret123"  # Should be redacted
            }

            results = await orchestrator.analyze_scan_report(scan_json)

            # Verify results
            assert len(results) == 2
            assert results[0].vulnerability_id == "A01:2021"
            assert results[1].vulnerability_id == "T1059"

    @pytest.mark.asyncio
    async def test_deduplication(self, mock_dependencies, mock_agent):
        """Test that duplicate IDs are only analyzed once."""
        with patch('app.orchestrator.get_agent', return_value=mock_agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            # Input with duplicate IDs
            scan_text = "A01:2021 appears twice: A01:2021. Also T1059."

            results = await orchestrator.analyze_scan_report(scan_text)

            # Verify deduplication
            assert len(results) == 2
            assert mock_agent.run.call_count == 2  # Only called once per unique ID

    @pytest.mark.asyncio
    async def test_empty_input(self, mock_dependencies, mock_agent):
        """Test handling of input with no vulnerabilities."""
        with patch('app.orchestrator.get_agent', return_value=mock_agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            scan_text = "No vulnerabilities found in this scan."

            results = await orchestrator.analyze_scan_report(scan_text)

            # Should return empty list
            assert results == []
            assert mock_agent.run.call_count == 0

    @pytest.mark.asyncio
    async def test_partial_failure(self, mock_dependencies):
        """Test that failures in individual analyses don't stop others."""
        # Create a mock agent that fails for specific IDs
        agent = AsyncMock()

        async def mock_run_with_failure(prompt, deps=None):
            if "A01:2021" in prompt:
                return AnalyzedVulnerability(
                    vulnerability_id="A01:2021",
                    title="Broken Access Control",
                    summary="This vulnerability allows users to act outside their intended permissions, leading to unauthorized information disclosure or modification",
                    severity_assessment="High severity due to potential for unauthorized access to sensitive data and system compromise",
                    technical_details="The vulnerability occurs when access control checks are missing or improperly implemented in the application logic",
                    prevention_strategies="Implement proper access controls, deny by default, use secure session management, and validate all user inputs",
                    detection_methods="Monitor for unusual access patterns and implement logging for all access attempts",
                    suggested_next_step="Review and strengthen access control implementation",
                    source_urls=[],
                    confidence_score=0.9
                )
            elif "T1059" in prompt:
                raise Exception("Simulated failure for T1059")
            elif "T1055" in prompt:
                return AnalyzedVulnerability(
                    vulnerability_id="T1055",
                    title="Process Injection",
                    summary="Process injection is a technique used by adversaries to execute code in the context of another process to evade detection",
                    severity_assessment="Medium severity as it enables privilege escalation and defense evasion capabilities",
                    technical_details="Adversaries may inject code into processes in order to evade process-based defenses and possibly elevate privileges",
                    prevention_strategies="Use application control, behavior monitoring, code integrity checks, and restrict process creation permissions",
                    detection_methods="Monitor process behavior for unusual activity and API calls associated with injection",
                    suggested_next_step="Implement process monitoring and behavior analysis",
                    source_urls=[],
                    confidence_score=0.85
                )
            else:
                raise Exception("Unexpected ID")

        agent.run.side_effect = mock_run_with_failure

        with patch('app.orchestrator.get_agent', return_value=agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            scan_text = "Found A01:2021, T1059, and T1055"

            results = await orchestrator.analyze_scan_report(scan_text)

            # Should have 2 successful results (A01:2021 and T1055)
            assert len(results) == 2
            assert results[0].vulnerability_id == "A01:2021"
            assert results[1].vulnerability_id == "T1055"

            # Agent should be called for all 3
            assert agent.run.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, mock_dependencies):
        """Test that concurrency is properly limited."""
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent_seen = 0

        agent = AsyncMock()

        async def mock_run_tracking_concurrency(prompt, deps=None):
            nonlocal concurrent_count, max_concurrent_seen

            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

            # Simulate some work
            await asyncio.sleep(0.01)

            concurrent_count -= 1

            # Extract ID from prompt for result
            if "A" in prompt:
                vuln_id = prompt.split()[-1]
            else:
                vuln_id = "UNKNOWN"

            return AnalyzedVulnerability(
                vulnerability_id=vuln_id,
                title="Test Vulnerability",
                summary="This is a test vulnerability summary that contains sufficient detail to meet the minimum character requirements for testing purposes",
                severity_assessment="Low severity test vulnerability for unit testing the orchestrator functionality",
                technical_details="Test technical details describing the nature of this mock vulnerability with sufficient length",
                prevention_strategies="Test prevention strategies including multiple approaches to mitigate this test vulnerability",
                detection_methods="Test detection methods for identifying this vulnerability in systems",
                suggested_next_step="Continue with testing the orchestrator functionality",
                source_urls=[],
                confidence_score=0.5
            )

        agent.run.side_effect = mock_run_tracking_concurrency

        with patch('app.orchestrator.get_agent', return_value=agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            # Create input with many vulnerabilities
            scan_text = " ".join([f"A{i:02d}:2021" for i in range(1, 11)])

            # Run with concurrency limit of 3
            results = await orchestrator.analyze_scan_report(scan_text, max_concurrent=3)

            # Verify all were processed
            assert len(results) == 10

            # Verify concurrency was limited
            assert max_concurrent_seen <= 3

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_dependencies):
        """Test that individual analysis timeouts are handled gracefully."""
        agent = AsyncMock()

        async def mock_run_with_delay(prompt, deps=None):
            if "A01:2021" in prompt:
                # This one will timeout
                await asyncio.sleep(10)  # Longer than timeout

            return AnalyzedVulnerability(
                vulnerability_id="A02:2021",
                title="Cryptographic Failures",
                summary="This vulnerability involves failures related to cryptography which often lead to sensitive data exposure or system compromise",
                severity_assessment="Low severity in this test case but can be critical in production environments",
                technical_details="Cryptographic failures include weak encryption, improper key management, and use of deprecated algorithms",
                prevention_strategies="Use strong encryption standards, proper key management, secure random number generation, and regular updates",
                detection_methods="Scan for weak ciphers, check certificate validity, and monitor for plaintext transmission",
                suggested_next_step="Review cryptographic implementations",
                source_urls=[],
                confidence_score=0.8
            )

        agent.run.side_effect = mock_run_with_delay

        with patch('app.orchestrator.get_agent', return_value=agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            scan_text = "Found A01:2021 and A02:2021"

            # Use very short timeout for testing
            results = await orchestrator.analyze_scan_report(
                scan_text,
                timeout_per_analysis=0.1
            )

            # Should have only 1 successful result (A02:2021)
            assert len(results) == 1
            assert results[0].vulnerability_id == "A02:2021"

    @pytest.mark.asyncio
    async def test_preserve_order(self, mock_dependencies):
        """Test that results are returned in order of extraction."""
        agent = AsyncMock()

        async def mock_run_with_varying_delays(prompt, deps=None):
            # Extract ID from prompt
            if "T1059" in prompt:
                await asyncio.sleep(0.05)  # Slower
                vuln_id = "T1059"
            elif "A01:2021" in prompt:
                await asyncio.sleep(0.01)  # Faster
                vuln_id = "A01:2021"
            elif "CVE-2023-12345" in prompt:
                await asyncio.sleep(0.03)  # Medium
                vuln_id = "CVE-2023-12345"
            else:
                vuln_id = "UNKNOWN"

            return AnalyzedVulnerability(
                vulnerability_id=vuln_id,
                title="Test Vulnerability for Order Preservation",
                summary="This is a test vulnerability used to verify that the orchestrator preserves the order of vulnerabilities as they appear in the input",
                severity_assessment="Medium severity test case for validating proper ordering in concurrent processing",
                technical_details="Technical details for this test vulnerability ensuring the minimum character count is met for validation",
                prevention_strategies="Prevention strategies for this test case including various mitigation techniques to reach minimum length",
                detection_methods="Detection methods for identifying this test vulnerability in the system",
                suggested_next_step="Verify order preservation in results",
                source_urls=[],
                confidence_score=0.7
            )

        agent.run.side_effect = mock_run_with_varying_delays

        with patch('app.orchestrator.get_agent', return_value=agent):
            orchestrator = VulnerabilityAnalysisOrchestrator(mock_dependencies)

            # Order in input: T1059, A01:2021, CVE-2023-12345
            scan_text = "First T1059, then A01:2021, finally CVE-2023-12345"

            results = await orchestrator.analyze_scan_report(scan_text)

            # Despite different processing times, order should be preserved
            assert len(results) == 3
            assert results[0].vulnerability_id == "T1059"
            assert results[1].vulnerability_id == "A01:2021"
            assert results[2].vulnerability_id == "CVE-2023-12345"


class TestConvenienceFunction:
    """Test the convenience function for scan report analysis."""

    @pytest.mark.asyncio
    async def test_convenience_function(self, mock_dependencies, mock_agent):
        """Test the analyze_scan_report convenience function."""
        with patch('app.orchestrator.get_agent', return_value=mock_agent):
            scan_text = "Found A01:2021"

            results = await analyze_scan_report(scan_text, mock_dependencies)

            assert len(results) == 1
            assert results[0].vulnerability_id == "A01:2021"