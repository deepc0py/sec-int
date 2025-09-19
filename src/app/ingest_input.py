"""Scan result input handler for processing vulnerability scan outputs.

This module provides functionality to accept, validate, normalize, and clean
raw API vulnerability scan output (JSON or text) for downstream parsing.
"""

import json
import re
from typing import Any

import click


class InvalidScanInputError(ValueError):
    """Raised when scan input is invalid or unsupported."""
    pass


# Keys that potentially contain sensitive information
SECRET_KEYS = {
    "api_key", "apikey", "api-key",
    "token", "access_token", "auth_token", "bearer_token",
    "secret", "password", "pass", "passwd",
    "credential", "credentials",
    "private_key", "private-key", "privatekey",
    "client_secret", "client-secret"
}


def _redact_secrets(obj: Any) -> Any:
    """Recursively redact sensitive information from nested structures.

    Args:
        obj: Any object (dict, list, or primitive)

    Returns:
        Object with sensitive values replaced by '***'
    """
    if isinstance(obj, dict):
        return {
            k: ("***REDACTED***" if k.lower() in SECRET_KEYS else _redact_secrets(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_secrets(v) for v in obj]
    return obj


def handle_scan_input(payload: str | dict) -> str:
    """Process and normalize scan input for vulnerability parsing.

    This function accepts raw scan output in either JSON (dict) or text (str) format,
    validates it, removes sensitive information, and normalizes the text for
    downstream processing.

    Args:
        payload: Raw scan output as string or dictionary

    Returns:
        Normalized string representation of the scan output

    Raises:
        InvalidScanInputError: If input is empty, None, or unsupported type
    """
    # Type validation
    if payload is None:
        raise InvalidScanInputError("Input cannot be None")

    # Process based on type
    if isinstance(payload, dict):
        # Redact secrets and convert to formatted JSON string
        cleaned_payload = _redact_secrets(payload)
        normalized_text = json.dumps(cleaned_payload, ensure_ascii=False, indent=2)
    elif isinstance(payload, str):
        normalized_text = payload.strip()
    else:
        raise InvalidScanInputError(
            f"Unsupported input type: {type(payload).__name__}. Expected str or dict."
        )

    # Validate non-empty
    if not normalized_text:
        raise InvalidScanInputError("Input is empty or contains only whitespace")

    # Normalize line endings and whitespace
    # Convert all line endings to Unix-style \n
    normalized_text = re.sub(r"\r\n?|\f", "\n", normalized_text)

    # Collapse excessive newlines (more than 3) to double newlines
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)

    # Remove trailing whitespace from each line
    lines = normalized_text.split("\n")
    normalized_text = "\n".join(line.rstrip() for line in lines)

    # Log warning for extremely large inputs (but still process them)
    if len(normalized_text) > 1_000_000:  # 1MB threshold
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Processing large input: {len(normalized_text):,} characters. "
            "Consider splitting into smaller chunks for better performance."
        )

    return normalized_text


@click.command()
@click.option(
    "--input-file", "--in",
    type=click.Path(exists=True, readable=True),
    required=True,
    help="Path to scan file (.json or .txt)"
)
@click.option(
    "--output-file", "--out",
    type=click.Path(),
    help="Path to output file (default: stdout)"
)
def cli(input_file: str, output_file: str | None) -> None:
    """CLI tool for normalizing vulnerability scan files.

    Reads a scan file (JSON or text), normalizes it, and outputs the result.
    """
    from pathlib import Path

    input_path = Path(input_file)

    try:
        # Read input file
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to parse as JSON first
        try:
            data = json.loads(content)
            normalized = handle_scan_input(data)
        except json.JSONDecodeError:
            # Not JSON, treat as plain text
            normalized = handle_scan_input(content)

        # Output results
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(normalized)
            click.echo(f"✅ Normalized output written to: {output_file}", err=True)
        else:
            click.echo(normalized)

    except InvalidScanInputError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()