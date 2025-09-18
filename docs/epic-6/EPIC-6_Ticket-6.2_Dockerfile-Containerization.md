
# EPIC-6 · Ticket 6.2 — Containerize the Application for Deployment

**Epic:** MVP Application and Deployment  
**Type:** DevOps  
**Priority:** High  
**Estimate:** 1 day  
**Owner:** DevOps / Senior SWE  
**Dependencies:** EPIC-1 (Poetry + deps), Ticket 6.1 (FastAPI app)  
**References:** Master spec

## Summary
Create a minimal, secure Docker image using a multi-stage build that installs dependencies from the lock file and runs the FastAPI app via uvicorn as a non-root user.

## Scope
- `Dockerfile` at repo root
- `.dockerignore` to keep image small
- Support `POETRY_VERSION`, `APP_ENV`, and standard envs

## Tasks
- [ ] Add `.dockerignore` (e.g., `.venv`, `__pycache__`, `.git`, `tests`, `data/*`, etc.).
- [ ] Implement multi-stage Dockerfile:
  - [ ] Builder stage: install Poetry, install deps with lock, build wheel.
  - [ ] Final stage: copy app, venv/site-packages or wheels; create non-root user; set entrypoint.
- [ ] Healthcheck using `/healthz`.
- [ ] Document build and run commands in README.
- [ ] Optional: add `docker-compose.override.yml` to run API + DB locally.

## Acceptance Criteria
- [ ] `docker build` completes successfully and image size is reasonable (&lt; 400MB target for Python slim base).
- [ ] Container starts, serves `/healthz`, and responds to `/analyze`.
- [ ] Container runs as a non-root user.
- [ ] Environment variables are respected (`APP_ENV`, `OPENAI_API_KEY`, `DATABASE_URL`).

## Technical Notes
Example `Dockerfile`:
```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder
ENV POETRY_VERSION=1.7.1     POETRY_VIRTUALENVS_CREATE=false     PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip && pip install "poetry==${POETRY_VERSION}"
RUN poetry install --no-interaction --no-ansi --only main
COPY src ./src

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     APP_ENV=prod
WORKDIR /app
# add non-root user
RUN useradd -m appuser
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app/src /app/src
EXPOSE 8000
HEALTHCHECK CMD python -c "import requests; import os; print(requests.get('http://127.0.0.1:8000/healthz').status_code)" || exit 1
USER appuser
ENTRYPOINT ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore` essentials:
```
.git
__pycache__/
*.pyc
.venv/
dist/
build/
data/
tests/
```

Run:
```bash
docker build -t vuln-rag-bot:latest .
docker run -p 8000:8000 --env APP_ENV=prod --env OPENAI_API_KEY=sk-*** --env DATABASE_URL="postgresql+asyncpg://rag_user:rag_pass@host.docker.internal:54320/rag_db" vuln-rag-bot:latest
```

## Out of Scope
- Publishing to a registry and CD pipelines.
- Kubernetes manifests (future).

## Definition of Done
- Image builds reproducibly and serves app endpoints as non-root.
