# Data Ingestion Documentation

This document describes the data ingestion pipeline for the Vulnerability Analysis RAG Bot.

## MITRE ATT&CK Ingestion

### Overview

The MITRE ATT&CK ingestion service (`src/app/ingestion/ingest_mitre.py`) fetches the latest MITRE ATT&CK Enterprise matrix data and extracts technique and sub-technique records for use in the RAG knowledge base.

### Usage

```bash
# Dry run to see what would be extracted
poetry run python -m app.ingestion.ingest_mitre --dry-run

# Extract data and save to default location (data/raw/mitre.jsonl)
poetry run python -m app.ingestion.ingest_mitre

# Extract data to custom location
poetry run python -m app.ingestion.ingest_mitre --output /path/to/output.jsonl

# Enable debug logging
poetry run python -m app.ingestion.ingest_mitre --log-level DEBUG
```

### Data Sources

- **Source**: MITRE ATT&CK Enterprise Matrix
- **Format**: STIX 2.x via `mitreattack-python` library
- **Scope**: Enterprise techniques and sub-techniques only (Mobile/ICS excluded for MVP)

### Extracted Fields

Each MITRE record includes:

- `source`: Always "mitre"
- `id`: ATT&CK ID (e.g., "T1059", "T1059.001")
- `title`: Technique name (e.g., "Command and Scripting Interpreter")
- `description`: Full technique description
- `url`: Official MITRE ATT&CK URL (if available)
- `stix_id`: Internal STIX object identifier

### Filtering

The ingestion process automatically filters out:

- Revoked techniques
- Deprecated techniques
- Patterns without valid ATT&CK IDs
- Patterns with empty names or descriptions

### Output Format

Data is saved as JSONL (JSON Lines) format, with one record per line:

```json
{"source": "mitre", "id": "T1059", "title": "Command and Scripting Interpreter", "description": "Adversaries may abuse...", "url": "https://attack.mitre.org/techniques/T1059/", "stix_id": "attack-pattern--..."}
{"source": "mitre", "id": "T1059.001", "title": "PowerShell", "description": "Adversaries may abuse PowerShell...", "url": "https://attack.mitre.org/techniques/T1059/001/", "stix_id": "attack-pattern--..."}
```

### Expected Volume

- **Techniques**: ~200-300 main techniques
- **Sub-techniques**: ~400-500 sub-techniques
- **Total**: ~600-800 records (as of 2024)

### Technical Notes

- Unicode characters in descriptions are preserved
- Network requests are made by the `mitreattack-python` library
- Data is fetched fresh each run (no local caching by default)
- Processing typically takes 30-60 seconds depending on network speed

### Testing

Run the test suite:

```bash
poetry run pytest tests/test_ingest_mitre.py -v
```

The tests use mocked data to avoid network dependencies and ensure consistent results.

## Error Handling

Common issues and solutions:

- **Network errors**: Check internet connectivity and retry
- **Missing ATT&CK IDs**: Some patterns may lack proper external references (filtered out)
- **Import errors**: Ensure `mitreattack-python` is installed via `poetry install`

## OWASP Top 10 Ingestion

### Overview

The OWASP Top 10 ingestion service (`src/app/ingestion/ingest_owasp.py`) fetches and parses OWASP Top 10 2021 vulnerability content from the official OWASP website and extracts structured data for the RAG knowledge base.

### Usage

```bash
# Dry run to see what would be extracted
poetry run python -m app.ingestion.ingest_owasp --dry-run

# Extract data and save to default location (data/raw/owasp.jsonl)
poetry run python -m app.ingestion.ingest_owasp

# Extract data to custom location
poetry run python -m app.ingestion.ingest_owasp --output /path/to/output.jsonl

# Enable debug logging
poetry run python -m app.ingestion.ingest_owasp --log-level DEBUG
```

### Data Sources

- **Source**: OWASP Top 10 2021 official website
- **Format**: HTML content extraction from individual vulnerability pages
- **Scope**: All 10 vulnerabilities (A01:2021 through A10:2021)

### Extracted Fields

Each OWASP record includes:

- `source`: Always "owasp"
- `id`: Vulnerability ID (e.g., "A01:2021", "A02:2021")
- `title`: Vulnerability name (e.g., "Broken Access Control")
- `description`: Full vulnerability content including description, prevention, examples
- `url`: Official OWASP URL for the vulnerability

### Content Processing

The ingestion process:

- Fetches HTML content from each vulnerability's official page
- Extracts comprehensive descriptions including prevention strategies
- Removes navigation elements and duplicated content
- Preserves formatting while cleaning up HTML artifacts

### Output Format

Data is saved as JSONL (JSON Lines) format, with one record per line:

```json
{"source": "owasp", "id": "A01:2021", "title": "Broken Access Control", "description": "Access control enforces policy...", "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"}
{"source": "owasp", "id": "A02:2021", "title": "Cryptographic Failures", "description": "The first thing is to determine...", "url": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/"}
```

### Expected Volume

- **Vulnerabilities**: Exactly 10 records (A01:2021 through A10:2021)
- **Content Size**: ~7,000-16,000 characters per vulnerability
- **Total**: ~100KB of structured vulnerability data

### Technical Notes

- Uses BeautifulSoup for HTML parsing
- Includes User-Agent header to avoid blocking
- Content deduplication to prevent repeated text
- Unicode characters in descriptions are preserved
- Processing typically takes 10-15 seconds for all 10 vulnerabilities

