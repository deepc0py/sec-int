"""Knowledge base retrieval service for vulnerability analysis.

This module provides vector similarity search capabilities over the vulnerability
knowledge base, enabling the AI agent to retrieve relevant context for analysis.
"""

import logging
from typing import Any

import asyncpg
from openai import AsyncOpenAI

from app.models import RetrievedContext, VulnerabilityFinding

logger = logging.getLogger(__name__)


class RetrievalService:
    """Service for retrieving relevant chunks from the vulnerability knowledge base."""

    def __init__(self, pool: asyncpg.Pool, oai_client: AsyncOpenAI):
        """Initialize the retrieval service.

        Args:
            pool: Database connection pool
            oai_client: OpenAI client for embedding generation
        """
        self.pool = pool
        self.oai_client = oai_client
        self.embedding_model = "text-embedding-3-small"

    async def search_vulnerability_knowledge(
        self,
        vulnerability_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> RetrievedContext:
        """Search for relevant knowledge chunks for a vulnerability.

        Args:
            vulnerability_id: The vulnerability identifier (e.g., 'A01:2021', 'T1059')
            top_k: Number of top chunks to retrieve
            similarity_threshold: Minimum similarity score for inclusion

        Returns:
            RetrievedContext with the vulnerability finding and retrieved chunks
        """
        # First, try to get exact metadata for this vulnerability
        vulnerability_info = await self._get_vulnerability_info(vulnerability_id)

        # Create the vulnerability finding
        finding = VulnerabilityFinding(
            id=vulnerability_id,
            source=self._infer_source(vulnerability_id),
            title=vulnerability_info.get("title"),
            description=None
        )

        # Generate enhanced query for better semantic search
        query = self._enhance_query(vulnerability_id, vulnerability_info.get("title"))

        # Get embedding for the query
        query_embedding = await self._generate_embedding(query)

        # Perform vector similarity search
        chunks_data = await self._vector_search(
            query_embedding, vulnerability_id, top_k, similarity_threshold
        )

        # Extract components for RetrievedContext
        retrieved_chunks = [chunk["content"] for chunk in chunks_data]
        source_urls = list(set(chunk["url"] for chunk in chunks_data if chunk["url"]))
        similarity_scores = [chunk["similarity_score"] for chunk in chunks_data]

        return RetrievedContext(
            finding=finding,
            retrieved_chunks=retrieved_chunks,
            source_urls=source_urls,
            similarity_scores=similarity_scores,
            retrieval_query=query
        )

    async def _get_vulnerability_info(self, vulnerability_id: str) -> dict[str, Any]:
        """Get basic info about a vulnerability from the database."""
        query = """
        SELECT DISTINCT title, url, source
        FROM vulnerability_knowledge
        WHERE vulnerability_id = $1
        LIMIT 1
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, vulnerability_id)
            if row:
                return {
                    "title": row["title"],
                    "url": row["url"],
                    "source": row["source"]
                }
            return {}

    def _infer_source(self, vulnerability_id: str) -> str:
        """Infer the source taxonomy from vulnerability ID format."""
        if vulnerability_id.startswith(("A", "A0")) and ":" in vulnerability_id:
            return "owasp"
        elif vulnerability_id.startswith("T") and ("." in vulnerability_id or vulnerability_id[1:].isdigit()):
            return "mitre"
        elif vulnerability_id.upper().startswith("CVE-"):
            return "cve"
        else:
            return "custom"

    def _enhance_query(self, vulnerability_id: str, title: str | None) -> str:
        """Enhance the search query with additional context."""
        parts = [vulnerability_id]

        if title:
            parts.append(title)

        # Add common vulnerability terms for better semantic matching
        if self._infer_source(vulnerability_id) == "owasp":
            parts.append("web application security vulnerability")
        elif self._infer_source(vulnerability_id) == "mitre":
            parts.append("attack technique threat")

        return " ".join(parts)

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for the given text."""
        try:
            response = await self.oai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise

    async def _vector_search(
        self,
        query_embedding: list[float],
        vulnerability_id: str,
        top_k: int,
        similarity_threshold: float
    ) -> list[dict[str, Any]]:
        """Perform vector similarity search with hybrid filtering."""
        # Use cosine distance for similarity search
        # PostgreSQL pgvector uses <-> operator for cosine distance
        query = """
        SELECT
            content,
            title,
            url,
            source,
            vulnerability_id,
            1 - (embedding <-> $1::vector) as similarity_score
        FROM vulnerability_knowledge
        WHERE
            (vulnerability_id = $2 OR 1 - (embedding <-> $1::vector) >= $3)
        ORDER BY
            CASE WHEN vulnerability_id = $2 THEN 0 ELSE 1 END,
            embedding <-> $1::vector
        LIMIT $4
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                query,
                str(query_embedding),  # Convert embedding list to string for PostgreSQL vector type
                vulnerability_id,
                similarity_threshold,
                top_k
            )

            return [
                {
                    "content": row["content"],
                    "title": row["title"],
                    "url": row["url"],
                    "source": row["source"],
                    "vulnerability_id": row["vulnerability_id"],
                    "similarity_score": float(row["similarity_score"])
                }
                for row in rows
            ]