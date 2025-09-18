# Actionable Development Plan: Minimum Viable Product for a Vulnerability Analysis RAG Bot

## Epic 5: Conversational Generation and Output

This epic focuses on the final, user-facing stage of the RAG pipeline. Here, the retrieved and synthesized information is transformed into a clear, structured, and conversational output. This involves crafting the guiding instructions for the LLM (the system prompt) and defining the precise format of its response using Pydantic models.

### User Story 5.1: Design System Prompt for Conversational Vulnerability Analysis

**User Story:**
As an AI engineer, I need to craft a detailed and effective system prompt for the Pydantic AI agent that defines its persona, task, constraints, and desired output format.

**Acceptance Criteria:**
- A system prompt is written as a multi-line string constant.
- The prompt establishes a clear persona for the agent (e.g., "You are a helpful and precise senior cybersecurity analyst specializing in API security.").
- It clearly defines the agent's primary task: to receive a vulnerability ID, use its tools to retrieve context, and then explain the vulnerability to the user.
- It instructs the agent on the desired tone: professional, clear, and educational.
- It explicitly instructs the agent to always use the provided tools to gather information before answering and to base its response solely on the retrieved context.
- The prompt is passed to the pydantic_ai.Agent constructor via the system_prompt argument.

**Technical Implementation Notes:**
The system prompt is one of the most critical levers for controlling an LLM's behavior. A well-crafted prompt is essential for ensuring the agent's responses are consistent, accurate, and aligned with the application's purpose. The prompt should be structured to guide the LLM's reasoning process. For this RAG application, it is vital to include instructions that prevent the model from "hallucinating" or relying on its internal, pre-trained knowledge. The prompt must force the agent to ground its analysis in the information retrieved by the retrieve_context tool. This is a key principle of building reliable RAG systems. The Pydantic AI framework is designed around the central role of the system prompt in defining an agent's behavior.1

### User Story 5.2: Define Pydantic Model for Structured Conversational Output

**User Story:**
As a developer, I need to ensure the agent's output is not just informative but also conversational and proactive by defining a Pydantic model that structures the conversation itself.

**Acceptance Criteria:**
- The AnalyzedVulnerability Pydantic model (from Epic 3) is finalized.
- The model includes standard fields like vulnerability_id, title, and summary.
- Crucially, the model includes a field named suggested_next_step of type str.
- The field's description instructs the LLM to generate a question or statement that encourages further user interaction (e.g., "Would you like to see common mitigation strategies for this vulnerability?").
- This model is confirmed as the result_type for the core Pydantic AI agent.

**Technical Implementation Notes:**
This user story implements a key design choice for fulfilling the user's requirement that the bot must "start a conversation." Instead of relying on prompt engineering alone to encourage this behavior, we can enforce it through the output schema. By making suggested_next_step a required field in the AnalyzedVulnerability model, we compel the LLM to generate this conversational element in every response.

Pydantic AI will not consider an agent run successful until the LLM's output can be successfully parsed and validated against this model.23 This means the model must generate content for the suggested_next_step field. This technique transforms the output from a static, one-way report into the first turn of a dynamic, interactive dialogue. It reliably makes the bot proactive, directly addressing a core requirement of the project in a structured and testable manner.

### User Story 5.3: Implement Logic to Consolidate Agent Findings into a Coherent Summary

**User Story:**
As a developer, I need to create a final processing step that takes the list of individual AnalyzedVulnerability objects from the orchestrator and formats them into a single, coherent, human-readable report.

**Acceptance Criteria:**
- A function format_final_report is implemented.
- The function takes a list of AnalyzedVulnerability objects as input.
- It generates a high-level summary at the beginning of the report (e.g., "API scan analysis complete. Found and analyzed 3 unique vulnerabilities.").
- It then iterates through each analyzed vulnerability, formatting its details (ID, title, summary, severity) in a clear and organized way (e.g., using Markdown formatting).
- The final output is a single string ready to be returned to the user or displayed in a UI.

**Technical Implementation Notes:**
This is the final assembly step. The orchestrator has done the heavy lifting of analyzing each finding individually. This module's responsibility is presentation. It should create a report that is easy to read and navigate. Using Markdown for formatting is a good choice as it is lightweight and can be easily rendered in many different frontends (e.g., a web UI, a Slack message, or a terminal). The structure should be hierarchical: a brief executive summary, followed by detailed sections for each finding. This ensures the user can quickly grasp the overall picture and then dive into the specifics of each vulnerability.

---