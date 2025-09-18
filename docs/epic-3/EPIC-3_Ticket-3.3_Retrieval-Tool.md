
# EPIC-3 · Ticket 3.3 — Develop Knowledge Base Retrieval Tool

**Epic:** Core Agent and Retrieval Logic  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1-2 days  
**Owner:** Senior SWE  
**Dependencies:** EPIC-1 Ticket 1.2 (DB), 1.3 (config); EPIC-2 Ticket 2.4 (populated DB); EPIC-3 Tickets 3.1-3.2  
**References:** Master spec

## Summary
Implement an async retrieval function that converts an input vulnerability ID to an embedding, queries `vulnerability_knowledge` using the `pgvector` cosine distance operator, and returns a `RetrievedContext` containing aggregated top-k chunks and URLs.

## Scope
- Module: `src/app/retrieval.py`
- Function: `async def retrieve_context(ctx, query: str) -> RetrievedContext`
- Use the same embedding model as ingestion (`text-embedding-3-small`).
- SQL uses `<->` operator and `LIMIT` (default 5).

## Tasks
- [ ] Implement `embed_query(query: str) -> list[float]` using OpenAI embeddings (async client).
- [ ] Implement DB query with `ORDER BY embedding <-> $1 LIMIT $2`.
- [ ] Aggregate `content` fields into a single formatted string or a list for the agent.
- [ ] Collect unique `url` values in retrieval results.
- [ ] Construct and return `RetrievedContext` with the original `VulnerabilityFinding`.
- [ ] Add configuration for `top_k` (default 5).
- [ ] Unit tests: mock OpenAI + DB; verify SQL is called with correct params; validate outputs.

## Acceptance Criteria
- [ ] Given a query like `T1059`, the function returns up to `top_k` chunks ordered by similarity.
- [ ] Returned object includes `finding`, `retrieved_chunks` (non-empty strings), and `source_urls` (unique).
- [ ] Uses the same embedding model dimension (1536) as the stored vectors.
- [ ] Tests simulate both non-empty and empty DB results.

## Technical Notes
SQL sketch:
```sql
SELECT content, url
FROM vulnerability_knowledge
ORDER BY embedding <-> $1
LIMIT $2;
```

Python sketch:
```python
# src/app/retrieval.py
import asyncpg
from openai import AsyncOpenAI
from app.models import RetrievedContext, VulnerabilityFinding
from typing import Sequence

async def retrieve_context(ctx, query: str, top_k: int = 5) -> RetrievedContext:
    # 1) embed query
    emb = await ctx.deps.oai.embeddings.create(
        model="text-embedding-3-small", input=query
    )
    vec = emb.data[0].embedding

    # 2) query DB
    rows: Sequence[asyncpg.Record] = await ctx.deps.pool.fetch(
        "SELECT content, url FROM vulnerability_knowledge ORDER BY embedding <-> $1 LIMIT $2;",
        vec, top_k
    )
    chunks = [r["content"] for r in rows]
    urls = list({r["url"] for r in rows if r["url"]})
    vf = VulnerabilityFinding(id=query, source="mitre" if query.startswith("T") else "owasp")
    return RetrievedContext(finding=vf, retrieved_chunks=chunks, source_urls=urls)
```
- Consider configurable source filters in the future.
- Ensure timeouts/retries around network calls.

## Out of Scope
- Registration as an agent tool (Ticket 3.4).
- Cross-source weighting or hybrid keyword search.

## Definition of Done
- Retrieval module merged with tests.
- Returns correct shape for agent consumption.
