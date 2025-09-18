# Actionable Development Plan: Minimum Viable Product for a Vulnerability Analysis RAG Bot

## Introduction: Building the Vulnerability Analysis RAG Bot

This document outlines a complete and actionable set of software development tickets for the creation of a Minimum Viable Product (MVP). The project's central goal is to engineer a specialized AI bot, built on the Pydantic AI framework, designed to transform raw API vulnerability scan reports into actionable, conversational intelligence. The primary audience for this tool includes security teams, DevOps engineers, and developers who require immediate, context-rich analysis of security findings.

The core problem this MVP addresses is the inherent complexity and opacity of typical security scan outputs. These reports are often dense, filled with cryptic identifiers, and lack the necessary context for teams to quickly assess risk and prioritize remediation. This bot will bridge the gap between raw data and human understanding by automating the laborious research and initial analysis process that follows a security scan.

The system is architected as a classic Retrieval-Augmented Generation (RAG) pipeline, which can be broken down into three distinct phases:

### Ingestion
This phase involves the systematic sourcing, parsing, and processing of knowledge from authoritative cybersecurity sources, specifically the OWASP Top 10 and the MITRE ATT&CK framework. This textual data is segmented into meaningful chunks, converted into numerical vector embeddings, and stored in a specialized vector database. This process creates the foundational knowledge base, or "brain," of the system.

### Retrieval
When the system receives a vulnerability finding from a scan report (e.g., an identifier like A03:2021 or T1059), it queries the vector database. The objective is to retrieve the most relevant and detailed explanatory text associated with that specific vulnerability, providing the necessary context for analysis.

### Generation
In the final phase, a Pydantic AI agent synthesizes the original finding with the retrieved contextual information. It then leverages a Large Language Model (LLM) to generate a structured, conversational explanation of the vulnerability, including an assessment of its severity and potential impact.

The technology stack for this MVP is centered on a set of robust and modern tools. The core logic will be implemented using Pydantic AI, a framework designed for building production-grade AI applications with a strong emphasis on type safety and structured data handling.1 The vector store will be a PostgreSQL database enhanced with the pgvector extension, a solution recommended in Pydantic AI's own RAG tutorials.3 Generation and embedding tasks will be handled by a state-of-the-art model from OpenAI, such as gpt-4o.3 Finally, a lightweight API layer will be built using FastAPI, which integrates seamlessly with the Pydantic ecosystem, to provide an entry point for the application.3

---

## Epic 1: Project Foundation and DevOps

This initial epic establishes the foundational infrastructure and development practices for the project. The tickets within this epic are designed to create a stable, reproducible, and scalable environment, ensuring that the development process is efficient and adheres to high-quality standards from the outset. This includes defining project dependencies, containerizing the database, managing configuration securely, and establishing an automated continuous integration pipeline.

### User Story 1.1: Setup Python Project with Dependency Management

**User Story:**
As a developer, I need a new Python project initialized with a modern dependency management tool so that all dependencies are explicitly defined, version-locked, and easily installable across different development environments.

**Acceptance Criteria:**
- A new project structure is created.
- The project is configured to use Poetry or a similar tool (e.g., PDM).
- A pyproject.toml file is present and defines the project's metadata, dependencies, and development dependencies.
- The Python version is constrained to >=3.12 as required by pydantic-ai.6
- A developer can set up the environment by running a single command (e.g., poetry install).
- A README.md file is created with initial setup instructions.

**Technical Implementation Notes:**
The choice of a modern dependency manager like Poetry is crucial for creating a reproducible build. It solves the classic problem of managing dependencies and virtual environments in a unified way. The pyproject.toml file will serve as the single source of truth for all project requirements.

The initial set of dependencies will be carefully selected based on the project's architecture. To keep the production environment lean, the pydantic-ai-slim package will be used with the openai extra, which installs only the necessary components for interacting with OpenAI models.5 For the asynchronous database connection to PostgreSQL, the asyncpg library is required, as demonstrated in the official RAG examples.4 The ingestion pipeline will necessitate a robust Markdown parser; markdown-it-py is a strong candidate due to its compliance with the CommonMark specification and its extensible plugin architecture.8

Development dependencies will include tools to enforce code quality, such as pytest for testing, ruff for high-performance linting and formatting, and mypy for static type checking. The strong emphasis on type safety in Pydantic AI's design philosophy, which aims to move runtime errors to development time, is best supported by integrating static analysis directly into the development workflow.10

