"""Core Pydantic AI agent for vulnerability analysis.

This module defines the main AI agent responsible for analyzing vulnerabilities
using retrieved context from the knowledge base. The agent uses structured outputs
and tool-based retrieval to provide accurate, grounded analysis.
"""

import logging
from dataclasses import dataclass
from typing import Any

import asyncpg
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext

from app.config import get_settings
from app.models import AnalyzedVulnerability, RetrievedContext
from app.retrieval import RetrievalService

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies required by the vulnerability analysis agent.

    These dependencies are injected into the agent context and provide
    access to external services like the database and OpenAI API.
    """

    pool: asyncpg.Pool
    """Database connection pool for vector similarity search."""

    oai: AsyncOpenAI
    """OpenAI client for embedding generation and LLM calls."""

    def __post_init__(self):
        """Validate dependencies after initialization."""
        # Check for pool-like interface
        if not hasattr(self.pool, 'acquire'):
            raise TypeError("pool must have an 'acquire' method (asyncpg.Pool-like interface)")

        # Check for OpenAI client-like interface
        if not hasattr(self.oai, 'models'):
            raise TypeError("oai must have a 'models' attribute (AsyncOpenAI-like interface)")


# System prompt that defines the agent's behavior and constraints
SYSTEM_PROMPT = """You are a helpful and precise senior cybersecurity analyst specializing in API security and vulnerability assessment.

Your role is to analyze vulnerability identifiers and provide comprehensive, actionable insights based on authoritative sources.

## Core Principles:
1. **Always use tools first**: Never provide analysis without first retrieving relevant context from the knowledge base
2. **Ground in retrieved context**: Base your analysis ONLY on the information retrieved from tools
3. **Do not hallucinate**: If information is not available in the retrieved context, explicitly state this limitation
4. **Be comprehensive**: Provide detailed technical analysis, severity assessment, and actionable recommendations
5. **Maintain conversation flow**: End with a thoughtful next step to keep the user engaged

## Analysis Structure:
When analyzing a vulnerability, provide:
- **Technical Summary**: What the vulnerability is and how it works
- **Severity Assessment**: Business impact, exploitability, and risk factors
- **Technical Details**: Attack vectors, exploitation methods, and affected components
- **Prevention Strategies**: Specific, actionable mitigation and prevention techniques
- **Detection Methods**: Tools, techniques, and indicators for identifying this vulnerability
- **Next Steps**: A conversational prompt to guide the user's next action

## Quality Standards:
- Use precise technical language appropriate for security professionals
- Include specific examples when available in the retrieved context
- Acknowledge source limitations and knowledge boundaries
- Provide balanced risk assessment considering both severity and exploitability
- Focus on actionable recommendations that can be implemented

