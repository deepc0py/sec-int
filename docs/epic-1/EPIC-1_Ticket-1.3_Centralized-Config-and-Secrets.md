
# EPIC-1 · Ticket 1.3 — Implement Centralized Configuration and Secrets Management

**Epic:** Project Foundation and DevOps  
**Type:** Feature  
**Priority:** High  
**Estimate:** 0.5–1 day  
**Owner:** Senior Software Engineer  
**Dependencies:** Ticket 1.1 (project scaffold)  
**References:** Master spec

## Summary
Create a type‑safe configuration module using `pydantic-settings` that loads validated settings from environment variables. Provide `.env.example` and ignore `.env`.

## Scope
- Add `config.py` exposing a `Settings` class.
- Load required variables: `DATABASE_URL`, `OPENAI_API_KEY`, `LLM_MODEL_NAME`, etc.
- Fail fast if required variables missing.
- Provide `.env.example` and `.gitignore` entries.

## Tasks
- [ ] Add `pydantic-settings` to dependencies (already specified in Ticket 1.1).
- [ ] Create `src/app/config.py` with `Settings(BaseSettings)`.
- [ ] Define fields and helpful descriptions.
- [ ] Ensure `.env` is ignored; add `.env.example` with placeholders.
- [ ] Wire a small bootstrap snippet that instantiates `Settings()` once (singleton pattern via module import).

## Acceptance Criteria
- [ ] `Settings()` loads from env and validates on startup.
- [ ] Missing required variables raise a clear validation error.
- [ ] `.env.example` documents all required values and formats.
- [ ] `.env` is not tracked by git.

## Technical Notes
**Example: `src/app/config.py`**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_ENV: str = "dev"
    DATABASE_URL: str  # e.g., postgresql+asyncpg://user:pass@localhost:54320/rag_db
    OPENAI_API_KEY: str
    LLM_MODEL_NAME: str = "gpt-4o"  # configurable for future changes

    # Optional extras
    LOG_LEVEL: str = "INFO"

settings = Settings()
```

**Example: `.env.example`**
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

## Out of Scope
- Secret storage in cloud secret managers (future).
- Rotations and audit trails.

## Definition of Done
- Config module merged with docs and example env file.
- App can import `settings` and read validated values.
