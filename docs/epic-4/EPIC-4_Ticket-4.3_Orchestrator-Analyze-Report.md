
# EPIC-4 · Ticket 4.3 — Create Orchestration Logic to Analyze Scan Report

**Epic:** Scan Result Processing and Orchestration  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Senior SWE  
**Dependencies:** Tickets 4.1–4.2 (input+parser), EPIC-3 Tickets 3.2–3.4 (agent+tool), EPIC-5 Ticket 5.3 (report formatting, later)  
**References:** Master spec

## Summary
Build `analyze_scan_report` that accepts raw scan content, normalizes it, extracts identifiers, iterates through unique findings, invokes the Agent for each to produce `AnalyzedVulnerability`, and returns the full list (to be formatted later). Handle failures per finding and continue.

## Scope
- Module: `src/app/orchestrator.py`
- Public API: `async def analyze_scan_report(raw: str | dict) -> list[AnalyzedVulnerability]`
- Behavior:
  - Normalize input (`handle_scan_input`).
  - Extract IDs (`extract_vulnerability_ids`).
  - For each finding, call `agent.run()` with the ID prompt (e.g., `"Analyze {id}"`).
  - Collect results; log failures and proceed.
  - Optional concurrency with bounded semaphore (e.g., 3–5).

## Tasks
- [ ] Implement orchestration with structured logging and timing metrics.
- [ ] Concurrency (optional for MVP): gather tasks with `asyncio.Semaphore` to avoid API DB/LLM overload.
- [ ] Error handling: catch validation/tool errors; add `errors: list[str]` to a result envelope (or log only).
- [ ] Return `list[AnalyzedVulnerability]` in the order of findings.
- [ ] Provide a convenience sync wrapper for CLI tests.
- [ ] Unit/integration tests:
  - [ ] Mock `agent.run` to return a valid `AnalyzedVulnerability`.
  - [ ] Verify that duplicate IDs are processed once.
  - [ ] Verify partial failure does not abort others.
- [ ] Documentation: `docs/orchestrator.md` with flow diagram.

## Acceptance Criteria
- [ ] Given a raw scan payload fixture, function returns N analyzed items matching extracted IDs.
- [ ] Agent is invoked once per unique ID (validated via mock call count).
- [ ] Failures in a single item do not stop processing remaining items.
- [ ] Optional concurrency respects configured limit (if enabled).

## Technical Notes
Sketch:
```python
# src/app/orchestrator.py
import asyncio, logging
from app.ingest_input import handle_scan_input
from app.parser import extract_vulnerability_ids
from app.agent import build_agent, AgentDependencies
from app.models import AnalyzedVulnerability
import asyncpg
from openai import AsyncOpenAI
from app.config import settings

async def analyze_scan_report(raw: str | dict) -> list[AnalyzedVulnerability]:
    text = handle_scan_input(raw)
    findings = extract_vulnerability_ids(text)
    if not findings:
        return []

    pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    oai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    deps = AgentDependencies(pool=pool, oai=oai)
    agent = build_agent()

    results: list[AnalyzedVulnerability] = []
    sem = asyncio.Semaphore(5)

    async def run_one(fid):
        async with sem:
            try:
                # Minimal prompt format; agent will call the retrieval tool internally
                resp = await agent.run(f"Analyze {fid.id}", deps=deps)
                results.append(resp.data)  # assumes pydantic_ai returns .data as model instance
            except Exception as e:
                logging.exception("Analysis failed for %s", fid.id)

    await asyncio.gather(*(run_one(f) for f in findings))

    await pool.close()
    return results
```
- Keep the prompt simple and ID-centric; agent’s system prompt mandates retrieval before answering.
- Consider per-run timeout; expose concurrency/timeout in settings for tuning.
```
