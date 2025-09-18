
# EPIC-2 · Ticket 2.1 — Develop MITRE ATT&CK Data Ingestion Service

**Epic:** Knowledge Base Ingestion Pipeline  
**Type:** Feature  
**Priority:** High  
**Estimate:** 1–2 days  
**Owner:** Data Engineer / Senior SWE  
**Dependencies:** EPIC-1 Tickets 1.1 (project), 1.2 (DB), 1.3 (config)  
**References:** Master spec (“Actionable Development Plan: Vulnerability Analysis RAG Bot”)

## Summary
Create `ingest_mitre.py` that programmatically fetches the latest MITRE ATT&CK **Enterprise** matrix data (STIX 2.x) using `mitreattack-python`, extracts technique and sub-technique records, and outputs normalized objects ready for chunking and embedding.

## Background
MITRE ATT&CK is distributed in STIX; `mitreattack-python` abstracts STIX queries and provides helpers to remove deprecated/revoked items. We ingest **attack-pattern** objects for techniques & sub-techniques (e.g., `T1059`, `T1059.006`).

## Scope
- Script: `src/app/ingestion/ingest_mitre.py`
- Pull latest Enterprise ATT&CK dataset (local cache or TAXII as supported by lib).
- Extract: ATT&CK ID, name, description, URLs; filter revoked/deprecated.
- Normalize to a Python dataclass or dict payload with fields:
  - `source="mitre" | id | title | description | url | stix_id`
- Emit as a list for downstream chunking; optionally write JSONL to `data/raw/mitre.jsonl` for debugging.

## Tasks
- [ ] Add module scaffold `src/app/ingestion/ingest_mitre.py`.
- [ ] Initialize `MitreAttackData` and load Enterprise dataset.
- [ ] Retrieve `attack-pattern` objects; apply `remove_revoked_deprecated`.
- [ ] For each object: derive external ATT&CK ID (e.g., from `external_references`), name, description, reference URL.
- [ ] Normalize to list[dict] with required fields.
- [ ] Save debug artifact to `data/raw/mitre.jsonl` (optional but helpful).
- [ ] Unit tests: sample subset fixture; validate extraction, filtering, and fields present.
- [ ] Logging (INFO) for counts: total, removed, final.
- [ ] Add README notes under `docs/ingestion.md` (MITRE section).

## Acceptance Criteria
- [ ] Running `poetry run python -m app.ingestion.ingest_mitre --dry-run` prints a count summary and writes optional JSONL when enabled.
- [ ] Revoked/deprecated entries are excluded.
- [ ] Each record includes: `id` (e.g., `T1059` or `T1059.006`), `title`, `description` (non-empty), `url` (if present), `source="mitre"`.
- [ ] Tests cover extraction and filtering (>=80% line coverage for module).

## Technical Notes
**Suggested structure**
```python
# src/app/ingestion/ingest_mitre.py
from dataclasses import dataclass, asdict
from mitreattack.navlayers.core.attackToExcel import AttackToExcel  # optional
from mitreattack.attackToExcel.stixToAttack import MitreAttackData
from mitreattack.attackToExcel.stixToAttack import remove_revoked_deprecated

@dataclass
class MitreRecord:
    source: str = "mitre"
    id: str = ""
    title: str = ""
    description: str = ""
    url: str | None = None
    stix_id: str = ""

def load_enterprise_objects() -> list[dict]:
    mad = MitreAttackData("enterprise-attack.json")  # or provided helper to fetch
    objs = mad.get_attack_patterns()
    objs = remove_revoked_deprecated(objs)
    out: list[MitreRecord] = []
    for o in objs:
        # external_references → ATT&CK ID + URL
        ext = next((r for r in o.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)
        attck_id = ext.get("external_id") if ext else None
        url = ext.get("url") if ext else None
        if not attck_id: 
            continue
        out.append(MitreRecord(
            id=attck_id,
            title=o.get("name","").strip(),
            description=o.get("description","").strip(),
            url=url,
            stix_id=o.get("id","")
        ))
    return [asdict(i) for i in out]
```

- Prefer a small CLI interface (`--dry-run`, `--output data/raw/mitre.jsonl`).
- Ensure unicode/newlines preserved in descriptions.
- Keep **only Enterprise** scope for MVP.

## Out of Scope
- Ingest Mobile/ICS matrices.
- Mapping to CAPEC/CWE (future epic).

## Definition of Done
- Script merged with tests and basic docs.
- Produces validated records suitable for chunking (Ticket 2.3).
