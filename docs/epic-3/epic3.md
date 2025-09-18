# Actionable Development Plan: Minimum Viable Product for a Vulnerability Analysis RAG Bot

## Epic 3: Core Agent and Retrieval Logic

This epic focuses on the construction of the Pydantic AI agent, which serves as the central orchestrator of the RAG process. The tickets here cover the definition of the data structures that govern the application's logic, the instantiation of the agent itself, and the creation of the tools that empower the agent to interact with its knowledge base.

### User Story 3.1: Define Pydantic Models for Vulnerability Data

**User Story:**
As a developer, I need to define a set of Pydantic BaseModel classes to represent the core data structures of the application, ensuring type safety and providing a clear data contract for inputs, internal states, and outputs.

**Acceptance Criteria:**
- A new Python module (models.py) is created to house all Pydantic models.
- A VulnerabilityFinding model is defined to represent a single parsed finding from a scan report.
- A RetrievedContext model is defined to structure the data retrieved from the vector store for a single finding.
- An AnalyzedVulnerability model is created to define the final, structured output of the agent's analysis for one vulnerability.
- All models use appropriate Python type hints (e.g., str, int, List, Optional).
- Field descriptions are added to the models where appropriate to serve as documentation and to provide context to the LLM.

**Technical Implementation Notes:**
The use of Pydantic models is a cornerstone of this application's architecture. It brings the discipline of static typing and data validation, which is a core tenet of the Pydantic AI framework, inspired by FastAPI's success.1 By defining these models upfront, we create a self-documenting "data contract" that clarifies how information flows through the system.

This approach offers a significant advantage in reliability. When a Pydantic model is designated as the result_type for a Pydantic AI agent, the framework will automatically ensure that the LLM's output conforms to that schema. If the LLM produces a malformed or incomplete response, Pydantic will raise a validation error, which can be caught and handled gracefully, preventing invalid data from propagating through the application.23 This moves a whole class of potential runtime errors into a managed validation step, which is crucial for building a production-grade system.

**Model NameField NameField TypeDescription**
VulnerabilityFindingidstrThe unique identifier for the vulnerability (e.g., 'A01:2021', 'T1059').sourcestrThe source of the identifier ('owasp' or 'mitre').
RetrievedContextfindingVulnerabilityFindingThe original finding that this context relates to.retrieved_chunksList[str]A list of the top-k text chunks retrieved from the vector database.source_urlsList[str]A list of unique source URLs associated with the retrieved chunks.
AnalyzedVulnerabilityvulnerability_idstrThe identifier off the vulnerability being analyzed.titlestrThe official name or title of the vulnerability.summarystrA concise, one-paragraph summary of what the vulnerability is.severity_assessmentstrA qualitative assessment of the typical severity and impact of this vulnerability, written in a conversational tone.suggested_next_stepstrA proactive, conversational prompt suggesting a logical next step for the user, such as asking for mitigation advice or examples.

### User Story 3.2: Implement Core Pydantic AI Agent

**User Story:**
As a developer, I need to implement the main Pydantic AI agent, configuring it with the chosen LLM, dependency types for database access, and the desired structured result type.

**Acceptance Criteria:**
- A module (agent.py) is created to define and instantiate the agent.
- A dataclass named AgentDependencies is created to define the dependencies required by the agent's tools (initially, an asyncpg.Pool for the database connection).
- The pydantic_ai.Agent is instantiated.
- The agent is configured with an LLM provider and model (e.g., 'openai:gpt-4o').
- The deps_type parameter of the agent is set to AgentDependencies.
- The result_type parameter is set to the AnalyzedVulnerability Pydantic model.

**Technical Implementation Notes:**
The Agent class is the central component of the Pydantic AI framework.25 Its instantiation brings together the model, the tools, and the data structures. The dependency injection system is a key feature that allows for clean, testable code.11 By defining an AgentDependencies dataclass, we provide a type-safe container for any external resources the agent needs, such as database connections or API clients.26 This dataclass is passed to the agent's constructor via the deps_type argument. Later, when the agent's tools are executed, they will receive a RunContext object from which they can access these dependencies in a type-safe manner (ctx.deps.pool).2 This pattern decouples the agent's logic from the specific implementation of its dependencies.

### User Story 3.3: Develop Knowledge Base Retrieval Tool

**User Story:**
As a developer, I need to create an asynchronous Python function that can perform a vector similarity search against the pgvector database to retrieve relevant knowledge base chunks for a given vulnerability ID.

**Acceptance Criteria:**
- An async function, retrieve_context, is implemented.
- The function accepts a RunContext and a query: str (the vulnerability ID) as arguments.
- The function uses the OpenAI client to generate an embedding for the input query.
- It uses the asyncpg connection pool from the RunContext (ctx.deps.pool) to execute a SQL query against the vulnerability_knowledge table.
- The SQL query uses the cosine distance operator (<->) to find the top 5 most similar chunks to the query embedding.
- The function aggregates the content of the retrieved rows into a single formatted string.
- The function returns a RetrievedContext object containing the original finding and the aggregated text.

**Technical Implementation Notes:**
This function is the heart of the "Retrieval" part of the RAG pipeline. The implementation will closely follow the pattern demonstrated in the official Pydantic AI RAG tutorial.3 The process is as follows: first, the incoming query string (e.g., "T1059") is converted into a vector using the same embedding model that was used during ingestion. This ensures that both the stored vectors and the query vector exist in the same dimensional space.

Next, a SQL query is executed against the pgvector database. The core of this query is the ORDER BY embedding <-> $1 clause, where $1 is the query vector. This clause calculates the cosine distance between the query vector and every stored vector in the table and orders the results by similarity.3 The LIMIT 5 clause restricts the result to the top 5 most relevant chunks. The function then formats these chunks into a single string to be passed to the LLM.

### User Story 3.4: Integrate Retrieval Tool with the Pydantic AI Agent

**User Story:**
As a developer, I need to register the retrieve_context function as a tool on the Pydantic AI agent so that the LLM can invoke it to gather information during its reasoning process.

**Acceptance Criteria:**
- The retrieve_context function is decorated with the @agent.tool decorator.
- The function's docstring is updated to clearly and concisely describe its purpose, arguments, and what it returns.
- The function's type hints are correct and specific.

**Technical Implementation Notes:**
Pydantic AI uses a powerful function-calling mechanism to allow the LLM to interact with external systems. The @agent.tool decorator is the primary way to enable this.2 When the agent is initialized, Pydantic AI inspects all functions registered with this decorator. It uses the function's name, its docstring, and the type annotations of its parameters to automatically generate a JSON schema.

This schema is then provided to the LLM as part of its instructions. When the agent is run with a user prompt, the LLM can decide if it needs to call one of the available tools to answer the question. If it does, it will generate a response containing the tool's name and the arguments it wants to pass. Pydantic AI intercepts this response, calls the corresponding Python function with the provided arguments (validating them against the type hints), and then sends the function's return value back to the LLM as additional context. This entire back-and-forth process allows the agent to augment its knowledge with real-time data from the vector store.

---