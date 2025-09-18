
# EPIC-2 · Ticket 2.2 — Develop OWASP Top 10 Data Ingestion Service

**Epic:** Knowledge Base Ingestion Pipeline  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Data Engineer / Senior SWE  
**Dependencies:** EPIC-1 (project, DB, config)  
**References:** Master spec

## Summary
Create `ingest_owasp.py` to fetch and parse **OWASP Top 10 2021** source Markdown from the official GitHub repo, extract identifiers/titles/descriptions, and normalize for downstream chunking and embedding.

## Background
OWASP publishes Top 10 as Markdown; parsing with `markdown-it-py` yields tokens/AST that allow robust section detection vs. brittle scraping.

## Scope
- Script: `src/app/ingestion/ingest_owasp.py`
- Identify all 10 vulnerabilities (e.g., `A01:2021-Broken Access Control`).
- Extract: identifier (e.g., `A01:2021`), title, full description text, source URL.
- Normalize to dicts: `source="owasp" | id | title | description | url`.
- Optional debug artifact: `data/raw/owasp_top10_2021.jsonl`.

## Tasks
- [ ] Discover canonical Markdown source URLs (constant list for 10 items).
- [ ] Add a simple loader (local file or fetch); store originals under `data/sources/owasp/` (optional).
- [ ] Parse Markdown via `markdown-it-py`:
  - [ ] Find heading pattern matching the 10 identifiers.
  - [ ] Aggregate subsequent paragraphs/lists until next major heading.
- [ ] Normalize fields and emit list[dict].
- [ ] Unit tests: sample doc fixture → verify identifier detection and section boundaries.
- [ ] Logging with counts and any items skipped.
- [ ] README notes under `docs/ingestion.md` (OWASP section).

## Acceptance Criteria
- [ ] Running `poetry run python -m app.ingestion.ingest_owasp --dry-run` prints a count summary and writes optional JSONL.
- [ ] Exactly 10 unique identifiers detected (A01..A10:2021).
- [ ] Each record includes `id`, `title`, `description` (non-empty), `url`, `source="owasp"`.
- [ ] Tests validate: heading detection, content aggregation, de-duplication.

## Technical Notes
**Parsing approach**
```python
# src/app/ingestion/ingest_owasp.py
from markdown_it import MarkdownIt

ID_PATTERN = r"^A(\d{2}):2021"  # adjust for APIs if needed later

def parse_markdown(md: str) -> list[dict]:
    mdp = MarkdownIt()
    tokens = mdp.parse(md)
    # Walk tokens: detect H2/H3 with pattern, collect text until next peer heading
    # Accumulate description preserving paragraphs & lists
    ...
```

- Prefer **structure-aware** parsing; avoid regex-only scraping.
- Keep raw Markdown text but strip HTML artifacts.
- Maintain `url` to the official source (for transparency/citations in UI later).

## Out of Scope
- OWASP API Top 10 (can follow the same pattern later).
- Internationalized versions.

## Definition of Done
- Script merged with tests and docs.
- Produces 10 normalized records for chunking (Ticket 2.3).
