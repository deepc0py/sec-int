"""Embedding and vector store population for vulnerability knowledge base.

This module generates embeddings for vulnerability chunks and stores them in
PostgreSQL with pgvector, providing the foundation for the RAG retrieval system.
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import asyncpg
import click
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings via OpenAI API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """Initialize the embedding service.

        Args:
            api_key: OpenAI API key
            model: Embedding model name (defaults to text-embedding-3-small)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_batch_size = 100  # OpenAI recommends max 100 texts per batch

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is list of floats)
        """
        if not texts:
            return []

        # Batch processing for large inputs
        all_embeddings = []

        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            logger.debug(f"Generating embeddings for batch {i//self.max_batch_size + 1}, size {len(batch)}")

            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )

                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch starting at {i}: {e}")
                raise

        return all_embeddings


class VectorStore:
    """PostgreSQL vector store with pgvector support."""

    def __init__(self, database_url: str):
        """Initialize the vector store.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool and create schema."""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self._create_schema()

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    async def _create_schema(self):
        """Create the vulnerability_knowledge table if it doesn't exist."""
        schema_sql = """
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS vulnerability_knowledge (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            embedding VECTOR(1536) NOT NULL,
            source VARCHAR(10) NOT NULL,
            vulnerability_id VARCHAR(20) NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            order_index INT NOT NULL DEFAULT 0,
            content_hash TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_source
            ON vulnerability_knowledge(source);
        CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_vuln
            ON vulnerability_knowledge(vulnerability_id);
        CREATE INDEX IF NOT EXISTS ix_vuln_knowledge_hash
            ON vulnerability_knowledge(content_hash);
        """

        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
            logger.info("Database schema initialized successfully")

    async def upsert_chunks(self, chunks: list[dict[str, Any]], embeddings: list[list[float]]):
        """Insert or update chunks with their embeddings.

        Args:
            chunks: List of chunk dictionaries with metadata
            embeddings: List of embedding vectors corresponding to chunks
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) != embeddings count ({len(embeddings)})")

        upsert_sql = """
        INSERT INTO vulnerability_knowledge (
            content, embedding, source, vulnerability_id, title, url, order_index, content_hash
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (content_hash) DO UPDATE SET
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            source = EXCLUDED.source,
            vulnerability_id = EXCLUDED.vulnerability_id,
            title = EXCLUDED.title,
            url = EXCLUDED.url,
            order_index = EXCLUDED.order_index
        """

        # Prepare batch data
        batch_data = []
        for chunk, embedding in zip(chunks, embeddings):
            content_hash = self._compute_content_hash(chunk)

            batch_data.append((
                chunk["content"],
                str(embedding),  # Convert embedding list to string for PostgreSQL vector type
                chunk["source"],
                chunk["vulnerability_id"],
                chunk["title"],
                chunk.get("url"),
                chunk["order_index"],
                content_hash
            ))

        # Execute batch insert
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(upsert_sql, batch_data)

        logger.info(f"Upserted {len(chunks)} chunks to vector store")

    async def truncate_table(self):
        """Remove all data from the vulnerability_knowledge table."""
        async with self.pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE vulnerability_knowledge")
            logger.info("Truncated vulnerability_knowledge table")

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the stored data."""
        stats_sql = """
        SELECT
            COUNT(*) as total_chunks,
            COUNT(DISTINCT source) as sources,
            COUNT(DISTINCT vulnerability_id) as vulnerabilities,
            AVG(LENGTH(content)) as avg_content_length
        FROM vulnerability_knowledge
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(stats_sql)

        return {
            "total_chunks": row["total_chunks"],
            "sources": row["sources"],
            "vulnerabilities": row["vulnerabilities"],
            "avg_content_length": round(row["avg_content_length"], 1) if row["avg_content_length"] else 0
        }

    async def test_similarity_search(self, query_text: str, embedding_service: EmbeddingService, limit: int = 3) -> list[dict[str, Any]]:
        """Test similarity search with a sample query.

        Args:
            query_text: Text to search for
            embedding_service: Service to generate query embedding
            limit: Number of results to return

        Returns:
            List of similar chunks with similarity scores
        """
        # Generate embedding for query
        query_embeddings = await embedding_service.embed_texts([query_text])
        query_embedding = query_embeddings[0]

        # Perform similarity search
        search_sql = """
        SELECT
            content,
            source,
            vulnerability_id,
            title,
            url,
            order_index,
            1 - (embedding <=> $1) as similarity
        FROM vulnerability_knowledge
        ORDER BY embedding <=> $1
        LIMIT $2
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(search_sql, query_embedding, limit)

        return [dict(row) for row in rows]

    @staticmethod
    def _compute_content_hash(chunk: dict[str, Any]) -> str:
        """Compute deterministic hash for chunk deduplication.

        Args:
            chunk: Chunk dictionary with metadata

        Returns:
            SHA256 hash string
        """
        # Use source, vulnerability_id, order_index, and content for hash
        hash_input = f"{chunk['source']}|{chunk['vulnerability_id']}|{chunk['order_index']}|{chunk['content']}"
        return hashlib.sha256(hash_input.encode()).hexdigest()


async def process_chunks_file(
    input_file: Path,
    vector_store: VectorStore,
    embedding_service: EmbeddingService,
    batch_size: int = 64,
    limit: int | None = None
):
    """Process a chunks file and populate the vector store.

    Args:
        input_file: Path to JSONL file with chunks
        vector_store: Vector store instance
        embedding_service: Embedding service instance
        batch_size: Number of chunks to process at once
        limit: Maximum number of chunks to process (for testing)
    """
    logger.info(f"Processing chunks from {input_file}")

    # Load chunks
    chunks = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                chunk = json.loads(line)
                chunks.append(chunk)

                if limit and len(chunks) >= limit:
                    break

    logger.info(f"Loaded {len(chunks)} chunks from {input_file}")

    # Process in batches
    total_processed = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

        # Extract content for embedding
        texts = [chunk["content"] for chunk in batch]

        # Generate embeddings
        embeddings = await embedding_service.embed_texts(texts)

        # Store in database
        await vector_store.upsert_chunks(batch, embeddings)

        total_processed += len(batch)
        logger.info(f"Processed {total_processed}/{len(chunks)} chunks")

    return total_processed


@click.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Input JSONL file with chunks"
)
@click.option(
    "--rebuild",
    is_flag=True,
    help="Truncate table before inserting (rebuild from scratch)"
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit number of chunks to process (for testing)"
)
@click.option(
    "--batch-size",
    type=int,
    default=64,
    help="Batch size for processing chunks"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without making changes"
)
@click.option(
    "--test-query",
    type=str,
    default=None,
    help="Test similarity search with given query after population"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
def main(
    input_file: Path,
    rebuild: bool,
    limit: int | None,
    batch_size: int,
    dry_run: bool,
    test_query: str | None,
    log_level: str
) -> None:
    """Populate vector store with vulnerability knowledge embeddings."""
    asyncio.run(async_main(
        input_file=input_file,
        rebuild=rebuild,
        limit=limit,
        batch_size=batch_size,
        dry_run=dry_run,
        test_query=test_query,
        log_level=log_level
    ))


async def async_main(
    input_file: Path,
    rebuild: bool,
    limit: int | None,
    batch_size: int,
    dry_run: bool,
    test_query: str | None,
    log_level: str
) -> None:
    """Async implementation of the main function."""

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Load settings
    settings = get_settings()

    try:
        if dry_run:
            # Dry run - just show what would be processed
            with open(input_file, "r", encoding="utf-8") as f:
                total_lines = sum(1 for line in f if line.strip())

            chunks_to_process = min(total_lines, limit) if limit else total_lines

            click.echo(f"\n🔬 Dry Run - Would Process:")
            click.echo(f"   • Input file: {input_file}")
            click.echo(f"   • Total chunks in file: {total_lines:,}")
            click.echo(f"   • Chunks to process: {chunks_to_process:,}")
            click.echo(f"   • Batch size: {batch_size}")
            click.echo(f"   • Rebuild mode: {rebuild}")
            click.echo(f"   • Would connect to: {settings.DATABASE_URL}")
            return

        # Initialize services for real run
        embedding_service = EmbeddingService(settings.OPENAI_API_KEY)
        vector_store = VectorStore(settings.DATABASE_URL)

        await vector_store.initialize()

        # Show initial stats
        initial_stats = await vector_store.get_stats()
        click.echo(f"\n📊 Initial Vector Store Stats:")
        click.echo(f"   • Total chunks: {initial_stats['total_chunks']:,}")
        click.echo(f"   • Sources: {initial_stats['sources']}")
        click.echo(f"   • Vulnerabilities: {initial_stats['vulnerabilities']}")

        if rebuild:
            click.echo("\n🗑️  Rebuilding: truncating existing data...")
            await vector_store.truncate_table()

        # Process chunks
        processed_count = await process_chunks_file(
            input_file=input_file,
            vector_store=vector_store,
            embedding_service=embedding_service,
            batch_size=batch_size,
            limit=limit
        )

        # Show final stats
        final_stats = await vector_store.get_stats()
        click.echo(f"\n✅ Processing Complete:")
        click.echo(f"   • Processed chunks: {processed_count:,}")
        click.echo(f"   • Total chunks in DB: {final_stats['total_chunks']:,}")
        click.echo(f"   • Sources: {final_stats['sources']}")
        click.echo(f"   • Vulnerabilities: {final_stats['vulnerabilities']}")
        click.echo(f"   • Avg content length: {final_stats['avg_content_length']} chars")

        # Test similarity search if requested
        if test_query:
            click.echo(f"\n🔍 Testing similarity search for: '{test_query}'")
            results = await vector_store.test_similarity_search(test_query, embedding_service)

            for i, result in enumerate(results, 1):
                click.echo(f"\n   {i}. [{result['source']}] {result['vulnerability_id']}: {result['title']}")
                click.echo(f"      Similarity: {result['similarity']:.3f}")
                click.echo(f"      Content: {result['content'][:100]}...")

        await vector_store.close()

    except Exception as e:
        logger.error(f"Failed to populate vector store: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()