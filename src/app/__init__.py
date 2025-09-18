"""
Vulnerability Analysis RAG Bot

An AI-powered agent that transforms raw API vulnerability scan reports
into actionable, conversational intelligence using a Retrieval-Augmented
Generation (RAG) pipeline powered by Pydantic AI.
"""

__version__ = "0.1.0"

# Core models
from .models import (
    AnalysisRequest,
    AnalyzedVulnerability,
    RetrievedContext,
    ScanParsingResult,
    VulnerabilityFinding,
)

# Agent and dependencies
from .agent import (
    AgentDependencies,
    build_agent,
    cleanup_agent_dependencies,
    create_agent_dependencies,
    get_agent,
    test_agent_dependencies,
    vulnerability_agent,
)

# Configuration
from .config import Settings, get_settings

__all__ = [
    # Models
    "AnalysisRequest",
    "AnalyzedVulnerability",
    "RetrievedContext",
    "ScanParsingResult",
    "VulnerabilityFinding",
    # Agent
    "AgentDependencies",
    "build_agent",
    "cleanup_agent_dependencies",
    "create_agent_dependencies",
    "get_agent",
    "test_agent_dependencies",
    "vulnerability_agent",
    # Config
    "Settings",
    "get_settings",
    # Version
    "__version__",
]
