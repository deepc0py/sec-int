
# EPIC-6 · Ticket 6.1 — Develop Basic API Endpoint to Trigger the Bot

**Epic:** MVP Application and Deployment  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1 day  
**Owner:** Senior SWE  
**Dependencies:** EPIC-3 (agent + tool), EPIC-4 (orchestrator), EPIC-5 (report formatter)  
**References:** Master spec

## Summary
Create a FastAPI application exposing a single POST `/analyze` endpoint that accepts a raw scan report, orchestrates the analysis, and returns a JSON payload with the formatted Markdown report and structured items.

## Scope
- File: `src/app/main.py`  
- Endpoint: `POST /analyze`  
- Request body model:
  - `report: str | dict` (raw text or JSON)  
  - optional: `{ "return_items": bool }` to include individual `AnalyzedVulnerability` objects.
- Response: `{ "ok": true, "summary_markdown": "...", "count": N, "items": [...] }`

## Tasks
- [ ] Add FastAPI app with `/healthz` (200 OK) and `/analyze` endpoints.
- [ ] Pydantic request/response models in `src/app/api_models.py` (or inline).
- [ ] Wire to `analyze_scan_report` (EPIC-4 Ticket 4.3) and `format_final_report` (EPIC-5 Ticket 5.3).
- [ ] Error handling: return 400 on validation errors; 500 with error id for unexpected exceptions.
- [ ] Add uvicorn entrypoint and docstrings.
- [ ] Update `README.md` with curl examples.

## Acceptance Criteria
- [ ] `uvicorn app.main:app --reload` serves the API locally.
- [ ] `POST /analyze` with a valid payload returns 200, includes Markdown report and count.
- [ ] Invalid payloads return 400 with a helpful message.
- [ ] `/healthz` returns 200 and a small JSON body.

## Technical Notes
Sketch:
```python
# src/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.orchestrator import analyze_scan_report
from app.reporting import format_final_report

app = FastAPI(title="Vuln RAG Bot API")

class AnalyzeRequest(BaseModel):
    report: str | dict
    return_items: bool = False

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        items = await analyze_scan_report(req.report)
        md = format_final_report(items)
        body = {"ok": True, "summary_markdown": md, "count": len(items)}
        if req.return_items:
            # pydantic models serialize to dicts
            body["items"] = [i.model_dump() for i in items]
        return body
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # TODO: add error id logging
        raise HTTPException(status_code=500, detail="Internal error")
```

Startup:
```bash
poetry run uvicorn app.main:app --reload
```

## Out of Scope
- Authentication/authorization (future).
- Rate limiting and multi-tenant controls.

## Definition of Done
- Endpoint merged, documented, and callable locally.
