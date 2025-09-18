
# EPIC-3 · Ticket 3.4 — Integrate Retrieval Tool with the Pydantic AI Agent

**Epic:** Core Agent and Retrieval Logic  
**Type:** Feature  
**Priority:** High  
**Estimate:** 0.5-1 day  
**Owner:** Senior SWE  
**Dependencies:** EPIC-3 Tickets 3.2 (agent), 3.3 (retrieval)  
**References:** Master spec

## Summary
Register `retrieve_context` as an agent tool so the LLM can call it during reasoning. Provide explicit type hints and a precise docstring to improve tool selection quality.

## Scope
- Update `src/app/agent.py` to register the tool via `@agent.tool` (or agent API).
- Ensure the tool accepts `query: str` and returns a `RetrievedContext`.
- Confirm schema is surfaced to the LLM (name, args, descriptions).

## Tasks
- [ ] Import retrieval function and decorate/register it with the agent.
- [ ] Write a concise docstring describing purpose, args, and return type.
- [ ] Confirm at runtime that the tool appears in the agent's tool list.
- [ ] Add a minimal integration test: mock DB + embeddings; run the agent with a prompt (e.g., `T1059`) and assert that the tool was invoked and a structured `AnalyzedVulnerability` is produced.
- [ ] Document usage example in `docs/agent.md`.

## Acceptance Criteria
- [ ] Tool is discoverable by the agent and callable in a test run.
- [ ] The agent uses the tool before answering (verified via logs/mocks).
- [ ] Agent output validates against `AnalyzedVulnerability` (result_type).

## Technical Notes
Sketch:
```python
# in src/app/agent.py
from app.retrieval import retrieve_context
agent = build_agent()

@agent.tool
async def get_context(ctx, query: str):
    """Retrieve top-k knowledge base chunks for a vulnerability ID (e.g., 'A03:2021', 'T1059').
    Returns a RetrievedContext with chunks and source URLs."""
    return await retrieve_context(ctx, query)
```
- Keep tool naming concise and descriptive (`get_context`).
- Ensure docstring clearly states behavior and expected inputs.

## Out of Scope
- Orchestrator logic to loop over many findings (Epic 4).
- UI surface/integration.

## Definition of Done
- Tool registered; agent can call it in tests and receive structured data.
- Documentation updated with examples.
