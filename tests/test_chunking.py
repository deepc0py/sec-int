"""Tests for text chunking functionality."""

from app.ingestion.chunking import (
    Chunk,
    RecursiveTextSplitter,
    TokenEstimator,
    chunk_document,
)


class TestTokenEstimator:
    """Test token estimation functionality."""

    def test_token_estimation(self):
        """Test basic token estimation."""
        estimator = TokenEstimator(chars_per_token=4.0)

        assert estimator.estimate_tokens("test") == 1  # 4 chars / 4 = 1 token
        assert estimator.estimate_tokens("hello world") == 2  # 11 chars / 4 = 2.75 -> 2 tokens
        assert estimator.estimate_tokens("this is a longer sentence") == 6  # 25 chars / 4 = 6.25 -> 6 tokens

    def test_char_estimation(self):
        """Test character count estimation for token targets."""
        estimator = TokenEstimator(chars_per_token=4.0)

        assert estimator.estimate_chars_for_tokens(10) == 40
        assert estimator.estimate_chars_for_tokens(100) == 400

    def test_minimum_token_count(self):
        """Test that minimum token count is 1."""
        estimator = TokenEstimator(chars_per_token=4.0)

        assert estimator.estimate_tokens("") == 1
        assert estimator.estimate_tokens("a") == 1


class TestRecursiveTextSplitter:
    """Test recursive text splitting functionality."""

    def test_short_text_no_split(self):
        """Test that short text is not split."""
        splitter = RecursiveTextSplitter(max_tokens=100, min_tokens=10)
        text = "This is a short text that should not be split."

        chunks = splitter.split_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        """Test handling of empty text."""
        splitter = RecursiveTextSplitter(max_tokens=100, min_tokens=10)

        chunks = splitter.split_text("")
        assert len(chunks) == 0

        chunks = splitter.split_text("   ")
        assert len(chunks) == 0

    def test_paragraph_splitting(self):
        """Test splitting on paragraph boundaries."""
        splitter = RecursiveTextSplitter(max_tokens=20, min_tokens=5)
        text = """First paragraph with some content here.

Second paragraph with more content that should be split.

Third paragraph with additional content."""

        chunks = splitter.split_text(text)

        assert len(chunks) >= 2
        # Ensure we don't have empty chunks
        assert all(chunk.strip() for chunk in chunks)

    def test_sentence_splitting(self):
        """Test splitting on sentence boundaries."""
        splitter = RecursiveTextSplitter(max_tokens=15, min_tokens=3)
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."

        chunks = splitter.split_text(text)

        assert len(chunks) >= 2
        # Check that sentences are generally preserved
        for chunk in chunks:
            assert chunk.strip()

    def test_word_splitting(self):
        """Test fallback to word-level splitting."""
        splitter = RecursiveTextSplitter(max_tokens=10, min_tokens=2)
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"

        chunks = splitter.split_text(text)

        assert len(chunks) >= 2
        assert all(chunk.strip() for chunk in chunks)

    def test_character_splitting_fallback(self):
        """Test character-level splitting as last resort."""
        splitter = RecursiveTextSplitter(max_tokens=5, min_tokens=1)
        text = "verylongwordwithoutanyspacesorpunctuation"

        chunks = splitter.split_text(text)

        assert len(chunks) >= 2
        assert all(chunk.strip() for chunk in chunks)

    def test_overlapping_chunks(self):
        """Test creation of overlapping chunks."""
        splitter = RecursiveTextSplitter(max_tokens=20, min_tokens=5, overlap_tokens=5)
        chunks = [
            "First chunk with some content here.",
            "Second chunk with different content.",
            "Third chunk with final content."
        ]

        overlapped = splitter.create_overlapping_chunks(chunks)

        assert len(overlapped) == len(chunks)
        # Second chunk should contain some content from first chunk
        assert len(overlapped[1]) > len(chunks[1])

    def test_no_overlap_single_chunk(self):
        """Test that single chunks don't get overlap processing."""
        splitter = RecursiveTextSplitter(max_tokens=100, min_tokens=10, overlap_tokens=10)
        chunks = ["Single chunk with content."]

        overlapped = splitter.create_overlapping_chunks(chunks)

        assert len(overlapped) == 1
        assert overlapped[0] == chunks[0]


