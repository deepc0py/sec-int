
# EPIC-1 · Ticket 1.4 — Establish Initial CI/CD Pipeline for Linting and Testing

**Epic:** Project Foundation and DevOps  
**Type:** CI/CD  
**Priority:** High  
**Estimate:** 0.5–1 day  
**Owner:** Senior Software Engineer  
**Dependencies:** Ticket 1.1 (project scaffold)  
**References:** Master spec

## Summary
Add a CI pipeline that runs linting, formatting checks, static type checks, and unit tests on every push and pull request.

## Scope
- GitHub Actions workflow (or equivalent in your CI) to enforce project quality gates.
- Steps: checkout, setup Python, install deps via lockfile, run `ruff`, `mypy`, `pytest`.

## Tasks
- [ ] Create `.github/workflows/ci.yml`.
- [ ] Cache Poetry/pip and virtualenv to speed builds.
- [ ] Run `ruff check` and `ruff format --check`.
- [ ] Run `mypy` with strictness aligned to project defaults.
- [ ] Run tests with `pytest -q`.
- [ ] Fail build on any violations.

## Acceptance Criteria
- [ ] CI triggers on `push` and `pull_request` to main branches.
- [ ] Workflow installs using the lockfile for reproducibility.
- [ ] Lint, type check, and tests are executed and gate merges.
- [ ] CI status is visible on PRs.

## Technical Notes
**Example: `.github/workflows/ci.yml`**
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Poetry
        run: |
          pip install --upgrade pip
          pip install poetry
          poetry --version

      - name: Install dependencies
        run: |
          poetry install --no-interaction --no-ansi

      - name: Ruff (lint + format check)
        run: |
          poetry run ruff check .
          poetry run ruff format --check .

      - name: Type check (mypy)
        run: poetry run mypy .

      - name: Tests (pytest)
        run: poetry run pytest -q
```

## Out of Scope
- Build/publish artifacts and container images (future).
- Deployment workflows (future).

## Definition of Done
- CI runs automatically and blocks merges on failures.
- Team can see pass/fail status and logs from each step.
