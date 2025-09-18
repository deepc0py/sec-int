# Actionable Development Plan: Minimum Viable Product for a Vulnerability Analysis RAG Bot

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