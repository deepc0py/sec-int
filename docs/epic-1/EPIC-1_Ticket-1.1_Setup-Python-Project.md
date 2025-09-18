
# EPIC-1 · Ticket 1.1 — Setup Python Project with Dependency Management

**Epic:** Project Foundation and DevOps  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Senior Software Engineer  
**Dependencies:** None  
**References:** Master spec (“Actionable Development Plan: Vulnerability Analysis RAG Bot”)

## Summary
Initialize a new Python project using a modern dependency manager so dependencies are explicit, version-locked, and easy to install across environments.

## Background
This is the baseline for all subsequent work. We’ll use a `pyproject.toml` with Poetry (or PDM) and pin Python to >=3.12 to satisfy pydantic‑ai requirements.

## Scope
- Create repo scaffolding and dependency/config files.
- Install core, database, ingestion, and dev tooling dependencies defined in the spec.
- Provide a one‑command setup for developers and initial README.

## Tasks
- [ ] Initialize a new repo with a clean project structure:
  - [ ] `src/` package (e.g., `src/app/__init__.py`)
  - [ ] `tests/`
  - [ ] `.gitignore`
  - [ ] `README.md`
- [ ] Add Poetry and configure Python version >= 3.12.
- [ ] Create `pyproject.toml` with dependencies (see below).
- [ ] Generate lockfile and verify deterministic install.
- [ ] Add initial `README.md` with setup instructions.
- [ ] Verify local environment setup via a single command.
- [ ] Add basic `hello world` script under `src/` and a smoke test under `tests/`.

## Acceptance Criteria
- [ ] Project installs with **one command** (e.g., `poetry install`) on a clean machine.
- [ ] `pyproject.toml` exists with metadata, dependencies, and dev dependencies.
- [ ] Python version is constrained to **>= 2**.
- [ ] `README.md` includes environment setup + run instructions.
- [ ] CI can use the lockfile to install deps (future ticket 1.4 will wire CI).

## Technical Notes
**Recommended dependencies (from spec):**
- Core: `pydantic-ai-slim ^1.0` (with `openai` extra), `openai ^1.0`, `fastapi ^0.111`, `uvicorn ^0.29`
- Database: `asyncpg ^0.29`, `psycopg2-binary ^2.9`
- Data Ingestion: `mitreattack-python ^2.0`, `markdown-it-py ^3.0`
- Utilities: `pydantic-settings ^2.2`
- Dev Tools: `pytest ^8.2`, `ruff ^0.4`, `mypy ^1.10`

**Example: `pyproject.toml` (Poetry)**
```toml
[tool.poetry]
name = "vuln-rag-bot"
version = "0.1.0"
description = "MVP for a Vulnerability Analysis RAG bot"
authors = ["Your Team"]
packages = [{ include = "app", from = "src" }]

[tool.poetry.dependencies]
python = ">=3.12,<3.13"
pydantic-ai-slim = {version = "^1.0", extras = ["openai"]}
openai = "^1.0"
fastapi = "^0.111"
uvicorn = "^0.29"
asyncpg = "^0.29"
psycopg2-binary = "^2.9"
mitreattack-python = "^2.0"
markdown-it-py = "^3.0"
pydantic-settings = "^2.2"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2"
ruff = "^0.4"
mypy = "^1.10"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**Setup**
```bash
# Install Poetry (if needed), then:
poetry install
poetry run python -m app.hello  # smoke run if you create app/hello.py
```

## Out of Scope
- CI configuration (covered in Ticket 1.4).
- Docker Compose for the database (Ticket 1.2).
- App configuration model (Ticket 1.3).

## Definition of Done
- Repo scaffolding committed.
- Lockfile present and reproducible install verified.
- Team can clone and run `poetry install` successfully.
