
# EPIC-3 · Ticket 3.2 — Implement Core Pydantic AI Agent

**Epic:** Core Agent and Retrieval Logic  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1-2 days  
**Owner:** Senior SWE  
**Dependencies:** EPIC-1 Ticket 1.3 (config), EPIC-3 Ticket 3.1 (models)  
**References:** Master spec

## Summary
Instantiate the main pydantic_ai.Agent, configure the LLM (openai:gpt-4o), define typed dependencies (DB pool, clients), and set AnalyzedVulnerability as the result_type to enforce structured outputs.

## Scope
- Module: `src/app/agent.py`
- Define `AgentDependencies` dataclass (e.g., `asyncpg.Pool`, OpenAI client).
- Initialize `Agent` with system prompt and result type.
- Provide a small runner wrapper for interactive/local testing.

## Tasks
- [ ] Create `src/app/agent.py` with `AgentDependencies` dataclass.
- [ ] Initialize OpenAI client from settings; create DB pool factory (but do not connect here).
- [ ] Instantiate `Agent` with:
  - [ ] `llm="openai:gpt-4o"` (configurable via settings).
  - [ ] `deps_type=AgentDependencies`.
  - [ ] `result_type=AnalyzedVulnerability`.
  - [ ] `system_prompt` (from spec: senior API security analyst persona; always use tools; ground only in retrieved context).
- [ ] Provide a module function `get_agent(deps: AgentDependencies) -> Agent`.
- [ ] Unit tests: smoke-test instantiation; confirm `result_type` is enforced (validation error on malformed output).

## Acceptance Criteria
- [ ] Importing and constructing the agent does not raise errors.
- [ ] `result_type` validation works: malformed outputs cause validation errors in tests.
- [ ] `system_prompt` present and instructs tool usage and non-hallucination behavior.

## Technical Notes
Sketch:
```python
# src/app/agent.py
from dataclasses import dataclass
from pydantic_ai import Agent
from app.models import AnalyzedVulnerability
from app.config import settings
import asyncpg
from openai import AsyncOpenAI

@dataclass
class AgentDependencies:
    pool: asyncpg.Pool
    oai: AsyncOpenAI

SYSTEM_PROMPT = """
You are a helpful and precise senior cybersecurity analyst specializing in API security.
You will receive a vulnerability ID. Always call tools to retrieve context first.
Base your answer solely on retrieved context. Do not invent facts.
Output must conform to the AnalyzedVulnerability schema.
"""

def build_agent() -> Agent[AgentDependencies, AnalyzedVulnerability]:
    return Agent(
        llm=f"openai:{settings.LLM_MODEL_NAME}",
        deps_type=AgentDependencies,
        result_type=AnalyzedVulnerability,
        system_prompt=SYSTEM_PROMPT,
    )
```
- Keep the model name configurable via `settings.LLM_MODEL_NAME`.
- Do not create the DB pool in the module import path; pass via deps to avoid side effects.

## Out of Scope
- Retrieval tool implementation and DB queries (Ticket 3.3).
- Orchestrator and API endpoints (later epics).

## Definition of Done
- Agent module merged with tests.
- Ready for tools to be registered (Ticket 3.4).
