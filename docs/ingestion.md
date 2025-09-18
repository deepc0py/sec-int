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

## Next Steps

After MITRE and OWASP ingestion, the extracted data will be:

1. **Chunked** (Ticket 2.3) - Split into smaller, semantically coherent pieces
2. **Embedded** (Ticket 2.4) - Converted to vector embeddings via OpenAI API
3. **Stored** (Ticket 2.4) - Inserted into PostgreSQL with pgvector for retrieval