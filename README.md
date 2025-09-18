# Vulnerability Analysis RAG Bot

An AI-powered agent that transforms raw API vulnerability scan reports into actionable, conversational intelligence. This bot uses a Retrieval-Augmented Generation (RAG) pipeline, powered by Pydantic AI, to analyze findings based on the OWASP Top 10 and MITRE ATT\&CK frameworks.

## Overview

This project addresses the complexity of typical security scan outputs. Instead of dense reports filled with cryptic identifiers, this bot provides clear, context-rich explanations for each vulnerability. It is designed for security teams, DevOps engineers, and developers who need to quickly assess risks and prioritize remediation.

The system works in three phases:

1.  **Ingestion:** It builds a knowledge base by processing authoritative cybersecurity sources (OWASP, MITRE), creating vector embeddings, and storing them in a `pgvector` database.
2.  **Retrieval:** When given a vulnerability ID from a scan (e.g., `A03:2021` or `T1059`), it retrieves the most relevant explanatory text from its knowledge base.
3.  **Generation:** A Pydantic AI agent synthesizes the finding with the retrieved context and uses a Large Language Model (LLM) to generate a structured, conversational explanation of the vulnerability's severity and impact.

## Features

  * **Automated Analysis:** Ingests raw API scan reports and automatically identifies known vulnerability identifiers.
  * **Rich Context:** Leverages a knowledge base built from the OWASP Top 10 and MITRE ATT\&CK frameworks.
  * **Conversational Output:** Generates clear, human-readable explanations for each finding, assessing severity and suggesting next steps.
  * **Structured Data:** Uses Pydantic models to ensure all inputs and outputs are type-safe and validated.
  * **API-Driven:** Exposes a simple FastAPI endpoint for easy integration into existing security workflows.
  * **Containerized:** Uses Docker for a reproducible and easy-to-deploy environment.

## Technology Stack

| Category | Library/Tool | Purpose |
| ----------------- | -------------------- | ------------------------------------------------------------ |
| **Core Framework** | `pydantic-ai` | The central GenAI agent framework for orchestration. |
| **Web API** | `fastapi` | High-performance web framework for the API endpoint. |
| **LLM & Embeddings**| `openai` | Interface for OpenAI's generation and embedding models. |
| **Database** | `PostgreSQL` + `pgvector` | Vector database for storing and retrieving knowledge embeddings. |
| **Data Ingestion** | `mitreattack-python` | Official library for parsing MITRE ATT\&CK STIX data. |
| | `markdown-it-py` | Versatile Markdown parser for ingesting OWASP documentation. [1, 2] |
| **DevOps** | `Docker` | Containerization for the database and application. |
| **Dependencies** | `Poetry` | Python dependency management and packaging. |
| **Code Quality** | `ruff`, `mypy`, `pytest` | Linting, static type checking, and testing. |

## Project Structure

```
.
├──.github/workflows/      # CI/CD pipelines
├── app/                    # Main application source code
│   ├── __init__.py
│   ├── agent.py            # Pydantic AI agent definition
│   ├── chunking.py         # Text chunking logic
│   ├── config.py           # Configuration management
│   ├── main.py             # FastAPI application and endpoints
│   ├── models.py           # Pydantic data models
│   ├── orchestrator.py     # Main analysis workflow logic
│   └── parser.py           # Parser for vulnerability IDs
├── scripts/                # Data ingestion and database scripts
│   ├── __init__.py
│   ├── ingest_mitre.py     # MITRE ATT&CK data ingestion
│   ├── ingest_owasp.py     # OWASP Top 10 data ingestion
│   └── populate_db.py      # Embedding and DB population script
├── tests/                  # Test suite
│   ├── __init__.py
│   └── test_integration.py # End-to-end integration tests
├──.env.example            # Example environment variables
├──.gitignore
├── docker-compose.yml      # Docker configuration for the database
├── Dockerfile              # Docker configuration for the application
├── pyproject.toml          # Project dependencies and metadata
└── README.md               # This file
```

