"""Pydantic models for vulnerability data structures.

This module defines the core data contracts used throughout the vulnerability
analysis pipeline, from scan parsing to RAG retrieval to final analysis output.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VulnerabilityFinding(BaseModel):
    """Represents one parsed finding from a vulnerability scan report.

    This model captures the essential information needed to identify and
    retrieve relevant context for a specific vulnerability.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        extra="forbid"
    )

    id: str = Field(
        ...,
        description="Vulnerability identifier (e.g., 'A01:2021', 'T1059', 'CVE-2023-1234')",
        min_length=1,
        examples=["A01:2021", "T1059", "T1059.001"]
    )

    source: str = Field(
        ...,
        description="Source taxonomy of the identifier: 'owasp', 'mitre', 'cve', or 'custom'",
        pattern="^(owasp|mitre|cve|custom)$",
        examples=["owasp", "mitre", "cve"]
    )

    title: Optional[str] = Field(
        default=None,
        description="Human-readable title or name of the vulnerability, if available",
        examples=["Broken Access Control", "Command and Scripting Interpreter"]
    )

    description: Optional[str] = Field(
        default=None,
        description="Additional context or description from the scan report",
        max_length=5000
    )


class RetrievedContext(BaseModel):
    """Top-k text chunks retrieved from the knowledge base for a given finding.

    This model represents the intermediate state after retrieval but before
    analysis, containing the original finding plus relevant context chunks.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        extra="forbid"
    )

    finding: VulnerabilityFinding = Field(
        ...,
        description="The original vulnerability finding that triggered the retrieval"
    )

    retrieved_chunks: list[str] = Field(
        default_factory=list,
        description="Top-k retrieved text chunks ordered by relevance score",
        max_length=20
    )

    source_urls: list[str] = Field(
        default_factory=list,
        description="Unique source URLs cited in the retrieved chunks for attribution",
        max_length=10
    )

    similarity_scores: list[float] = Field(
        default_factory=list,
        description="Similarity scores corresponding to each retrieved chunk",
        max_length=20
    )

    retrieval_query: Optional[str] = Field(
        default=None,
        description="The processed query used for retrieval (may differ from raw ID)",
        max_length=500
    )


class AnalyzedVulnerability(BaseModel):
    """Final, structured analysis output for a single vulnerability.

    This model represents the complete analysis result that will be returned
    to users, including actionable insights and conversation continuity.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        extra="forbid"
    )

    vulnerability_id: str = Field(
        ...,
        description="The original vulnerability identifier being analyzed",
        min_length=1,
        examples=["A01:2021", "T1059"]
    )

    title: str = Field(
        ...,
        description="Official name or title of the vulnerability",
        min_length=1,
        max_length=200,
        examples=["Broken Access Control", "Command and Scripting Interpreter"]
    )

    summary: str = Field(
        ...,
        description="Concise, technical explanation of what the vulnerability is and how it works",
        min_length=50,
        max_length=1000
    )

    severity_assessment: str = Field(
        ...,
        description="Conversational assessment of severity, impact, and business risk",
        min_length=30,
        max_length=800
    )

    technical_details: str = Field(
        ...,
        description="Technical implementation details, attack vectors, and exploitation methods",
        min_length=50,
        max_length=1200
    )

    prevention_strategies: str = Field(
        ...,
        description="Specific, actionable prevention and mitigation strategies",
        min_length=50,
        max_length=1000
    )

    detection_methods: str = Field(
        ...,
        description="Methods and tools for detecting this vulnerability",
        min_length=30,
        max_length=800
    )

    suggested_next_step: str = Field(
        ...,
        description="Proactive, conversational prompt to guide the user's next action",
        min_length=20,
        max_length=300,
        examples=[
            "Would you like me to analyze another vulnerability from your scan?",
            "Should we explore the specific prevention strategies for your application architecture?"
        ]
    )

    source_urls: list[str] = Field(
        default_factory=list,
        description="Source URLs used to generate this analysis for transparency and further reading",
        max_length=10
    )

    confidence_score: Optional[float] = Field(
        default=None,
        description="Confidence score for the analysis quality (0.0-1.0)",
        ge=0.0,
        le=1.0
    )


class ScanParsingResult(BaseModel):
    """Result of parsing a vulnerability scan file.

    This model captures the outcome of scan file processing, including
    successfully parsed findings and any errors encountered.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        extra="forbid"
    )

    findings: list[VulnerabilityFinding] = Field(
        default_factory=list,
        description="Successfully parsed vulnerability findings"
    )

    parsing_errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during parsing"
    )

    total_findings: int = Field(
        ...,
        description="Total number of findings attempted to parse",
        ge=0
    )

    successful_findings: int = Field(
        ...,
        description="Number of successfully parsed findings",
        ge=0
    )

    scan_file_type: Optional[str] = Field(
        default=None,
        description="Detected type of scan file (e.g., 'nmap', 'nessus', 'json')"
    )


class AnalysisRequest(BaseModel):
    """Request model for vulnerability analysis.

    This model structures incoming analysis requests, supporting both
    individual vulnerability IDs and full scan file analysis.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        extra="forbid"
    )

    vulnerability_ids: list[str] = Field(
        default_factory=list,
        description="List of specific vulnerability IDs to analyze",
        max_length=50
    )

    scan_content: Optional[str] = Field(
        default=None,
        description="Raw scan file content to parse and analyze",
        max_length=1000000  # 1MB limit
    )

    include_technical_details: bool = Field(
        default=True,
        description="Whether to include detailed technical analysis"
    )

    include_prevention_strategies: bool = Field(
        default=True,
        description="Whether to include prevention and mitigation strategies"
    )

    max_findings_to_analyze: int = Field(
        default=10,
        description="Maximum number of findings to analyze from scan",
        ge=1,
        le=100
    )