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