## Quick Start

**Want to get the bot running in 5 minutes?** Here's the express setup:

```bash
# 1. Clone and install dependencies
git clone <your-repository-url>
cd pyramid
poetry install

# 2. Set up environment
export OPENAI_API_KEY=sk-your-actual-api-key-here
cat > .env << 'EOF'
DATABASE_URL=postgresql://rag_user:rag_pass@localhost:54320/rag_db
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=rag_pass
POSTGRES_DB=rag_db
LLM_MODEL_NAME=gpt-4o
EOF

# 3. Start database and build knowledge base
docker compose up -d
poetry run python -m app.ingestion.ingest_mitre
poetry run python -m app.ingestion.ingest_owasp
poetry run python -m app.ingestion.chunking --input-file data/raw/mitre.jsonl
poetry run python -m app.ingestion.chunking --input-file data/raw/owasp.jsonl
cat data/raw/mitre.chunked.jsonl data/raw/owasp.chunked.jsonl > data/raw/combined.chunked.jsonl
poetry run python -m app.ingestion.populate_db --input-file data/raw/combined.chunked.jsonl --rebuild

# 4. Start the bot
poetry run uvicorn app.main:app --reload

# 5. Test it!
curl -X POST "http://127.0.0.1:8000/chat?message=Analyze%20vulnerability%20A01:2021"
```

🎉 **You now have a fully functional vulnerability analysis bot!**

## Getting Started

For a detailed setup walkthrough, follow these steps:

