
# EPIC-5 · Ticket 5.3 — Implement Logic to Consolidate Agent Findings into a Coherent Summary

**Epic:** Conversational Generation and Output  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1 day  
**Owner:** Senior SWE  
**Dependencies:** EPIC-4 Ticket 4.3 (Orchestrator), EPIC-3 (Agent + Models)  
**References:** Master spec

## Summary
Create `format_final_report` that converts a list of `AnalyzedVulnerability` objects into a single, human-readable **Markdown** report with an executive summary and sections for each finding.

## Scope
- Module: `src/app/reporting.py`
- Function: `def format_final_report(items: list[AnalyzedVulnerability]) -> str`
- Output:
  - Executive summary: count and short description
  - Per finding: `## {vulnerability_id} — {title}`; then bullets for summary & severity; include `suggested_next_step`
  - Optional: table of contents and source links if available (passed in summary text)

## Tasks
- [ ] Implement formatter; ensure safe Markdown escaping for user-provided text.
- [ ] Add TOC when `len(items) >= 3`.
- [ ] Include a timestamp header and environment (dev/stage/prod) from settings.
- [ ] CLI helper: `python -m app.reporting --in sample.json > report.md` (optional).
- [ ] Unit tests:
  - [ ] Empty list → “No findings” message.
  - [ ] Sample three items → verify headings, counts, and that Markdown compiles (basic regex checks).
  - [ ] Ensure no trailing whitespace; lines <= 120 chars preferred.

## Acceptance Criteria
- [ ] Output is valid Markdown and readable in GitHub/Docs.
- [ ] Report starts with an executive summary and a count of analyzed vulnerabilities.
- [ ] Each item section includes ID, title, summary, severity, and suggested next step.
- [ ] Tests pass with representative fixtures.

## Technical Notes
Function sketch:
```python
from datetime import datetime
from app.models import AnalyzedVulnerability
from app.config import settings

def format_final_report(items: list[AnalyzedVulnerability]) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if not items:
        return f"# API Scan Analysis\n\n_As of {ts}_\n\nNo vulnerabilities were identified in the provided report."

    lines: list[str] = []
    lines.append(f"# API Scan Analysis\n\n_As of {ts} — env: {settings.APP_ENV}_\n")
    lines.append(f"Found and analyzed **{len(items)}** unique vulnerabilities.\n")

    if len(items) >= 3:
        lines.append("## Table of Contents")
        for it in items:
            lines.append(f"- [{it.vulnerability_id} — {it.title}](#{it.vulnerability_id.lower().replace(':','').replace('.','')}-{it.title.lower().replace(' ','-')})")
        lines.append("")

    for it in items:
        anchor = f"{it.vulnerability_id} — {it.title}"
        lines.append(f"## {anchor}")
        lines.append("**Summary**")
        lines.append(it.summary.strip())
        lines.append("")
        lines.append("**Severity & Impact**")
        lines.append(it.severity_assessment.strip())
        lines.append("")
        lines.append("**Next Step**")
        lines.append(it.suggested_next_step.strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```
