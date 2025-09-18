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

## Getting Started

Follow these steps to set up and run the project locally.

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

Create a `.env` file by copying the example file.

```bash
cp .env.example .env
```

Now, edit the `.env` file and add your credentials and configuration:

```dotenv
# Application
APP_ENV=dev
LOG_LEVEL=INFO

# Database (asyncpg URL)
DATABASE_URL=postgresql+asyncpg://rag_user:rag_pass@localhost:54320/rag_db

# OpenAI
OPENAI_API_KEY=sk-***
LLM_MODEL_NAME=gpt-4o
```

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

### 7\. Ingest Knowledge Base Data

#### MITRE ATT&CK Data (Available Now)

Extract MITRE ATT&CK Enterprise techniques and sub-techniques:

```bash
# Test ingestion (dry run)
poetry run python -m app.ingestion.ingest_mitre --dry-run

# Extract data to default location
poetry run python -m app.ingestion.ingest_mitre

# Extract to custom location
poetry run python -m app.ingestion.ingest_mitre --output /path/to/mitre.jsonl
```

#### OWASP Top 10 Data (Available Now)

Extract OWASP Top 10 2021 vulnerabilities:

```bash
# Test ingestion (dry run)
poetry run python -m app.ingestion.ingest_owasp --dry-run

# Extract data to default location
poetry run python -m app.ingestion.ingest_owasp

# Extract to custom location
poetry run python -m app.ingestion.ingest_owasp --output /path/to/owasp.jsonl
```

#### Full Knowledge Base Population (Coming Soon)

The complete ingestion and embedding pipeline is under development:

```bash
# Future: Run full ingestion and embedding script
poetry run python scripts/populate_db.py
```

**Note:** The embedding script will make hundreds of calls to the OpenAI API and may incur costs.

## Usage

### 1\. Run the Application

Start the FastAPI server using Uvicorn.

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### 2\. Send an Analysis Request

You can send a POST request to the `/analyze` endpoint with a raw text payload containing the scan report. The bot will extract any recognized OWASP and MITRE ATT\&CK identifiers and return a structured analysis.

Here is an example using `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
-H "Content-Type: application/json" \
-d '{
  "report_text": "Scan complete. Findings include potential A03:2021 Injection vulnerability and evidence of T1059 Command and Scripting Interpreter usage."
}'
```

The API will return a JSON object containing a detailed, conversational breakdown for each identified vulnerability.

## Running Tests

To run the integration test suite, use `pytest`:

```bash
poetry run pytest
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.