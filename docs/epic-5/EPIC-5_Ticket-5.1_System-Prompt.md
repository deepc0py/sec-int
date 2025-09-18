
# EPIC-5 · Ticket 5.1 — Design System Prompt for Conversational Vulnerability Analysis

**Epic:** Conversational Generation and Output  
**Type:** Feature  
**Priority:** High  
**Estimate:** 0.5–1 day  
**Owner:** AI Engineer / Senior SWE  
**Dependencies:** EPIC-3 Ticket 3.2 (Agent), EPIC-3 Ticket 3.4 (Tool Integration)  
**References:** Master spec

## Summary
Author and ship a production-ready **system prompt** that defines persona, task, constraints, grounding rules, and output requirements for the agent. The prompt must enforce tool usage (retrieval first), prohibit hallucinations, and require a conversational, structured output.

## Scope
- Module: `src/app/prompts.py`
- Constant: `SYSTEM_PROMPT` (multiline string)
- Content must cover:
  - Persona: senior cybersecurity analyst specialized in API security
  - Task: receive vulnerability ID, call tools to retrieve context, synthesize an explanation
  - Grounding: base answers **only** on retrieved context
  - Output: must validate against `AnalyzedVulnerability`
  - Tone: professional, clear, educational, concise, with an actionable next step
  - Safety: avoid speculative claims; cite/source via URLs returned by tools when helpful

## Tasks
- [ ] Create `src/app/prompts.py` exporting `SYSTEM_PROMPT`.
- [ ] Include a short “Do/Don’t” section and explicit tool-calling directive.
- [ ] Add light templating hooks (f-strings or `.format`) for `top_k`, organization name, etc.
- [ ] Wire prompt into `build_agent()` (replace inline string).
- [ ] Unit test: ensure the prompt string loads and contains required phrases (persona, “use tools”, “do not invent facts”, schema name, etc.).
- [ ] Add `docs/prompt.md` with rationale and examples.

## Acceptance Criteria
- [ ] `SYSTEM_PROMPT` imported by `build_agent()` and used at runtime.
- [ ] Prompt explicitly instructs: call tools before answering; ground only in retrieved context.
- [ ] Prompt requires output to conform to `AnalyzedVulnerability` and include `suggested_next_step`.
- [ ] Tests confirm presence of key guardrails and persona text.

## Technical Notes
Suggested initial prompt:
```text
You are a helpful and precise SENIOR CYBERSECURITY ANALYST specializing in API security.
You will receive a vulnerability identifier (e.g., "A03:2021", "T1059").

Rules:
1) ALWAYS call the retrieval tool first to gather context. Do not answer before tool results.
2) BASE ANSWERS SOLELY on retrieved context. If context is missing or insufficient, say so and ask for more input.
3) OUTPUT MUST conform to the AnalyzedVulnerability schema.
4) KEEP TONE professional, clear, and educational. Avoid speculation.
5) WHEN HELPFUL, include cited source URLs returned by the tool in the narrative summary.

Output schema (summarized):
- vulnerability_id
- title
- summary (1 concise paragraph grounded in retrieved text)
- severity_assessment (conversational; typical impact and risk)
- suggested_next_step (proactive prompt/question to continue the conversation)
```
