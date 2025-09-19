"""Orchestrator service for end-to-end vulnerability analysis workflows.

This module coordinates the complete analysis pipeline from vulnerability identification
through knowledge retrieval to final structured analysis output.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union

from app.agent import AgentDependencies, get_agent
from app.ingest_input import handle_scan_input
from app.models import AnalysisRequest, AnalyzedVulnerability, VulnerabilityFinding
from app.parser import extract_vulnerability_ids

logger = logging.getLogger(__name__)


class VulnerabilityAnalysisOrchestrator:
    """Orchestrates the complete vulnerability analysis workflow."""

    def __init__(self, dependencies: AgentDependencies):
        """Initialize the orchestrator with agent dependencies.

        Args:
            dependencies: Configured agent dependencies (database, OpenAI client)
        """
        self.deps = dependencies
        self.agent = get_agent()

    async def analyze_vulnerability(self, vulnerability_id: str) -> AnalyzedVulnerability:
        """Analyze a single vulnerability using the complete RAG pipeline.

        Args:
            vulnerability_id: The vulnerability identifier to analyze

        Returns:
            Comprehensive vulnerability analysis
        """
        logger.info(f"Starting analysis for vulnerability: {vulnerability_id}")

        try:
            # Create analysis prompt that guides the agent to use tools
            prompt = f"""Please analyze the vulnerability {vulnerability_id}.

Follow this process:
1. First, use the search_vulnerability_knowledge tool to retrieve relevant information
2. Based on the retrieved context, provide a comprehensive analysis

