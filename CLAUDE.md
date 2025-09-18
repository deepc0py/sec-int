# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Vulnerability Analysis RAG Bot** - an AI-powered agent that transforms raw API vulnerability scan reports into actionable, conversational intelligence using a Retrieval-Augmented Generation (RAG) pipeline powered by Pydantic AI.

### Core Architecture

The system operates in three phases:
1. **Ingestion**: Builds a knowledge base from OWASP Top 10 and MITRE ATT&CK frameworks, creates vector embeddings, stores in pgvector database
2. **Retrieval**: Given vulnerability IDs (e.g., `A03:2021`, `T1059`), retrieves relevant explanatory text from knowledge base
3. **Generation**: Pydantic AI agent synthesizes findings with retrieved context using LLM to generate structured, conversational explanations

### Technology Stack

- **Core Framework**: `pydantic-ai` for agent orchestration
- **Web API**: `fastapi` for API endpoints
- **LLM & Embeddings**: `openai` for generation and embedding models
- **Database**: `PostgreSQL` + `pgvector` for vector storage
- **Data Ingestion**: `mitreattack-python` for MITRE data, `markdown-it-py` for OWASP docs
- **Dependencies**: `Poetry` for dependency management
- **Code Quality**: `ruff`, `mypy`, `pytest`

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Start PostgreSQL + pgvector database
docker-compose up -d

# Populate knowledge base (requires OpenAI API key)
poetry run python scripts/populate_db.py
```

### Running the Application
```bash
# Start FastAPI server
poetry run uvicorn app.main:app --reload

# API available at http://127.0.0.1:8000
```

### Testing
```bash
# Run test suite
poetry run pytest
```

### Code Quality
```bash
# Linting and formatting
poetry run ruff check
poetry run ruff format

# Type checking
poetry run mypy
```

## Project Structure

```
app/                    # Main application source
├── agent.py           # Pydantic AI agent definition
├── chunking.py        # Text chunking logic
├── config.py          # Configuration management
├── main.py            # FastAPI application and endpoints
├── models.py          # Pydantic data models
├── orchestrator.py    # Main analysis workflow logic
└── parser.py          # Vulnerability ID parser

scripts/                # Data ingestion scripts
├── ingest_mitre.py    # MITRE ATT&CK data ingestion
├── ingest_owasp.py    # OWASP Top 10 data ingestion
└── populate_db.py     # Embedding and DB population

tests/                  # Test suite
└── test_integration.py # End-to-end integration tests
```

## Environment Configuration

Required environment variables (see .env.example):
- `OPENAI_API_KEY`: OpenAI API key for LLM and embeddings
- `LLM_MODEL_NAME`: Model to use (e.g., "gpt-4o")
- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials

## Development Notes

### Current State
This repository contains comprehensive documentation and specifications in the `docs/` directory with detailed epics, user stories, and technical implementation notes. The actual implementation appears to be in planning/specification phase.

### Key Implementation Details
- Uses Pydantic models for type safety throughout the system
- Implements RAG pattern with pgvector for similarity search
- Processes OWASP (A01:2021 format) and MITRE ATT&CK (T1059 format) identifiers
- Generates conversational, structured vulnerability analyses
- Designed for integration into existing security workflows via API

### Database Schema
The vector database uses a `vulnerability_knowledge` table with:
- `content`: Raw text chunks
- `embedding`: Vector(1536) for similarity search
- `source`: 'owasp' or 'mitre'
- `vulnerability_id`: Identifier (e.g., 'A01:2021', 'T1059')
- `title`: Human-readable vulnerability name
- `url`: Source documentation link