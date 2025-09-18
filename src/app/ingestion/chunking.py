"""Text chunking strategy for technical documents.

This module implements a recursive, structure-aware chunker that splits
vulnerability documents into semantically coherent chunks while preserving
paragraphs/sentences and maintaining proper metadata.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a chunk of text with metadata."""

    content: str
    vulnerability_id: str
    title: str
    source: str
    url: str | None
    order_index: int
    token_count: int
    overlap_pre: bool = False
    overlap_post: bool = False


class TokenEstimator:
    """Simple token estimator using character-to-token ratio."""

    def __init__(self, chars_per_token: float = 4.0):
        """Initialize with average characters per token.

        Args:
            chars_per_token: Average characters per token (GPT models ~4 chars/token)
        """
        self.chars_per_token = chars_per_token

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text."""
        return max(1, int(len(text) / self.chars_per_token))

    def estimate_chars_for_tokens(self, token_count: int) -> int:
        """Estimate character count for given token target."""
        return int(token_count * self.chars_per_token)


class RecursiveTextSplitter:
    """Recursive text splitter with prioritized separators."""

    def __init__(
        self,
        max_tokens: int = 512,
        min_tokens: int = 50,
        overlap_tokens: int = 50,
        tokenizer: TokenEstimator | None = None
    ):
        """Initialize the text splitter.

        Args:
            max_tokens: Maximum tokens per chunk
            min_tokens: Minimum tokens per chunk
            overlap_tokens: Target overlap between chunks
            tokenizer: Token estimator (defaults to character-based)
        """
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens
        self.tokenizer = tokenizer or TokenEstimator()

        # Prioritized separators for recursive splitting
        self.separators = [
            "\n\n\n",  # Multiple line breaks
            "\n\n",    # Paragraph breaks
            "\n",      # Line breaks
            ". ",      # Sentence endings
            "! ",      # Exclamation sentences
            "? ",      # Question sentences
            "; ",      # Semicolon breaks
            ", ",      # Comma breaks
            " ",       # Word breaks
            ""         # Character-level fallback
        ]

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks using recursive separator strategy."""
        if not text.strip():
            return []

        # Check if text fits within limits
        token_count = self.tokenizer.estimate_tokens(text)
        if token_count <= self.max_tokens:
            if token_count >= self.min_tokens:
                return [text.strip()]
            else:
                # Text too short, return as-is if not empty
                return [text.strip()] if text.strip() else []

        # Find best separator to split the text
        return self._recursive_split(text, 0)

    def _recursive_split(self, text: str, separator_index: int) -> list[str]:
        """Recursively split text using prioritized separators."""
        if separator_index >= len(self.separators):
            # Fallback: character-level split
            return self._character_split(text)

        separator = self.separators[separator_index]

        if separator == "":
            # Character-level fallback
            return self._character_split(text)

        if separator not in text:
            # Try next separator
            return self._recursive_split(text, separator_index + 1)

        # Split by current separator
        parts = text.split(separator)
        if len(parts) == 1:
            # No split occurred, try next separator
            return self._recursive_split(text, separator_index + 1)

        # Recombine parts to fit within token limits
        chunks = []
        current_chunk = ""

        for i, part in enumerate(parts):
            # Add separator back (except for last part)
            part_with_sep = part + (separator if i < len(parts) - 1 else "")

            # Check if adding this part would exceed limits
            test_chunk = current_chunk + part_with_sep
            if self.tokenizer.estimate_tokens(test_chunk) <= self.max_tokens:
                current_chunk = test_chunk
            else:
                # Current chunk is ready, start new one
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # Check if single part is too large
                if self.tokenizer.estimate_tokens(part_with_sep) > self.max_tokens:
                    # Recursively split this part
                    sub_chunks = self._recursive_split(part_with_sep, separator_index + 1)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = part_with_sep

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk]

    def _character_split(self, text: str) -> list[str]:
        """Fallback character-level splitting."""
        max_chars = self.tokenizer.estimate_chars_for_tokens(self.max_tokens)
        chunks = []

        for i in range(0, len(text), max_chars):
            chunk = text[i:i + max_chars]
            if chunk.strip():
                chunks.append(chunk.strip())

        return chunks

    def create_overlapping_chunks(self, chunks: list[str]) -> list[str]:
        """Add overlap between adjacent chunks."""
        if len(chunks) <= 1:
            return chunks

        overlapped_chunks = []
        overlap_chars = self.tokenizer.estimate_chars_for_tokens(self.overlap_tokens)

        for i, chunk in enumerate(chunks):
            final_chunk = chunk

            # Add prefix overlap from previous chunk
            if i > 0 and overlap_chars > 0:
                prev_chunk = chunks[i - 1]
                if len(prev_chunk) > overlap_chars:
                    overlap_prefix = prev_chunk[-overlap_chars:]
                    # Try to break at word boundary
                    space_pos = overlap_prefix.find(' ')
                    if space_pos > 0:
                        overlap_prefix = overlap_prefix[space_pos + 1:]
                    final_chunk = overlap_prefix + " " + final_chunk

            overlapped_chunks.append(final_chunk)

        return overlapped_chunks