### 1\. Prerequisites

  * Python 3.12+
  * Poetry ([installation guide](https://python-poetry.org/docs/#installation))
  * Docker and Docker Compose
  * An OpenAI API Key

### 2\. Clone the Repository

```bash
git clone <your-repository-url>
cd pyramid
```

### 3\. Install Dependencies

Install the required Python packages using Poetry.

```bash
poetry install
```

### 4\. Configure Environment Variables

Create a `.env` file with the required configuration:

```bash
cat > .env << 'EOF'
# Database configuration
DATABASE_URL=postgresql://rag_user:rag_pass@localhost:54320/rag_db

# PostgreSQL credentials (used by docker-compose)
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=rag_pass
POSTGRES_DB=rag_db

# LLM Model configuration
LLM_MODEL_NAME=gpt-4o
EOF
```

**Important:** Make sure you have your OpenAI API key set in your shell environment:

```bash
export OPENAI_API_KEY=sk-your-actual-api-key-here
```

You can add this to your `~/.zshrc` or `~/.bashrc` for persistence.

### 5\. Start the Database

Launch the PostgreSQL + `pgvector` database using Docker Compose. This will also create a persistent volume to store the data.

```bash
docker compose up -d
```

### 6\. Verify Setup

Test that everything is working:

```bash
# Run smoke test
poetry run python -m app.hello

# Run tests
poetry run pytest

# Check code quality
poetry run ruff check
poetry run mypy src/
```

### 7\. Build Knowledge Base

The bot requires a populated knowledge base to provide vulnerability analysis. Follow these steps to build it:

#### Step 1: Ingest Raw Data

Extract data from MITRE ATT&CK and OWASP sources:

```bash
# Extract MITRE ATT&CK Enterprise techniques (679 techniques)
poetry run python -m app.ingestion.ingest_mitre

# Extract OWASP Top 10 2021 vulnerabilities (10 vulnerabilities)
poetry run python -m app.ingestion.ingest_owasp
```

This creates raw data files in `data/raw/`.

#### Step 2: Chunk the Data

Process the raw data into optimized chunks for vector search:

```bash
# Chunk MITRE data (783 chunks generated)
poetry run python -m app.ingestion.chunking --input-file data/raw/mitre.jsonl

# Chunk OWASP data (117 chunks generated)
poetry run python -m app.ingestion.chunking --input-file data/raw/owasp.jsonl
```

#### Step 3: Populate Vector Database

Generate embeddings and populate the database (this step costs ~$2-5 in OpenAI API calls):

```bash
# Combine chunked files
cat data/raw/mitre.chunked.jsonl data/raw/owasp.chunked.jsonl > data/raw/combined.chunked.jsonl

# Populate database with embeddings (900 total chunks)
poetry run python -m app.ingestion.populate_db --input-file data/raw/combined.chunked.jsonl --rebuild
```

✅ **After this step, your knowledge base will contain 900 chunks covering 689 vulnerabilities from MITRE ATT&CK and OWASP Top 10!**

## Usage

### 1\. Run the Application

Start the FastAPI server:

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 2\. Test the Health Endpoints

```bash
# Check API status
curl http://127.0.0.1:8000/

# Check health and dependencies
curl http://127.0.0.1:8000/health
```

### 3\. Analyze Vulnerabilities

#### Option A: Chat Interface (Recommended)

Use the conversational chat endpoint for flexible vulnerability analysis:

```bash
curl -X POST "http://127.0.0.1:8000/chat?message=Analyze%20vulnerability%20A01:2021"
```

#### Option B: Direct Analysis

Send specific vulnerability IDs for structured analysis:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"vulnerability_ids": ["A01:2021"]}'
```

### 4\. Example Response

The bot will return comprehensive analysis like this:

```json
{
  "vulnerability_id": "A01:2021",
  "title": "Broken Access Control",
  "summary": "Broken Access Control refers to vulnerabilities where users can act outside of their intended permissions...",
  "severity_assessment": "Broken Access Control is considered highly severe due to its potential to compromise an entire application's integrity...",
  "technical_details": "Attack vectors include URL tampering, parameter manipulation, insecure direct object references...",
  "prevention_strategies": "Implement access controls server-side, adhere to the principle of least privilege...",
  "detection_methods": "Detection involves reviewing access control configurations and employing automated scanning tools...",
  "suggested_next_step": "Would you like me to provide examples of how to implement effective access control in your application?",
  "source_urls": ["https://owasp.org/Top10/A01_2021-Broken_Access_Control/"],
  "confidence_score": 0.98
}
```

### 5\. Supported Vulnerability Types

- **OWASP Top 10 2021**: A01:2021 through A10:2021
- **MITRE ATT&CK**: T1059, T1055, T1003, and 676 other techniques
- **Chat queries**: "Analyze A01:2021", "What is broken access control?", "Explain T1059"

## Running Tests

To run the integration test suite, use `pytest`:

```bash
poetry run pytest
```

## Troubleshooting

### Common Issues

**🔧 "Database connection failed"**
- Make sure Docker is running: `docker compose ps`
- Check if port 54320 is available: `lsof -i :54320`
- Restart the database: `docker compose restart`

**🔧 "OpenAI API error"**
- Verify your API key: `echo $OPENAI_API_KEY`
- Check OpenAI billing and usage limits
- Ensure you have sufficient credits (~$2-5 needed for knowledge base setup)

**🔧 "Tool 'search_vulnerability_knowledge' exceeded max retries"**
- The knowledge base is not populated. Run the ingestion pipeline:
  ```bash
  poetry run python -m app.ingestion.populate_db --input-file data/raw/combined.chunked.jsonl --rebuild
  ```

**🔧 "No vulnerability knowledge found"**
- Verify chunks are in the database:
  ```bash
  poetry run python -c "
  import asyncpg, asyncio
  async def check():
      conn = await asyncpg.connect('postgresql://rag_user:rag_pass@localhost:54320/rag_db')
      count = await conn.fetchval('SELECT COUNT(*) FROM vulnerability_knowledge')
      print(f'Knowledge base contains {count} chunks')
      await conn.close()
  asyncio.run(check())
  "
  ```

### Performance Tips

- **Faster startup**: Keep the database running between sessions
- **Cost optimization**: Use `gpt-4o-mini` instead of `gpt-4o` for testing
- **Better responses**: Try specific queries like "Explain A01:2021 broken access control" instead of just "A01:2021"

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.