I need a complete analysis including technical details, severity assessment,
prevention strategies, and detection methods."""

            # Run the agent analysis
            result = await self.agent.run(prompt, deps=self.deps)

            logger.info(f"Analysis completed for vulnerability: {vulnerability_id}")
            # In Pydantic AI 1.0.8, the result data is accessed directly from the result object
            return result

        except Exception as e:
            logger.error(f"Analysis failed for {vulnerability_id}: {e}")
            raise

    async def analyze_multiple_vulnerabilities(
        self, vulnerability_ids: List[str], max_analyses: int = 10
    ) -> List[AnalyzedVulnerability]:
        """Analyze multiple vulnerabilities in sequence.

        Args:
            vulnerability_ids: List of vulnerability identifiers
            max_analyses: Maximum number of vulnerabilities to analyze

        Returns:
            List of vulnerability analyses
        """
        # Limit the number of analyses to prevent resource exhaustion
        ids_to_analyze = vulnerability_ids[:max_analyses]

        logger.info(f"Starting batch analysis for {len(ids_to_analyze)} vulnerabilities")

        results = []
        for vuln_id in ids_to_analyze:
            try:
                analysis = await self.analyze_vulnerability(vuln_id)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze {vuln_id}: {e}")
                # Continue with other vulnerabilities even if one fails
                continue

        logger.info(f"Batch analysis completed: {len(results)}/{len(ids_to_analyze)} successful")
        return results

    async def process_analysis_request(self, request: AnalysisRequest) -> List[AnalyzedVulnerability]:
        """Process a complete analysis request.

        Args:
            request: The analysis request containing vulnerability IDs or scan content

        Returns:
            List of vulnerability analyses
        """
        logger.info("Processing analysis request")

        # For now, we'll handle vulnerability IDs directly
        # Scan content parsing would be implemented here in the future
        if request.scan_content:
            logger.warning("Scan content parsing not yet implemented")
            raise NotImplementedError("Scan content parsing not yet supported")

        if not request.vulnerability_ids:
            logger.error("No vulnerability IDs provided in request")
            raise ValueError("No vulnerability IDs provided")

        # Analyze the requested vulnerabilities
        return await self.analyze_multiple_vulnerabilities(
            request.vulnerability_ids,
            request.max_findings_to_analyze
        )

    async def chat_analysis(self, message: str) -> AnalyzedVulnerability:
        """Handle conversational analysis requests.

        Args:
            message: User message that may contain vulnerability references

        Returns:
            Structured analysis result
        """
        logger.info(f"Processing chat analysis: {message[:100]}...")

        try:
            # Run the agent with the user's message
            # The agent will decide whether to use tools based on the message content
            result = await self.agent.run(message, deps=self.deps)

            logger.info("Chat analysis completed successfully")
            # In Pydantic AI 1.0.8, the result data is accessed directly from the result object
            return result

        except Exception as e:
            logger.error(f"Chat analysis failed: {e}")
            raise

    async def analyze_scan_report(
        self,
        raw: Union[str, dict],
        max_concurrent: int = 5,
        timeout_per_analysis: float = 30.0
    ) -> List[AnalyzedVulnerability]:
        """Analyze a complete scan report by extracting and processing all vulnerability IDs.

        This is the main orchestration function that implements the full pipeline:
        1. Normalize the input (handle JSON/text)
        2. Extract vulnerability IDs using the parser
        3. Analyze each unique vulnerability with concurrency control
        4. Return results, handling failures gracefully

        Args:
            raw: Raw scan output as string or dictionary
            max_concurrent: Maximum number of concurrent analyses (default: 5)
            timeout_per_analysis: Timeout in seconds for each analysis (default: 30)

        Returns:
            List of analyzed vulnerabilities in order of extraction
        """
        start_time = time.time()
        logger.info("Starting scan report analysis")

        # Step 1: Normalize the input
        try:
            normalized_text = handle_scan_input(raw)
            logger.debug(f"Normalized {len(normalized_text)} characters of input")
        except Exception as e:
            logger.error(f"Failed to normalize input: {e}")
            raise

        # Step 2: Extract vulnerability IDs
        findings = extract_vulnerability_ids(normalized_text)
        logger.info(f"Extracted {len(findings)} unique vulnerability IDs")

        if not findings:
            logger.warning("No vulnerability IDs found in input")
            return []

        # Step 3: Analyze each vulnerability with concurrency control
        results: List[AnalyzedVulnerability] = []
        errors: List[Dict[str, str]] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_timeout(finding: VulnerabilityFinding, index: int):
            """Analyze a single vulnerability with timeout and error handling."""
            async with semaphore:
                vuln_id = finding.id
                logger.debug(f"Analyzing vulnerability {index+1}/{len(findings)}: {vuln_id}")

                try:
                    # Apply timeout to individual analysis
                    analysis = await asyncio.wait_for(
                        self.analyze_vulnerability(vuln_id),
                        timeout=timeout_per_analysis
                    )
                    return (index, analysis, None)

                except asyncio.TimeoutError:
                    error_msg = f"Analysis timeout for {vuln_id} after {timeout_per_analysis}s"
                    logger.warning(error_msg)
                    return (index, None, {"id": vuln_id, "error": error_msg})

                except Exception as e:
                    error_msg = f"Analysis failed for {vuln_id}: {str(e)}"
                    logger.error(error_msg)
                    return (index, None, {"id": vuln_id, "error": error_msg})

        # Create tasks for all findings
        tasks = [
            analyze_with_timeout(finding, i)
            for i, finding in enumerate(findings)
        ]

        # Execute all tasks concurrently
        task_results = await asyncio.gather(*tasks)

        # Sort results by original index to preserve extraction order
        task_results.sort(key=lambda x: x[0])

        # Collect successful results and errors
        for index, analysis, error in task_results:
            if analysis:
                results.append(analysis)
            if error:
                errors.append(error)

        # Log summary
        elapsed_time = time.time() - start_time
        logger.info(
            f"Scan report analysis completed in {elapsed_time:.2f}s: "
            f"{len(results)}/{len(findings)} successful, {len(errors)} failed"
        )

        if errors:
            logger.warning(f"Failed analyses: {errors}")

        return results


# Convenience function for direct use
async def analyze_scan_report(
    raw: Union[str, dict],
    dependencies: AgentDependencies,
    **kwargs
) -> List[AnalyzedVulnerability]:
    """Convenience function to analyze a scan report without instantiating the orchestrator.

    Args:
        raw: Raw scan output as string or dictionary
        dependencies: Configured agent dependencies
        **kwargs: Additional arguments passed to orchestrator.analyze_scan_report()

    Returns:
        List of analyzed vulnerabilities
    """
    orchestrator = VulnerabilityAnalysisOrchestrator(dependencies)
    return await orchestrator.analyze_scan_report(raw, **kwargs)