**CategoryLibrary/ToolVersionPurpose**
Corepython^3.12 Base runtime environment, meeting the minimum requirement for Pydantic AI.6pydantic-ai-slim^1.0The core GenAI agent framework. The slim version is used to minimize dependency footprint.7openai^1.0Required for Pydantic AI's OpenAI model provider and for direct calls to the embedding API.4fastapi^0.111A modern web framework for creating the API endpoint, chosen for its tight integration with Pydantic.3uvicorn^0.29ASGI server to run the FastAPI application.Databaseasyncpg^0.29High-performance asynchronous PostgreSQL client library, required for interacting with pgvector.4psycopg2-binary^2.9Standard synchronous PostgreSQL adapter, often useful for scripting or simple database operations.Data Ingestionmitreattack-python^2.0Official MITRE library for programmatically accessing and parsing ATT&CK STIX data.12markdown-it-py^3.0A versatile and CommonMark-compliant Markdown parser for ingesting OWASP documentation from its source repositories.8Utilitiespydantic-settings^2.2For managing application configuration and secrets via environment variables, leveraging Pydantic's validation capabilities.Dev Toolspytest^8.2The standard framework for writing and running tests in Python.ruff^0.4An extremely fast Python linter and code formatter, used to enforce a consistent code style and catch common errors.mypy^1.10A static type checker for Python, essential for leveraging Pydantic AI's type-safe design and catching type-related bugs early.10

### User Story 1.2: Configure Vector Database (PostgreSQL + pgvector) via Docker

**User Story:**
As a developer, I need a containerized PostgreSQL database with the pgvector extension, managed by Docker Compose, so that I can spin up a consistent and isolated database environment with a single command.

**Acceptance Criteria:**
- A docker-compose.yml file is created in the project root.
- The file defines a PostgreSQL service using an official pgvector image (e.g., pgvector/pgvector:pg17).
- The service is configured with a persistent volume to ensure data is not lost on restart.
- Environment variables are used to set the PostgreSQL user, password, and database name.
- The database is exposed on a non-standard host port (e.g., 54320) to prevent conflicts with other local PostgreSQL instances.
- A developer can start the entire database stack by running docker-compose up.

**Technical Implementation Notes:**
Using Docker Compose is a standard practice for managing multi-service local development environments. It encapsulates the service configuration, making the setup process trivial for any developer joining the project. The Pydantic AI RAG tutorials provide a direct docker run command that serves as a perfect template for the docker-compose.yml service definition.3

A key best practice, also highlighted in the documentation, is to map the container's standard PostgreSQL port (5432) to a non-standard host port like 54320.4 This small detail prevents a common source of frustration in development environments where multiple projects might require a PostgreSQL instance. The use of a named volume (-v \pwd`/postgres-data:/var/lib/postgresql/data`) ensures that the vector database persists across container restarts, which is essential for an efficient development loop, as the data ingestion and embedding process can be time-consuming and costly.4

### User Story 1.3: Implement Centralized Configuration and Secrets Management

**User Story:**
As a developer, I need a centralized and secure way to manage application configuration and secrets, such as API keys and database connection strings, so that the application is portable and sensitive data is not hard-coded in the source code.

**Acceptance Criteria:**
- The pydantic-settings library is added as a project dependency.
- A configuration module (e.g., config.py) is created, defining a Settings class that inherits from BaseSettings.
- All configuration variables (e.g., DATABASE_URL, OPENAI_API_KEY, LLM_MODEL_NAME) are defined as fields in the Settings class.
- The application loads its configuration from environment variables.
- A .env.example file is created in the project root, documenting all required environment variables and providing placeholder values.
- The .env file is added to .gitignore to prevent accidental commits of secrets.

**Technical Implementation Notes:**
Hard-coding configuration values and secrets is a significant security risk and makes the application difficult to deploy in different environments (development, staging, production). The Pydantic AI examples consistently demonstrate the use of environment variables for secrets like OPENAI_API_KEY.5

By using pydantic-settings, this practice is formalized. This library uses a Pydantic model to define, validate, and load configuration. This provides two key benefits: first, it offers a single, type-safe object for accessing configuration throughout the application; second, it will raise a validation error on startup if a required environment variable is missing, leading to a fail-fast behavior that prevents runtime errors later on.

---

## Epic 2: Knowledge Base Ingestion Pipeline

This epic is dedicated to building the data pipelines that will source, process, and store the information forming the core of the RAG system's knowledge base. This is a multi-step process that involves fetching data from disparate sources (MITRE and OWASP), applying a sophisticated chunking strategy to prepare the text for embedding, and finally populating the vector database. The quality and structure of the data ingested here will directly determine the performance and accuracy of the final application.

