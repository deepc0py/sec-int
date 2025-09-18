
# EPIC-6 · Ticket 6.3 — Implement End-to-End Integration Test Suite

**Epic:** MVP Application and Deployment  
**Type:** QA / Test  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Senior SWE / QA  
**Dependencies:** Tickets 6.1 (API), 6.2 (Container), EPIC-3 (Agent + Models), EPIC-4 (Orchestrator)  
**References:** Master spec

## Summary
Create an E2E integration test that exercises the full workflow: POST `/analyze` with a sample report → parser extracts IDs → agent runs with mocked dependencies → formatted Markdown is returned. Mocks must cover OpenAI embeddings/LLM and DB to keep tests deterministic and fast.

## Scope
- Test file: `tests/test_integration.py`
- Use `fastapi.testclient.TestClient` or `httpx.AsyncClient` for async tests.
- Fixtures: sample scan payload, mock knowledge base records, monkeypatch for OpenAI + asyncpg.

## Tasks
- [ ] Add fixtures for:
  - [ ] Sample payload containing e.g., `"T1059"` and `"A01:2021"`.
  - [ ] Mock retrieval results (chunks + URLs).
- [ ] Monkeypatch:
  - [ ] OpenAI embeddings to return deterministic vectors (size 1536).
  - [ ] Agent `.run()` to return a valid `AnalyzedVulnerability` (or allow tool path with mocked DB).
  - [ ] asyncpg pool to return canned rows for vector search.
- [ ] Test `/healthz` returns 200.
- [ ] Test `/analyze` returns 200, contains `summary_markdown` and `count`.
- [ ] Assert at least one section header appears for each parsed ID.
- [ ] Ensure tests run under CI with no network and no Docker dependency.

## Acceptance Criteria
- [ ] `pytest` passes locally and in CI.
- [ ] Integration test covers request → response and validates structure.
- [ ] Tests are isolated, repeatable, and do not hit external services.
- [ ] Coverage includes happy-path and failure-path (e.g., malformed input 400).

## Technical Notes
Sketch:
```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_analyze_minimal(client, monkeypatch):
    # monkeypatch agent.run or retrieval to avoid network calls
    from app import orchestrator
    async def fake_analyze_scan_report(raw):
        from app.models import AnalyzedVulnerability
        return [AnalyzedVulnerability(
            vulnerability_id="T1059", title="Command and Scripting Interpreter",
            summary="...", severity_assessment="...", suggested_next_step="See mitigations?"
        )]
    monkeypatch.setattr(orchestrator, "analyze_scan_report", fake_analyze_scan_report)

    r = client.post("/analyze", json={"report": "Observed T1059 activity"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["count"] == 1
    assert "# API Scan Analysis" in body["summary_markdown"]
```
- Keep external calls fully mocked to ensure speed and determinism.
