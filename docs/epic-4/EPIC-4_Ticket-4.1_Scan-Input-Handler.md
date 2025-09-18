
# EPIC-4 · Ticket 4.1 — Implement Scan Result Input Handler

**Epic:** Scan Result Processing and Orchestration  
**Type:** Feature  
**Priority:** High  
**Estimate:** 0.5–1 day  
**Owner:** Senior SWE  
**Dependencies:** EPIC-1 (project+config), EPIC-3 Ticket 3.1 (models)  
**References:** Master spec (“Actionable Development Plan: Vulnerability Analysis RAG Bot”)

## Summary
Create a handler that accepts raw API vulnerability scan output (JSON or text), validates it, normalizes to a single string, and returns it for downstream parsing.

## Scope
- Module: `src/app/ingest_input.py`
- Public API: `def handle_scan_input(payload: str | dict) -> str`
- Validation: non-empty input; stringify JSON; trim control characters; normalize whitespace.
- Optional CLI: `python -m app.ingest_input --in path/to/file.[json|txt]` prints normalized text.

## Tasks
- [ ] Implement `handle_scan_input(payload)`:
  - [ ] If `dict`, `json.dumps(..., ensure_ascii=False, indent=2)` then strip secrets (simple heuristic keys: `api_key`, `token`).
  - [ ] If `str`, return trimmed text.
  - [ ] Normalize newlines to `\n`; collapse >3 consecutive newlines to 2.
  - [ ] Guard for extremely large input (log a warning and allow; no truncation in MVP).
- [ ] Add error types: `InvalidScanInputError` with helpful message.
- [ ] Unit tests for: empty input, dict input, string input, newline normalization, secret redaction heuristic.
- [ ] Add section to `docs/ingestion.md` describing accepted forms and examples.

## Acceptance Criteria
- [ ] Function returns a non-empty normalized string for valid inputs.
- [ ] Passing empty/whitespace-only or unsupported types raises `InvalidScanInputError`.
- [ ] CLI can read `.json` and `.txt` files and prints normalized text to stdout.
- [ ] Tests cover success/failure paths.

## Technical Notes
Example implementation:
```python
# src/app/ingest_input.py
import json, re
from typing import Any

SECRET_KEYS = {"api_key", "apikey", "token", "secret"}

class InvalidScanInputError(ValueError): ...

def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in SECRET_KEYS else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj

def handle_scan_input(payload: str | dict) -> str:
    if isinstance(payload, dict):
        payload = json.dumps(_redact(payload), ensure_ascii=False, indent=2)
    elif isinstance(payload, str):
        payload = payload.strip()
    else:
        raise InvalidScanInputError("Unsupported input type; expected str or dict")
    if not payload:
        raise InvalidScanInputError("Empty input")
    text = re.sub(r"\r\n?|\f", "\n", payload)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
```