### User Story 2.1: Develop MITRE ATT&CK Data Ingestion Service

**User Story:**
As a data engineer, I need to create a service that programmatically fetches the latest MITRE ATT&CK Enterprise matrix data, parses it, and extracts key information for each technique and sub-technique.

**Acceptance Criteria:**
- A Python script (ingest_mitre.py) is created for this purpose.
- The script uses the mitreattack-python library to access the ATT&CK data.
- The script fetches the complete Enterprise ATT&CK dataset, which is provided in STIX 2.x format.15
- For each technique and sub-technique, the script extracts the ATT&CK ID (e.g., 'T1059', 'T1059.006'), name, and full description.
- The extracted data is structured into a list of objects, each representing a single vulnerability, ready for the next stage of processing.
- The script includes logic to filter out any revoked or deprecated objects to ensure the knowledge base is current.13

**Technical Implementation Notes:**
The MITRE Corporation provides the ATT&CK knowledge base in a machine-readable STIX format, which is a standardized JSON-based language for cyber threat intelligence.15 The official mitreattack-python library is the ideal tool for this task, as it abstracts away the complexities of the STIX format and provides a high-level API for querying the data.12

The implementation will involve initializing the MitreAttackData class with the source data (which can be downloaded locally or accessed via a TAXII server). The script will then iterate through all objects of type attack-pattern (the STIX representation for techniques).13 For each object, it will extract relevant fields like external_references (to get the ATT&CK ID), name, and description. The remove_revoked_deprecated utility function from the library will be used to ensure data quality.13

### User Story 2.2: Develop OWASP Top 10 Data Ingestion Service

**User Story:**
As a data engineer, I need a service to ingest the content of the OWASP Top 10 2021 report by parsing the official documentation from its source.

**Acceptance Criteria:**
- A Python script (ingest_owasp.py) is created.
- The script identifies and fetches the source Markdown files for the OWASP Top 10 2021 from the official OWASP GitHub repository.17
- The script uses a Markdown parsing library (e.g., markdown-it-py) to parse the content.
- The parser correctly identifies the sections corresponding to each of the ten vulnerabilities (e.g., A01:2021-Broken Access Control).
- For each vulnerability, the script extracts its identifier, title, and the full descriptive text.
- The extracted data is structured into a list of objects, similar to the output of the MITRE ingestion service.

**Technical Implementation Notes:**
Unlike the structured data from MITRE, the OWASP Top 10 documentation is primarily available as web pages and Markdown files.17 The most reliable source for parsing is the official GitHub repository, which contains the content in Markdown format.

