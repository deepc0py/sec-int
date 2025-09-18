"""Orchestrator service for end-to-end vulnerability analysis workflows.

This module coordinates the complete analysis pipeline from vulnerability identification
through knowledge retrieval to final structured analysis output.
"""

import logging
from typing import List

from app.agent import AgentDependencies, get_agent
from app.models import AnalysisRequest, AnalyzedVulnerability, VulnerabilityFinding

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