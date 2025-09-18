
# EPIC-2 · Ticket 2.3 — Implement Text Chunking Strategy for Technical Documents

**Epic:** Knowledge Base Ingestion Pipeline  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Senior SWE  
**Dependencies:** Tickets 2.1 & 2.2 (normalized MITRE/OWASP records)  
**References:** Master spec

## Summary
Create `chunking.py` implementing a **recursive, structure-aware** chunker that splits each vulnerability document into semantically coherent chunks (~256–512 tokens) with overlap, preserving paragraphs/sentences and attaching metadata.

## Background
Naive fixed-size splits harm retrieval. A prioritized separator approach (paragraph → sentence → fallback) yields higher-quality embeddings for RAG over dense security docs.

## Scope
- Module: `src/app/ingestion/chunking.py`
- Input: one normalized record (`id`, `title`, `description`, `source`, `url`).
- Output: list of chunks with fields:
  - `content`, `vulnerability_id`, `title`, `source`, `url`, `order_index`, `overlap_pre`/`overlap_post` (optional).
- Token target ~256–512; overlap ~50 tokens (configurable).

## Tasks
- [ ] Implement tokenization helper (tiktoken-compatible or heuristic char-to-token ratio).
- [ ] Recursive splitter with prioritized separators: `\n\n` → headings → `. ` (sentence) → fallback split.
- [ ] Preserve sentences; avoid mid-sentence splits unless unavoidable.
- [ ] Add configurable `max_tokens`, `min_tokens`, `overlap_tokens`.
- [ ] Return stable ordering (`order_index`) per parent doc.
- [ ] Unit tests: feed crafted long text; assert sizes, boundaries, overlap semantics.
- [ ] Add simple CLI for dry-runs using sample data from Tickets 2.1/2.2.

## Acceptance Criteria
- [ ] Given a long description, function returns chunks within target token window (±20%).
- [ ] Sentences and paragraphs generally preserved; no empty chunks.
- [ ] Metadata correctly attached; `order_index` strictly increasing.
- [ ] Overlap present between adjacent chunks when needed.
- [ ] Tests cover edge cases (short text, extremely long paragraph, headings).

## Technical Notes
**Interface**
```python
def chunk_document(
    *, text: str, metadata: dict, max_tokens: int = 512, overlap_tokens: int = 50
) -> list[dict]:
    ...
```

- Implement a pluggable tokenizer strategy; default to rough estimator to avoid runtime dependency if needed.
- Consider normalizing whitespace and preserving code blocks/lists as atomic units when possible.

## Out of Scope
- Language detection or multilingual chunking.
- Semantic segmentation via model calls (future enhancement).

## Definition of Done
- Chunker module merged with tests and usage docs.
- Produces high-quality chunks for embeddings (Ticket 2.4).