The markdown-it-py library can parse the Markdown into a token stream, allowing the script to programmatically identify document structure.8 The script will look for specific heading patterns (e.g., ## A01:2021 Broken Access Control) to delineate the content for each vulnerability. Once a section is identified, all subsequent text until the next major heading will be aggregated as the description for that vulnerability. This approach is more robust than simple web scraping, as it is less susceptible to changes in website layout.

### User Story 2.3: Implement Text Chunking Strategy for Technical Documents

**User Story:**
As a data engineer, I need a centralized text chunking module that can take the raw text content for each vulnerability and split it into smaller, semantically coherent chunks suitable for vector embedding.

**Acceptance Criteria:**
- A new Python module (chunking.py) is created.
- The module implements a recursive, structure-aware chunking strategy.
- The chunking function takes the text of a single vulnerability as input.
- It splits the text based on a prioritized list of separators (e.g., paragraph breaks \n\n, section headers, sentence breaks .).
- The function aims to create chunks of a target size (e.g., 256-512 tokens) but will not break sentences or paragraphs unless necessary.
- Each generated chunk is associated with the metadata of its parent vulnerability (ID, title, source).

**Technical Implementation Notes:**
The effectiveness of a RAG system is highly dependent on its chunking strategy. For dense, technical documentation like that of OWASP and MITRE, a naive fixed-size chunking approach is inadequate because it frequently splits sentences and separates related concepts, which degrades retrieval accuracy.19

The implementation will therefore focus on a more sophisticated, content-aware method. The core logic should treat each individual vulnerability (e.g., the full text for MITRE ATT&CK technique T1059) as a single "document." This reframes the problem from splitting a massive corpus to logically segmenting the information for a single, focused topic. This approach ensures that all retrieved chunks for a given query are guaranteed to be about the correct vulnerability, dramatically improving the signal-to-noise ratio of the retrieval step.

A recursive splitting strategy, which attempts to split on the largest semantic boundaries first (like paragraphs) before moving to smaller ones (sentences), is the best fit.21 This preserves as much semantic context as possible within each chunk. An overlap between chunks (e.g., 50 tokens) can also be implemented to ensure that context is not lost at the boundaries of chunks.21

### User Story 2.4: Implement Embedding and Vector Store Population Logic

**User Story:**
As a data engineer, I need a script that takes the processed and chunked vulnerability data, generates vector embeddings for each chunk, and populates the pgvector database with this information.

**Acceptance Criteria:**
- A script (populate_db.py) is created to orchestrate the embedding and database insertion process.
- The script establishes an asynchronous connection to the PostgreSQL database using asyncpg.
- It first executes a DDL statement to create the vulnerability_knowledge table if it does not already exist.
- For each text chunk, the script calls the OpenAI embeddings API (using a model like text-embedding-3-small) to generate a vector embedding.4
- The script then executes an INSERT statement to store the chunk's content, its vector embedding, and all associated metadata (source, vulnerability ID, title, URL) into the database.
- The script should be idempotent, meaning it can be run multiple times without creating duplicate entries. This can be achieved by checking for existing entries based on content or a unique identifier.

**Technical Implementation Notes:**
This script ties the entire ingestion pipeline together. The schema for the vector database table is a critical design decision. Storing rich metadata alongside the vector embedding is essential for both current functionality and future extensibility. For instance, including the source ('owasp' or 'mitre') and vulnerability_id allows the retrieval system to not only find relevant content but also to cite its origins and provide users with a direct link to the source material for verification. This builds trust and transforms the bot from an opaque oracle into a transparent research assistant. The Pydantic AI RAG examples provide a solid foundation for the required SQL schema and the asyncpg interaction patterns.3

**Column NameData TypeConstraintsDescription**
idSERIALPRIMARY KEYA unique, auto-incrementing identifier for each chunk.
contentTEXTNOT NULLThe raw text of the document chunk.
embeddingVECTOR(1536)NOT NULLThe numerical vector representation of the content, generated by the embedding model. The dimension (1536) must match the output of the chosen model (e.g., OpenAI's text-embedding-3-small).4
sourceVARCHAR(10)NOT NULLThe origin of the knowledge, either 'owasp' or 'mitre'. This allows for filtering and source attribution.
vulnerability_idVARCHAR(20)NOT NULLThe specific identifier of the vulnerability this chunk belongs to (e.g., 'A01:2021' or 'T1059.006'). This is the primary key for grouping all chunks related to a single vulnerability.
titleTEXTNOT NULLThe title or name of the parent vulnerability (e.g., "Broken Access Control" or "Python"). This provides human-readable context.
urlTEXTAn optional URL pointing to the source document for the vulnerability, enabling direct user verification.

---

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

## Epic 6: MVP Application and Deployment

This final epic focuses on packaging the entire system into a deployable, testable application. It involves creating an API endpoint to expose the bot's functionality, containerizing the application for portability, and implementing an end-to-end test suite to ensure all components work together correctly.

### User Story 6.1: Develop a Basic API Endpoint (e.g., FastAPI) to Trigger the Bot

**User Story:**
As a developer, I need to create a simple web server with a single API endpoint that can receive a vulnerability scan report, trigger the analysis, and return the final summary.

**Acceptance Criteria:**
- A main.py file is created to house the FastAPI application.
- A single POST endpoint (e.g., /analyze) is defined.
- The endpoint accepts a JSON payload containing the raw scan report text.
- When called, the endpoint invokes the analyze_scan_report orchestrator function.
- The endpoint returns the formatted final report as a JSON response with a 200 status code upon success.
- Appropriate error handling is implemented to return a non-200 status code if the analysis fails.

**Technical Implementation Notes:**
FastAPI is the natural choice for the web framework, given that Pydantic AI was heavily inspired by it and the two libraries share the same underlying Pydantic models for data validation.1 This creates a seamless development experience. The Pydantic AI RAG tutorial itself provides an example of using a FastAPI backend.3 The endpoint will use Pydantic to define the expected request body, automatically handling input validation and documentation generation.

### User Story 6.2: Containerize the Application for Deployment

**User Story:**
As a DevOps engineer, I need a Dockerfile to package the entire Python application and its dependencies into a standardized container image, so that it can be deployed consistently across different environments.

**Acceptance Criteria:**
- A Dockerfile is created in the project root.
- The Dockerfile uses a suitable Python base image (e.g., python:3.11-slim).
- It copies the project's source code and dependency files (pyproject.toml, poetry.lock) into the image.
- It installs the project dependencies using the lock file to ensure reproducible builds.
- It defines the command to run the application using uvicorn.
- The resulting image is optimized for size and security (e.g., by using a multi-stage build and running as a non-root user).

**Technical Implementation Notes:**
Containerization is the modern standard for deploying applications. A Dockerfile provides a reproducible recipe for building an image that contains the application, its runtime, and all its dependencies. This eliminates "works on my machine" problems and simplifies deployment to any container orchestration platform (like Docker Swarm, Kubernetes, or cloud services like AWS ECS or Google Cloud Run). A multi-stage build is a best practice where one stage is used to build the application and install dependencies, and a final, smaller stage copies only the necessary artifacts, resulting in a more secure and efficient production image.

### User Story 6.3: Implement End-to-End Integration Test Suite

**User Story:**
As a quality assurance engineer, I need an end-to-end integration test suite that validates the entire application workflow, from API request to the final generated response, to ensure all components are working together correctly.

**Acceptance Criteria:**
- A new test file (test_integration.py) is created.
- The test suite uses a test client (e.g., FastAPI.TestClient) to make live requests to the application's API endpoint.
- A small, static set of test data is created, including a sample scan report and a corresponding mock knowledge base.
- The tests mock the database connection and the OpenAI API calls to ensure tests are fast, deterministic, and do not incur costs.
- One test case sends a sample scan report to the /analyze endpoint and asserts that it receives a 200 OK response.
- Another test case validates the structure and content of the returned analysis, ensuring it matches the expected format defined by the Pydantic models.

**Technical Implementation Notes:**
While unit tests are essential for verifying individual components, integration tests are crucial for ensuring the entire system works as a cohesive whole. Pydantic AI's dependency injection system is specifically designed to facilitate testing. The documentation highlights the ability to override dependencies during testing.27

In our integration test, we can use the agent.override(deps=test_deps) context manager to inject a mock database connection. This allows the test to simulate the retrieval process without needing a running PostgreSQL instance. Similarly, the OpenAI API calls can be patched using a library like pytest-mock. This allows us to provide a canned response for the LLM generation step, making the test's outcome predictable and independent of the actual LLM's performance. This level of testability is a key feature of a well-architected, production-ready application.

---

## Conclusion: MVP Review and Future Roadmap

The completion of the tickets outlined in these six epics will result in a functional, containerized, and tested Minimum Viable Product. This MVP will deliver on the core promise of the project: an AI-powered RAG bot capable of ingesting an API vulnerability scan report, identifying OWASP Top 10 and MITRE ATT&CK findings, retrieving relevant context from a custom-built knowledge base, and generating a structured, conversational summary of the analysis. The use of Pydantic AI ensures a robust, type-safe foundation, while the architecture provides a clear path for future expansion.

Upon successful delivery of the MVP, the following enhancements represent a logical roadmap for future development:

### Knowledge Base Expansion
The current knowledge base is limited to two sources. It can be significantly enriched by ingesting data from other relevant cybersecurity frameworks, such as the Common Weakness Enumeration (CWE), Common Attack Pattern Enumeration and Classification (CAPEC), and vendor-specific security advisories. This would broaden the bot's analytical capabilities.

### Enhanced Conversational Abilities
The MVP's conversation is single-turn. Implementing conversational memory would allow the bot to understand context from previous interactions within the same session. A user could ask follow-up questions (e.g., "Show me code examples of that vulnerability") and receive contextually aware answers.

### Interactive Frontend and Integrations
While the MVP exposes an API, a more user-friendly interface would increase adoption. This could be a simple web-based chat application. The research indicates that frameworks like CopilotKit are designed to integrate with Pydantic AI's stateful nature to build such UIs.31 Furthermore, integrating the bot directly into developer workflows via platforms like Slack or Microsoft Teams would bring its capabilities directly to where users work.

### Advanced Observability and Evaluation
To move from an MVP to a production system, robust monitoring is essential. Pydantic AI offers tight integration with Pydantic Logfire, an OpenTelemetry platform for real-time debugging, performance monitoring, and cost tracking of LLM interactions.2 Implementing this would provide invaluable insights into the agent's behavior and operational costs. Additionally, using a framework like pydantic-evals would enable systematic testing and evaluation of the RAG system's performance over time.10
