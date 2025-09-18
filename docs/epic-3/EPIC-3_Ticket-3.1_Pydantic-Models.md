
# EPIC-3 · Ticket 3.1 — Define Pydantic Models for Vulnerability Data

**Epic:** Core Agent and Retrieval Logic  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1 day  
**Owner:** Senior SWE  
**Dependencies:** EPIC-1 Ticket 1.1 (project), 1.3 (config)  
**References:** Master spec (“Actionable Development Plan: Vulnerability Analysis RAG Bot”)

## Summary
Create Pydantic BaseModel classes to represent the core data contracts for findings, retrieved context, and analyzed results. These models will be used across parsing, retrieval, agent orchestration, and output formatting.

## Scope
- Module: `src/app/models.py`
- Models: `VulnerabilityFinding`, `RetrievedContext`, `AnalyzedVulnerability`
- Include docstrings and field descriptions to guide LLM behavior and developer usage.

## Tasks
- [ ] Add `src/app/models.py` with the three models below.
- [ ] Ensure strict typing: `str`, `list[str]`, `Optional[str]`, etc.
- [ ] Add `model_config` (Pydantic v2) to enable `populate_by_name=True` and useful defaults.
- [ ] Add helpful `Field(..., description="...")` metadata for each field.
- [ ] Unit tests to validate parsing/serialization and required fields.
- [ ] Export models in package `__init__.py` for easy import elsewhere.

## Acceptance Criteria
- [ ] Models compile and pass mypy type checks.
- [ ] Serialization round-trips (dict<->model) work for all fields.
- [ ] Validation errors raised for missing required fields.
- [ ] Docstrings/field descriptions exist and are clear.

## Technical Notes
Suggested model definitions (sketch):
```python
# src/app/models.py
from typing import List, Optional
from pydantic import BaseModel, Field

class VulnerabilityFinding(BaseModel):
    """Represents one parsed finding from a scan report."""
    id: str = Field(..., description="Identifier (e.g., 'A01:2021', 'T1059')")
    source: str = Field(..., description="Source of the identifier: 'owasp' or 'mitre'")

class RetrievedContext(BaseModel):
    """Top-k text chunks retrieved for a given finding."""
    finding: VulnerabilityFinding = Field(..., description="The original finding")
    retrieved_chunks: List[str] = Field(..., description="Top-k retrieved text chunks")
    source_urls: List[str] = Field(default_factory=list, description="Unique source URLs cited")

class AnalyzedVulnerability(BaseModel):
    """Final, structured analysis for a single vulnerability."""
    vulnerability_id: str = Field(..., description="Identifier being analyzed")
    title: str = Field(..., description="Official name/title")
    summary: str = Field(..., description="Concise explanation of the vulnerability")
    severity_assessment: str = Field(..., description="Conversational severity & impact")
    suggested_next_step: str = Field(
        ..., description="Proactive prompt to continue the conversation"
    )
```

## Out of Scope
- Agent construction and DB queries (covered by later tickets).

## Definition of Done
- Models merged with tests and documentation.
- Used downstream by the agent result type (Ticket 3.2) and retrieval (Ticket 3.3).