class TestChunkDocument:
    """Test the main chunk_document function."""

    def test_chunk_document_basic(self):
        """Test basic document chunking functionality."""
        text = """This is a test document with multiple paragraphs.

The second paragraph contains more information about the vulnerability.

The third paragraph provides prevention strategies and examples."""

        metadata = {
            "id": "TEST-001",
            "title": "Test Vulnerability",
            "source": "test",
            "url": "https://example.com/test"
        }

        chunks = chunk_document(
            text=text,
            metadata=metadata,
            max_tokens=50,
            min_tokens=10,
            overlap_tokens=10
        )

        assert len(chunks) >= 1
        assert all(isinstance(chunk, dict) for chunk in chunks)

        # Check first chunk structure
        first_chunk = chunks[0]
        assert "content" in first_chunk
        assert "vulnerability_id" in first_chunk
        assert "title" in first_chunk
        assert "source" in first_chunk
        assert "url" in first_chunk
        assert "order_index" in first_chunk
        assert "token_count" in first_chunk

        # Check metadata preservation
        assert first_chunk["vulnerability_id"] == "TEST-001"
        assert first_chunk["title"] == "Test Vulnerability"
        assert first_chunk["source"] == "test"
        assert first_chunk["url"] == "https://example.com/test"

    def test_chunk_document_ordering(self):
        """Test that chunks maintain proper ordering."""
        text = "Paragraph one. Paragraph two. Paragraph three. Paragraph four."

        metadata = {
            "id": "TEST-002",
            "title": "Test Document",
            "source": "test"
        }

        chunks = chunk_document(
            text=text,
            metadata=metadata,
            max_tokens=10,
            min_tokens=2,
            overlap_tokens=2
        )

        # Check order_index is sequential
        for i, chunk in enumerate(chunks):
            assert chunk["order_index"] == i

    def test_chunk_document_empty_text(self):
        """Test handling of empty text."""
        metadata = {"id": "TEST-003", "title": "Empty Test", "source": "test"}

        chunks = chunk_document(text="", metadata=metadata)
        assert len(chunks) == 0

        chunks = chunk_document(text="   ", metadata=metadata)
        assert len(chunks) == 0

    def test_chunk_document_overlap_flags(self):
        """Test overlap flags are set correctly."""
        text = "First section content. Second section content. Third section content."

        metadata = {
            "id": "TEST-004",
            "title": "Overlap Test",
            "source": "test"
        }

        chunks = chunk_document(
            text=text,
            metadata=metadata,
            max_tokens=15,
            min_tokens=3,
            overlap_tokens=5
        )

        if len(chunks) > 1:
            # First chunk should not have pre-overlap
            assert chunks[0]["overlap_pre"] is False
            assert chunks[0]["overlap_post"] is True

            # Middle chunks should have both overlaps
            for chunk in chunks[1:-1]:
                assert chunk["overlap_pre"] is True
                assert chunk["overlap_post"] is True

            # Last chunk should not have post-overlap
            assert chunks[-1]["overlap_pre"] is True
            assert chunks[-1]["overlap_post"] is False

    def test_chunk_document_no_overlap(self):
        """Test chunking without overlap."""
        text = "Content for testing chunking without any overlap between chunks."

        metadata = {
            "id": "TEST-005",
            "title": "No Overlap Test",
            "source": "test"
        }

        chunks = chunk_document(
            text=text,
            metadata=metadata,
            max_tokens=20,
            min_tokens=5,
            overlap_tokens=0
        )

        # All overlap flags should be False
        for chunk in chunks:
            assert chunk["overlap_pre"] is False
            assert chunk["overlap_post"] is False

    def test_chunk_document_token_counts(self):
        """Test that token counts are within expected ranges."""
        text = "This is a longer document that should be split into multiple chunks " * 10

        metadata = {
            "id": "TEST-006",
            "title": "Token Count Test",
            "source": "test"
        }

        max_tokens = 50
        min_tokens = 10

        chunks = chunk_document(
            text=text,
            metadata=metadata,
            max_tokens=max_tokens,
            min_tokens=min_tokens,
            overlap_tokens=10
        )

        # Check token counts are reasonable (allowing for estimation variance)
        for chunk in chunks:
            token_count = chunk["token_count"]
            assert token_count >= 1  # At least 1 token
            # Allow some variance for token estimation
            assert token_count <= max_tokens * 1.3  # 30% tolerance

    def test_real_vulnerability_content(self):
        """Test with realistic vulnerability content."""
        text = """Access control enforces policy such that users cannot act outside of their intended permissions.
        Failures typically lead to unauthorized information disclosure, modification, or destruction of all data or
        performing a business function outside the user's limits.

        Common access control vulnerabilities include:

        • Violation of the principle of least privilege
        • Bypassing access control checks by modifying the URL
        • Permitting viewing or editing someone else's account
        • Elevation of privilege

        How to Prevent:

        • Except for public resources, deny by default
        • Implement access control mechanisms once and re-use them
        • Model access controls should enforce record ownership
        • Disable web server directory listing"""

        metadata = {
            "id": "A01:2021",
            "title": "Broken Access Control",
            "source": "owasp",
            "url": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"
        }

        chunks = chunk_document(
            text=text,
            metadata=metadata,
            max_tokens=100,
            min_tokens=20,
            overlap_tokens=20
        )

        assert len(chunks) >= 1
        assert all(chunk["content"].strip() for chunk in chunks)
        assert all(chunk["vulnerability_id"] == "A01:2021" for chunk in chunks)