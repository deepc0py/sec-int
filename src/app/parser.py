"""Parser for extracting OWASP and MITRE ATT&CK vulnerability identifiers.

This module provides functionality to scan normalized text and extract
all OWASP Top 10 and MITRE ATT&CK Enterprise vulnerability identifiers,
returning them as structured VulnerabilityFinding objects.
"""

import re
from typing import List

import click

from app.models import VulnerabilityFinding


# Compiled regex patterns for vulnerability identifiers
MITRE_PATTERN = re.compile(
    r"\b(T\d{4}(?:\.\d{3})?)\b",
    re.IGNORECASE
)
"""Matches MITRE ATT&CK technique IDs: T1234 or T1234.001"""

OWASP_PATTERN = re.compile(
    r"\b(A(?:PI)?\d{1,2}:\d{4})\b",
    re.IGNORECASE
)
"""Matches OWASP identifiers: A01:2021 or API1:2023"""

CVE_PATTERN = re.compile(
    r"\b(CVE-\d{4}-\d{4,})\b",
    re.IGNORECASE
)
"""Matches CVE identifiers: CVE-2023-12345 (requires at least 4 digits after year)"""


def extract_vulnerability_ids(text: str) -> List[VulnerabilityFinding]:
    """Extract all vulnerability identifiers from text.

    Scans the input text for OWASP Top 10, MITRE ATT&CK, and CVE identifiers,
    deduplicates them while preserving order, and returns structured findings.

    Args:
        text: Normalized text to scan for vulnerability identifiers

    Returns:
        List of unique VulnerabilityFinding objects in order of first appearance

    Examples:
        >>> text = "Found A01:2021 and T1059 vulnerabilities. Also T1059.001 sub-technique."
        >>> findings = extract_vulnerability_ids(text)
        >>> [f.id for f in findings]
        ['A01:2021', 'T1059', 'T1059.001']
    """
    if not text:
        return []

    # Track seen IDs to avoid duplicates
    seen_ids = set()
    findings = []

    # Combine all patterns with source mapping for original order preservation
    patterns = [
        (MITRE_PATTERN, "mitre"),
        (OWASP_PATTERN, "owasp"),
        (CVE_PATTERN, "cve"),
    ]

    # Find all matches with their positions for stable ordering
    matches = []
    for pattern, source in patterns:
        for match in pattern.finditer(text):
            vuln_id = match.group(1).upper()  # Normalize to uppercase
            position = match.start()
            matches.append((position, vuln_id, source))

    # Sort by position to preserve original order
    matches.sort(key=lambda x: x[0])

    # Create findings for unique IDs
    for _, vuln_id, source in matches:
        if vuln_id not in seen_ids:
            seen_ids.add(vuln_id)
            findings.append(VulnerabilityFinding(
                id=vuln_id,
                source=source,
                title=None,  # Will be populated by enrichment later
                description=None
            ))

    return findings


def extract_vulnerability_ids_with_context(
    text: str,
    context_chars: int = 100
) -> List[VulnerabilityFinding]:
    """Extract vulnerability IDs with surrounding context.

    Similar to extract_vulnerability_ids but also captures surrounding text
    for additional context about each finding.

    Args:
        text: Normalized text to scan
        context_chars: Number of characters to capture before/after each ID

    Returns:
        List of VulnerabilityFinding objects with description field containing context
    """
    if not text:
        return []

    seen_ids = set()
    findings = []

    patterns = [
        (MITRE_PATTERN, "mitre"),
        (OWASP_PATTERN, "owasp"),
        (CVE_PATTERN, "cve"),
    ]

    matches = []
    for pattern, source in patterns:
        for match in pattern.finditer(text):
            vuln_id = match.group(1).upper()
            position = match.start()

            # Extract context
            start = max(0, position - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end].strip()

            # Clean up context (remove excessive whitespace)
            context = re.sub(r"\s+", " ", context)

            matches.append((position, vuln_id, source, context))

    # Sort by position
    matches.sort(key=lambda x: x[0])

    # Create findings with context
    for _, vuln_id, source, context in matches:
        if vuln_id not in seen_ids:
            seen_ids.add(vuln_id)
            findings.append(VulnerabilityFinding(
                id=vuln_id,
                source=source,
                title=None,
                description=f"...{context}..." if context else None
            ))

    return findings


@click.command()
@click.option(
    "--input-file", "--in",
    type=click.Path(exists=True, readable=True),
    help="Path to text file to parse"
)
@click.option(
    "--text",
    help="Text to parse directly"
)
@click.option(
    "--context/--no-context",
    default=False,
    help="Include surrounding context for each finding"
)
@click.option(
    "--json/--no-json",
    default=False,
    help="Output as JSON instead of human-readable format"
)
def cli(
    input_file: str | None,
    text: str | None,
    context: bool,
    json: bool
) -> None:
    """CLI tool for extracting vulnerability IDs from text.

    Parses text for OWASP, MITRE ATT&CK, and CVE identifiers.
    """
    import sys
    import json as json_lib
    from pathlib import Path

    # Get input text
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
    elif text:
        content = text
    else:
        # Read from stdin if no input specified
        content = sys.stdin.read()

    # Extract findings
    if context:
        findings = extract_vulnerability_ids_with_context(content)
    else:
        findings = extract_vulnerability_ids(content)

    # Output results
    if json:
        output = [f.model_dump() for f in findings]
        click.echo(json_lib.dumps(output, indent=2))
    else:
        if not findings:
            click.echo("No vulnerability identifiers found.", err=True)
        else:
            click.echo(f"Found {len(findings)} unique vulnerability identifier(s):\n")
            for finding in findings:
                click.echo(f"  • {finding.id} ({finding.source})")
                if finding.description:
                    # Indent context
                    lines = finding.description.split("\n")
                    for line in lines:
                        click.echo(f"    {line}")
                    click.echo()


if __name__ == "__main__":
    cli()