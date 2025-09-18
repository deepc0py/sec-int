
# EPIC-2 · Ticket 2.4 — Implement Embedding and Vector Store Population Logic

**Epic:** Knowledge Base Ingestion Pipeline  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Senior SWE  
**Dependencies:** EPIC-1 Ticket 1.2 (DB), Ticket 1.3 (config), Tickets 2.1–2.3 (data + chunks)  
**References:** Master spec

## Summary
Create `populate_db.py` that generates embeddings for each chunk (OpenAI `text-embedding-3-small`) and inserts chunk + metadata into PostgreSQL with `pgvector`, using `asyncpg` and idempotent upserts.

## Background
Embedding consistency (same model for ingestion and retrieval) and rich metadata are critical for accurate RAG and transparent citations.

## Scope
- Script: `src/app/ingestion/populate_db.py`
- Create table `vulnerability_knowledge` if not exists.
- For each chunk: call embeddings API, store `content`, `embedding`, `source`, `vulnerability_id`, `title`, `url`, `order_index`, and hash for idempotency.
- Handle batching, retries, and rate limits.

## Tasks
- [ ] DDL migration (simple inline or SQL file) executed on startup.
- [ ] Implement async OpenAI embeddings client; batch requests where possible.
- [ ] Compute deterministic `content_hash` (e.g., SHA256 of `source|vuln_id|order_index|content`).
- [ ] Upsert semantics: skip insert when `content_hash` exists.
- [ ] Insert using `asyncpg.executemany` or batched statements.
- [ ] Logging: progress, batch size, failures (with backoff).
- [ ] Unit/integration tests with mocked OpenAI and a test DB.
- [ ] CLI flags: `--rebuild` (truncate + reinsert), `--limit`, `--dry-run`.

## Acceptance Criteria
- [ ] Table is created with correct schema and `vector` column dimension 1536.
- [ ] Script processes input chunks and inserts rows; re-running does not duplicate (idempotent).
- [ ] Embedding failures are retried with exponential backoff; failures logged but do not crash the whole run.
- [ ] Basic query sanity check (top-1 nearest neighbor for a sample query) passes at end of run (optional).

## Technical Notes
**Schema (SQL)**
```sql
CREATE TABLE IF NOT EXISTS vulnerability_knowledge (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding VECTOR(1536) NOT NULL,
  source VARCHAR(10) NOT NULL,
  vulnerability_id VARCHAR(20) NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  order_index INT NOT NULL DEFAULT 0,
  content_hash TEXT UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_source ON vulnerability_knowledge(source);
CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_vuln ON vulnerability_knowledge(vulnerability_id);
```

**Insertion sketch**
```python
import hashlib, asyncio, asyncpg
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def embed_texts(texts: list[str]) -> list[list[float]]:
    resp = await client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]

def hash_chunk(source, vid, idx, content) -> str:
    return hashlib.sha256(f"{source}|{vid}|{idx}|{content}".encode()).hexdigest()
```

- Use transactions per batch; tune batch size (e.g., 64–128) respecting token/size limits.
- Store `order_index` to help reconstruction in retrieval stage.
- Consider simple VACUUM/ANALYZE note in docs after bulk insert.

## Out of Scope
- Advanced migrations framework.
- Cloud-hosted Postgres provisioning.

## Definition of Done
- Script merges with tests and docs.
- Table populated from MITRE and OWASP chunks without duplicates; reruns remain idempotent.
