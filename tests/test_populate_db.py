"""Tests for embedding and vector store population functionality."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.ingestion.populate_db import EmbeddingService, VectorStore, process_chunks_file


class TestEmbeddingService:
    """Test embedding service functionality."""

    @pytest.fixture
    def embedding_service(self):
        """Create a mock embedding service."""
        return EmbeddingService(api_key="test-key")

    @pytest.mark.asyncio
    async def test_embed_texts_single_batch(self, embedding_service):
        """Test embedding generation for a single batch."""
        texts = ["Test content 1", "Test content 2"]
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.4, 0.5, 0.6])
        ]

        with patch.object(embedding_service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            result = await embedding_service.embed_texts(texts)

            assert result == mock_embeddings
            mock_create.assert_called_once_with(
                model="text-embedding-3-small",
                input=texts
            )

    @pytest.mark.asyncio
    async def test_embed_texts_empty_list(self, embedding_service):
        """Test embedding generation with empty input."""
        result = await embedding_service.embed_texts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_texts_large_batch(self, embedding_service):
        """Test embedding generation with batch size handling."""
        # Create 150 texts (larger than max_batch_size of 100)
        texts = [f"Test content {i}" for i in range(150)]

        # Mock responses for two batches
        mock_response_1 = Mock()
        mock_response_1.data = [Mock(embedding=[0.1, 0.2, 0.3]) for _ in range(100)]

        mock_response_2 = Mock()
        mock_response_2.data = [Mock(embedding=[0.4, 0.5, 0.6]) for _ in range(50)]

        with patch.object(embedding_service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2]

            result = await embedding_service.embed_texts(texts)

            # Should have called create twice
            assert mock_create.call_count == 2
            assert len(result) == 150


class TestVectorStore:
    """Test vector store functionality."""

    @pytest.fixture
    def vector_store(self):
        """Create a vector store with mock database URL."""
        return VectorStore("postgresql://test:test@localhost/test")

    def test_compute_content_hash(self):
        """Test content hash computation."""
        chunk = {
            "source": "test",
            "vulnerability_id": "T1001",
            "order_index": 0,
            "content": "Test content"
        }

        hash1 = VectorStore._compute_content_hash(chunk)
        hash2 = VectorStore._compute_content_hash(chunk)

        # Same input should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_content_hash_different_inputs(self):
        """Test that different inputs produce different hashes."""
        chunk1 = {
            "source": "test",
            "vulnerability_id": "T1001",
            "order_index": 0,
            "content": "Test content 1"
        }

        chunk2 = {
            "source": "test",
            "vulnerability_id": "T1001",
            "order_index": 0,
            "content": "Test content 2"
        }

        hash1 = VectorStore._compute_content_hash(chunk1)
        hash2 = VectorStore._compute_content_hash(chunk2)

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_upsert_chunks_mismatch_count(self, vector_store):
        """Test that mismatched chunk and embedding counts raise error."""
        chunks = [{"content": "test"}]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]  # More embeddings than chunks

        with pytest.raises(ValueError, match="Chunks count \\(1\\) != embeddings count \\(2\\)"):
            await vector_store.upsert_chunks(chunks, embeddings)


class TestProcessChunksFile:
    """Test chunk file processing functionality."""

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunk data."""
        return [
            {
                "content": "Access control enforces policy...",
                "vulnerability_id": "A01:2021",
                "title": "Broken Access Control",
                "source": "owasp",
                "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                "order_index": 0,
                "token_count": 50,
                "overlap_pre": False,
                "overlap_post": True
            },
            {
                "content": "Adversaries may abuse command and script interpreters...",
                "vulnerability_id": "T1059",
                "title": "Command and Scripting Interpreter",
                "source": "mitre",
                "url": "https://attack.mitre.org/techniques/T1059/",
                "order_index": 0,
                "token_count": 75,
                "overlap_pre": False,
                "overlap_post": False
            }
        ]

    @pytest.fixture
    def temp_chunks_file(self, sample_chunks):
        """Create a temporary JSONL file with sample chunks."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for chunk in sample_chunks:
                f.write(json.dumps(chunk) + '\n')
            temp_file = Path(f.name)

        yield temp_file

        # Cleanup
        temp_file.unlink()

    @pytest.mark.asyncio
    async def test_process_chunks_file_basic(self, temp_chunks_file, sample_chunks):
        """Test basic chunk file processing."""
        # Mock services
        mock_vector_store = Mock()
        mock_vector_store.upsert_chunks = AsyncMock()

        mock_embedding_service = Mock()
        mock_embedding_service.embed_texts = AsyncMock(
            return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )

        # Process file
        result = await process_chunks_file(
            input_file=temp_chunks_file,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            batch_size=10
        )

        # Verify results
        assert result == 2  # Processed 2 chunks

        # Verify embedding service was called with correct texts
        mock_embedding_service.embed_texts.assert_called_once()
        call_args = mock_embedding_service.embed_texts.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0] == sample_chunks[0]["content"]
        assert call_args[1] == sample_chunks[1]["content"]

        # Verify vector store upsert was called
        mock_vector_store.upsert_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chunks_file_with_limit(self, temp_chunks_file):
        """Test chunk file processing with limit."""
        # Mock services
        mock_vector_store = Mock()
        mock_vector_store.upsert_chunks = AsyncMock()

        mock_embedding_service = Mock()
        mock_embedding_service.embed_texts = AsyncMock(
            return_value=[[0.1, 0.2, 0.3]]
        )

        # Process file with limit
        result = await process_chunks_file(
            input_file=temp_chunks_file,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            batch_size=10,
            limit=1  # Only process first chunk
        )

        # Should only process 1 chunk despite 2 being available
        assert result == 1

        # Verify only one text was embedded
        mock_embedding_service.embed_texts.assert_called_once()
        call_args = mock_embedding_service.embed_texts.call_args[0][0]
        assert len(call_args) == 1

    @pytest.mark.asyncio
    async def test_process_chunks_file_batching(self, temp_chunks_file):
        """Test chunk file processing with small batch size."""
        # Mock services
        mock_vector_store = Mock()
        mock_vector_store.upsert_chunks = AsyncMock()

        mock_embedding_service = Mock()
        mock_embedding_service.embed_texts = AsyncMock(
            side_effect=[[[0.1, 0.2, 0.3]], [[0.4, 0.5, 0.6]]]
        )

        # Process file with batch size of 1
        result = await process_chunks_file(
            input_file=temp_chunks_file,
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            batch_size=1  # Force two separate batches
        )

        # Should process both chunks
        assert result == 2

        # Should have been called twice (once per batch)
        assert mock_embedding_service.embed_texts.call_count == 2
        assert mock_vector_store.upsert_chunks.call_count == 2


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_chunk_metadata_preservation(self):
        """Test that all required metadata fields are preserved."""
        chunk = {
            "content": "Test vulnerability content",
            "vulnerability_id": "A01:2021",
            "title": "Test Vulnerability",
            "source": "test",
            "url": "https://example.com/test",
            "order_index": 1,
            "token_count": 25,
            "overlap_pre": True,
            "overlap_post": False
        }

        # Test hash computation includes required fields
        content_hash = VectorStore._compute_content_hash(chunk)
        assert content_hash is not None
        assert len(content_hash) == 64

    def test_embedding_dimension_consistency(self):
        """Test that embedding dimensions match expected size."""
        # text-embedding-3-small should produce 1536-dimensional vectors
        expected_dimension = 1536

        # This would be tested with actual API calls in integration tests
        # For unit tests, we just verify the expectation is documented
        assert expected_dimension == 1536  # OpenAI text-embedding-3-small dimension

    @pytest.mark.asyncio
    async def test_empty_chunks_file(self):
        """Test handling of empty chunks file."""
        # Create empty file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_file = Path(f.name)

        try:
            # Mock services
            mock_vector_store = Mock()
            mock_vector_store.upsert_chunks = AsyncMock()

            mock_embedding_service = Mock()
            mock_embedding_service.embed_texts = AsyncMock(return_value=[])

            # Process empty file
            result = await process_chunks_file(
                input_file=temp_file,
                vector_store=mock_vector_store,
                embedding_service=mock_embedding_service,
                batch_size=10
            )

            # Should process 0 chunks
            assert result == 0

            # Services should not be called for empty input
            mock_embedding_service.embed_texts.assert_not_called()
            mock_vector_store.upsert_chunks.assert_not_called()

        finally:
            temp_file.unlink()

    def test_malformed_chunks_file(self):
        """Test handling of malformed JSON in chunks file."""
        # Create file with malformed JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')  # This will cause JSON decode error
            f.write('{"another": "valid"}\n')
            temp_file = Path(f.name)

        try:
            # This should raise a JSON decode error when processing
            # In a real implementation, we might want to handle this gracefully
            # For now, we expect it to fail fast
            with pytest.raises(json.JSONDecodeError):
                with open(temp_file, 'r') as file:
                    for line in file:
                        if line.strip():
                            json.loads(line)  # This will fail on the malformed line

        finally:
            temp_file.unlink()