Remember: Your analysis is only as good as the context you retrieve. Always start with tool calls to gather relevant information."""


def build_agent() -> Agent[AgentDependencies, AnalyzedVulnerability]:
    """Build and configure the vulnerability analysis agent.

    Returns:
        Configured Pydantic AI agent with proper dependencies and result type
    """
    settings = get_settings()

    agent = Agent(
        model=f"openai:{settings.LLM_MODEL_NAME}",
        output_type=AnalyzedVulnerability,
        deps_type=AgentDependencies,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.tool
    async def search_vulnerability_knowledge(
        ctx: RunContext[AgentDependencies], vulnerability_id: str
    ) -> RetrievedContext:
        """Search the knowledge base for relevant vulnerability information.

        This tool retrieves detailed context about vulnerabilities from the knowledge base
        using vector similarity search. Use this tool FIRST before providing any analysis.

        Args:
            vulnerability_id: The vulnerability identifier to search for (e.g., 'A01:2021', 'T1059')

        Returns:
            Retrieved context including relevant text chunks, source URLs, and metadata
        """
        retrieval_service = RetrievalService(ctx.deps.pool, ctx.deps.oai)

        try:
            context = await retrieval_service.search_vulnerability_knowledge(vulnerability_id)
            logger.info(f"Retrieved {len(context.retrieved_chunks)} chunks for {vulnerability_id}")
            return context
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge for {vulnerability_id}: {e}")
            # Return empty context on failure so analysis can continue
            from app.models import VulnerabilityFinding
            empty_finding = VulnerabilityFinding(
                id=vulnerability_id,
                source="unknown"
            )
            return RetrievedContext(finding=empty_finding)

    logger.info(f"Built vulnerability analysis agent with model: {settings.LLM_MODEL_NAME}")
    return agent


async def create_agent_dependencies(
    database_url: str | None = None,
    openai_api_key: str | None = None
) -> AgentDependencies:
    """Create agent dependencies with database and OpenAI client.

    Args:
        database_url: PostgreSQL connection URL (defaults to settings)
        openai_api_key: OpenAI API key (defaults to settings)

    Returns:
        Configured AgentDependencies instance

    Raises:
        ConnectionError: If database connection fails
        ValueError: If configuration is invalid
    """
    settings = get_settings()

    # Use provided values or fall back to settings
    db_url = database_url or settings.DATABASE_URL
    api_key = openai_api_key or settings.OPENAI_API_KEY

    if not db_url:
        raise ValueError("DATABASE_URL is required")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")

    try:
        # Create database connection pool
        pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=10,
            command_timeout=30
        )

        if not pool:
            raise ConnectionError("Failed to create database connection pool")

        # Create OpenAI client
        oai_client = AsyncOpenAI(api_key=api_key)

        deps = AgentDependencies(pool=pool, oai=oai_client)
        logger.info("Successfully created agent dependencies")
        return deps

    except Exception as e:
        logger.error(f"Failed to create agent dependencies: {e}")
        raise


async def cleanup_agent_dependencies(deps: AgentDependencies) -> None:
    """Clean up agent dependencies and close connections.

    Args:
        deps: AgentDependencies instance to clean up
    """
    try:
        if deps.pool:
            await deps.pool.close()
            logger.info("Closed database connection pool")

        # OpenAI client doesn't need explicit cleanup
        # but we can close the underlying HTTP client if needed
        if hasattr(deps.oai, '_client') and hasattr(deps.oai._client, 'aclose'):
            await deps.oai._client.aclose()
            logger.info("Closed OpenAI client")

    except Exception as e:
        logger.warning(f"Error during dependency cleanup: {e}")


async def test_agent_dependencies(deps: AgentDependencies) -> dict[str, Any]:
    """Test agent dependencies to ensure they're working correctly.

    Args:
        deps: AgentDependencies to test

    Returns:
        Dictionary with test results

    Raises:
        Exception: If critical dependencies fail
    """
    results = {
        "database": False,
        "openai": False,
        "database_error": None,
        "openai_error": None
    }

    # Test database connection
    try:
        async with deps.pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            results["database"] = True
            results["database_version"] = version
            logger.info("Database connection test successful")
    except Exception as e:
        results["database_error"] = str(e)
        logger.error(f"Database connection test failed: {e}")

    # Test OpenAI client
    try:
        # Simple API test - just check if we can make a basic call
        models = await deps.oai.models.list()
        results["openai"] = True
        results["openai_models_count"] = len(models.data) if models else 0
        logger.info("OpenAI client test successful")
    except Exception as e:
        results["openai_error"] = str(e)
        logger.error(f"OpenAI client test failed: {e}")

    return results


# Global agent instance (lazy-loaded)
_vulnerability_agent: Agent[AgentDependencies, AnalyzedVulnerability] | None = None


def get_agent() -> Agent[AgentDependencies, AnalyzedVulnerability]:
    """Get the global vulnerability analysis agent instance.

    The agent is lazy-loaded on first access to avoid requiring
    environment variables during module import.

    Returns:
        The configured vulnerability analysis agent
    """
    global _vulnerability_agent
    if _vulnerability_agent is None:
        _vulnerability_agent = build_agent()
    return _vulnerability_agent


# For backward compatibility - this will be a function that acts like a property
def vulnerability_agent() -> Agent[AgentDependencies, AnalyzedVulnerability]:
    """Get the global vulnerability analysis agent instance.

    Note: This is a function for backward compatibility.
    Prefer using get_agent() directly.
    """
    return get_agent()