### Testing

Run the test suite:

```bash
poetry run pytest tests/test_ingest_owasp.py -v
```

The tests cover data structure validation and title extraction functionality.

## Text Chunking

### Overview

The text chunking service (`src/app/ingestion/chunking.py`) splits vulnerability documents into semantically coherent chunks while preserving context through overlapping windows. This prepares the data for embedding generation and vector storage.

### Usage

```bash
# Dry run to see chunking output
poetry run python -m app.ingestion.chunking --input-file data/raw/owasp.jsonl --dry-run

# Chunk OWASP data with custom settings
poetry run python -m app.ingestion.chunking \
  --input-file data/raw/owasp.jsonl \
  --output-file data/raw/owasp_chunked.jsonl \
  --max-tokens 256 \
  --overlap-tokens 25

# Chunk MITRE data
poetry run python -m app.ingestion.chunking \
  --input-file data/raw/mitre.jsonl \
  --output-file data/raw/mitre_chunked.jsonl \
  --max-tokens 512 \
  --overlap-tokens 50
```

### Chunking Strategy

The chunker uses a recursive approach with prioritized separators:

1. **Paragraph breaks** (`\n\n`) - Preferred for semantic coherence
2. **Sentence endings** (`. `, `! `, `? `) - Maintains logical units
3. **Word boundaries** (` `) - Fallback for smaller chunks
4. **Character level** - Last resort for very long strings

### Chunk Structure

Each chunk includes comprehensive metadata:

```json
{
  "content": "Access control enforces policy such that users cannot act...",
  "vulnerability_id": "A01:2021",
  "title": "Broken Access Control",
  "source": "owasp",
  "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
  "order_index": 0,
  "token_count": 45,
  "overlap_pre": false,
  "overlap_post": true
}
```

### Expected Results

- **OWASP**: 10 vulnerabilities → ~120-130 chunks
- **MITRE**: 679 techniques → ~780-800 chunks
- **Average chunk size**: 900-1200 characters
- **Expansion ratio**: 1.02-1.10x (due to overlap)

## Embedding and Vector Storage

### Overview

The vector population service (`src/app/ingestion/populate_db.py`) generates embeddings for vulnerability chunks using OpenAI's `text-embedding-3-small` model and stores them in PostgreSQL with pgvector for semantic similarity search.

### Usage

```bash
# Dry run to see what would be processed
poetry run python -m app.ingestion.populate_db \
  --input-file data/raw/owasp_chunked.jsonl \
  --dry-run \
  --limit 5

# Populate vector store with OWASP chunks
poetry run python -m app.ingestion.populate_db \
  --input-file data/raw/owasp_chunked.jsonl \
  --batch-size 32

# Populate with MITRE chunks (rebuild entire database)
poetry run python -m app.ingestion.populate_db \
  --input-file data/raw/mitre_chunked.jsonl \
  --rebuild \
  --batch-size 64

# Test similarity search after population
poetry run python -m app.ingestion.populate_db \
  --input-file data/raw/owasp_chunked.jsonl \
  --test-query "SQL injection prevention" \
  --limit 10
```

### Database Schema

The service automatically creates the required schema:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS vulnerability_knowledge (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    source VARCHAR(10) NOT NULL,
    vulnerability_id VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    order_index INT NOT NULL DEFAULT 0,
    content_hash TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_source ON vulnerability_knowledge(source);
CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_vuln ON vulnerability_knowledge(vulnerability_id);
CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_hash ON vulnerability_knowledge(content_hash);
```

### Key Features

- **Idempotent Operations**: Content hashing prevents duplicate insertions
- **Batch Processing**: Configurable batch sizes for optimal performance
- **Rate Limiting**: Respects OpenAI API limits with proper batching
- **Error Handling**: Exponential backoff for transient failures
- **Similarity Testing**: Built-in similarity search validation

### Expected Performance

- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Processing Speed**: ~50-100 chunks per minute (API dependent)
- **Storage Efficiency**: ~6KB per chunk (text + embedding + metadata)
- **Total Storage**: ~5-10MB for complete MITRE + OWASP dataset

### Testing

Run the comprehensive test suite:

```bash
poetry run pytest tests/test_populate_db.py -v
```

Tests cover embedding generation, vector storage, batch processing, and idempotency.

## Complete Pipeline

To process data from ingestion to vector storage:

```bash
# 1. Ingest raw data
poetry run python -m app.ingestion.ingest_mitre
poetry run python -m app.ingestion.ingest_owasp

# 2. Chunk the data
poetry run python -m app.ingestion.chunking --input-file data/raw/mitre.jsonl --output-file data/raw/mitre_chunked.jsonl
poetry run python -m app.ingestion.chunking --input-file data/raw/owasp.jsonl --output-file data/raw/owasp_chunked.jsonl

# 3. Populate vector store
poetry run python -m app.ingestion.populate_db --input-file data/raw/mitre_chunked.jsonl --rebuild
poetry run python -m app.ingestion.populate_db --input-file data/raw/owasp_chunked.jsonl

# 4. Test the system
poetry run python -m app.ingestion.populate_db --input-file data/raw/owasp_chunked.jsonl --test-query "broken authentication" --dry-run
```

## Next Steps

The populated vector store is now ready for:

1. **RAG Agent Development** (Epic 3) - Query interface and context retrieval
2. **Vulnerability Analysis** (Epic 4) - Scan processing and report generation
3. **API Deployment** (Epic 6) - Production-ready endpoints