def chunk_document(
    *,
    text: str,
    metadata: dict[str, Any],
    max_tokens: int = 512,
    min_tokens: int = 50,
    overlap_tokens: int = 50
) -> list[dict[str, Any]]:
    """Chunk a document into semantically coherent pieces.

    Args:
        text: The text content to chunk
        metadata: Document metadata (id, title, source, url)
        max_tokens: Maximum tokens per chunk
        min_tokens: Minimum tokens per chunk
        overlap_tokens: Target overlap between chunks

    Returns:
        List of chunk dictionaries with content and metadata
    """
    if not text.strip():
        return []

    # Initialize splitter
    splitter = RecursiveTextSplitter(
        max_tokens=max_tokens,
        min_tokens=min_tokens,
        overlap_tokens=overlap_tokens
    )

    # Split text into chunks
    text_chunks = splitter.split_text(text)

    if not text_chunks:
        return []

    # Add overlaps
    if len(text_chunks) > 1 and overlap_tokens > 0:
        text_chunks = splitter.create_overlapping_chunks(text_chunks)

    # Create chunk objects with metadata
    chunks = []
    for i, content in enumerate(text_chunks):
        token_count = splitter.tokenizer.estimate_tokens(content)

        chunk = Chunk(
            content=content,
            vulnerability_id=metadata.get("id", ""),
            title=metadata.get("title", ""),
            source=metadata.get("source", ""),
            url=metadata.get("url"),
            order_index=i,
            token_count=token_count,
            overlap_pre=i > 0 and overlap_tokens > 0,
            overlap_post=i < len(text_chunks) - 1 and overlap_tokens > 0
        )

        chunks.append(asdict(chunk))

    logger.info(f"Chunked document '{metadata.get('id', 'unknown')}' into {len(chunks)} chunks")
    return chunks


@click.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Input JSONL file (from MITRE/OWASP ingestion)"
)
@click.option(
    "--output-file",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSONL file (default: input_file.chunked.jsonl)"
)
@click.option(
    "--max-tokens",
    type=int,
    default=512,
    help="Maximum tokens per chunk"
)
@click.option(
    "--min-tokens",
    type=int,
    default=50,
    help="Minimum tokens per chunk"
)
@click.option(
    "--overlap-tokens",
    type=int,
    default=50,
    help="Overlap tokens between chunks"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print summary without writing output"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
def main(
    input_file: Path,
    output_file: Path | None,
    max_tokens: int,
    min_tokens: int,
    overlap_tokens: int,
    dry_run: bool,
    log_level: str
) -> None:
    """Chunk vulnerability documents from ingestion output."""

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        # Read input records
        records = []
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

        logger.info(f"Loaded {len(records)} records from {input_file}")

        # Process each record
        all_chunks = []
        total_input_chars = 0
        total_output_chars = 0

        for record in records:
            text = record.get("description", "")
            if not text:
                logger.warning(f"No description found for record {record.get('id', 'unknown')}")
                continue

            total_input_chars += len(text)

            # Chunk the document
            chunks = chunk_document(
                text=text,
                metadata=record,
                max_tokens=max_tokens,
                min_tokens=min_tokens,
                overlap_tokens=overlap_tokens
            )

            all_chunks.extend(chunks)
            total_output_chars += sum(len(chunk["content"]) for chunk in chunks)

        # Print summary
        avg_chunk_size = total_output_chars / len(all_chunks) if all_chunks else 0
        expansion_ratio = total_output_chars / total_input_chars if total_input_chars else 0

        click.echo(f"\n📊 Chunking Summary:")
        click.echo(f"   • Input records: {len(records)}")
        click.echo(f"   • Output chunks: {len(all_chunks)}")
        click.echo(f"   • Input characters: {total_input_chars:,}")
        click.echo(f"   • Output characters: {total_output_chars:,}")
        click.echo(f"   • Average chunk size: {avg_chunk_size:.0f} chars")
        click.echo(f"   • Expansion ratio: {expansion_ratio:.2f}x")
        click.echo(f"   • Chunking settings: max={max_tokens}, min={min_tokens}, overlap={overlap_tokens}")

        if not dry_run:
            # Determine output file
            if output_file is None:
                output_file = input_file.with_suffix('.chunked.jsonl')

            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Write chunks
            with open(output_file, "w", encoding="utf-8") as f:
                for chunk in all_chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

            click.echo(f"   • Output written to: {output_file}")
        else:
            click.echo(f"   • Dry run - no output written")

    except Exception as e:
        logger.error(f"Failed to chunk documents: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()