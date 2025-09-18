# Actionable Development Plan: Minimum Viable Product for a Vulnerability Analysis RAG Bot

## Epic 4: Scan Result Processing and Orchestration

This epic covers the "front door" of the application: the components responsible for ingesting the raw API vulnerability scan report, parsing it to identify known vulnerability identifiers, and orchestrating the analysis workflow by feeding these identifiers to the core AI agent.

### User Story 4.1: Implement Scan Result Input Handler

**User Story:**
As a developer, I need a handler function that can accept raw API vulnerability scan data, likely in JSON or plain text format, and prepare it for processing.

**Acceptance Criteria:**
- A function handle_scan_input is created.
- The function accepts a raw string or a dictionary as input, representing the content of a scan report.
- It performs basic validation to ensure the input is not empty.
- It normalizes the input into a single string format for consistent parsing.
- The function returns the normalized string content.

**Technical Implementation Notes:**
This component serves as the initial entry point for data into the system. While the MVP will likely handle a simple text or JSON payload, this handler can be extended in the future to support various formats from different scanning tools (e.g., XML from ZAP, specific JSON schemas from commercial scanners). The primary responsibility here is to create a consistent, predictable input for the downstream parsing logic.

### User Story 4.2: Develop Parser for OWASP and MITRE ATT&CK Identifiers

**User Story:**
As a developer, I need a robust parsing module that can scan a given text and accurately extract all instances of OWASP Top 10 and MITRE ATT&CK identifiers.

**Acceptance Criteria:**
- A new module (parser.py) is created.
- The module contains a function extract_vulnerability_ids.
- The function uses regular expressions to find all matches for MITRE ATT&CK ID patterns (e.g., T\d{4} and T\d{4}\.\d{3}).
- The function uses regular expressions to find all matches for OWASP Top 10 ID patterns (e.g., A\d{1,2}:\d{4} and API\d{1,2}:\d{4}).
- The function returns a de-duplicated list of VulnerabilityFinding objects, correctly populating the id and source fields for each match.

**Technical Implementation Notes:**
The accuracy of this parser is critical to the entire system's effectiveness. If an identifier is missed, it will not be analyzed. The regular expressions must be crafted carefully to be specific enough to avoid false positives while being general enough to capture variations.

MITRE ATT&CK Regex: A suitable pattern would be r'\b(T\d{4}(?:\.\d{3})?)\b'. This pattern looks for a word boundary (\b), followed by the letter 'T', four digits (\d{4}), and an optional non-capturing group (?:\.\d{3})? for sub-techniques (a period followed by three digits). The final word boundary ensures that it doesn't match parts of other words. The format is well-defined in MITRE's documentation.29

OWASP Top 10 Regex: A suitable pattern would be r'\b(A(PI)?\d{1,2}:\d{4})\b'. This pattern looks for a word boundary, the letter 'A', an optional 'PI' for the API-specific list 30, one or two digits (\d{1,2}), a colon, and four digits for the year (\d{4}).

The function will use Python's re.findall to extract all matches and then process the results to populate the VulnerabilityFinding Pydantic model defined in Epic 3.

### User Story 4.3: Create Orchestration Logic to Map Findings to Agent Queries

**User Story:**
As a developer, I need to create the main orchestration logic that takes the list of parsed vulnerability findings, iterates through them, and invokes the Pydantic AI agent for each one to get a detailed analysis.

**Acceptance Criteria:**
- An orchestrator.py module is created with a main analyze_scan_report function.
- The function takes the raw scan report content as input.
- It first calls the extract_vulnerability_ids parser to get a list of findings.
- It then iterates asynchronously over the unique findings.
- For each finding, it calls agent.run() with a prompt constructed from the finding's ID.
- It collects the structured AnalyzedVulnerability object returned by each successful agent run.
- The function returns a list of all the analyzed vulnerability objects.

**Technical Implementation Notes:**
This orchestrator component is more than just a simple loop; it acts as the state manager for the entire analysis process. While a sequential iteration is sufficient for the MVP, this is where more complex logic would reside in a production system. The orchestrator is responsible for managing the lifecycle of the analysis. Pydantic AI agents are designed to be stateful, meaning they can preserve progress across runs.31 The orchestrator can leverage this by managing a session or context for the entire scan report.

Furthermore, it should handle potential failures. Pydantic AI has built-in support for retries on failed tool calls or validation errors.32 The orchestrator can be designed to catch exceptions from agent.run(), log the failure for a specific vulnerability ID, and continue processing the rest of the findings. This ensures that a single problematic finding does not halt the analysis of the entire report. This elevates the orchestrator from a simple script to a resilient piece of the application's core control flow.

---