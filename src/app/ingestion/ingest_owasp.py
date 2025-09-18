"""OWASP Top 10 data ingestion service.

This module fetches and parses OWASP Top 10 2021 source content,
extracts vulnerability identifiers/titles/descriptions, and outputs
normalized objects ready for chunking and embedding.
"""

import json
import logging
import re
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class OwaspRecord:
    """Normalized OWASP Top 10 vulnerability record."""

    source: str = "owasp"
    id: str = ""
    title: str = ""
    description: str = ""
    url: str | None = None


# OWASP Top 10 2021 vulnerability URLs
OWASP_VULNERABILITIES = {
    "A01:2021": "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
    "A02:2021": "https://owasp.org/Top10/A02_2021-Cryptographic_Failures/",
    "A03:2021": "https://owasp.org/Top10/A03_2021-Injection/",
    "A04:2021": "https://owasp.org/Top10/A04_2021-Insecure_Design/",
    "A05:2021": "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/",
    "A06:2021": "https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/",
    "A07:2021": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/",
    "A08:2021": "https://owasp.org/Top10/A08_2021-Software_and_Data_Integrity_Failures/",
    "A09:2021": "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/",
    "A10:2021": "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/",
}


def extract_title_from_url(url: str) -> str:
    """Extract vulnerability title from OWASP URL."""
    # Extract title from URL pattern like A01_2021-Broken_Access_Control
    match = re.search(r'A\d{2}_2021-([^/]+)', url)
    if match:
        title = match.group(1).replace('_', ' ').replace('-', ' ')
        # Clean up common URL artifacts
        title = title.replace('%28', '(').replace('%29', ')')
        return title.strip()
    return ""


def fetch_vulnerability_content(vuln_id: str, url: str) -> str:
    """Fetch and extract content from an OWASP vulnerability page."""
    logger.info(f"Fetching content for {vuln_id} from {url}")

    try:
        # Create request with User-Agent header to avoid blocking
        request = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )

        with urllib.request.urlopen(request) as response:
            html_content = response.read().decode('utf-8')

        # Parse HTML content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract main content sections
        content_parts = []

        # Look for the main vulnerability description
        # OWASP pages typically have structured content in the main area
        main_content = soup.find('main') or soup.find('div', class_='main') or soup.find('body')

        if main_content:
            # Extract text from paragraphs, avoiding duplicates
            seen_texts = set()
            for element in main_content.find_all(['p', 'div'], class_=lambda x: x != 'nav'):
                # Skip navigation elements
                if element.find_parent(['nav', 'header', 'footer']):
                    continue

                text = element.get_text(strip=True)
                # Only include substantial text and avoid duplicates
                if text and len(text) > 20 and text not in seen_texts:
                    content_parts.append(text)
                    seen_texts.add(text)

        # Join content with appropriate spacing
        full_content = '\n\n'.join(content_parts)

        # Clean up the content
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)  # Remove excessive newlines
        full_content = re.sub(r'[ \t]+', ' ', full_content)  # Normalize whitespace

        logger.info(f"Extracted {len(full_content)} characters for {vuln_id}")
        return full_content.strip()

    except Exception as e:
        logger.error(f"Failed to fetch content for {vuln_id}: {e}")
        return ""


def load_owasp_vulnerabilities() -> list[dict[str, Any]]:
    """Load and extract OWASP Top 10 2021 vulnerabilities.

    Returns:
        List of normalized OWASP vulnerability records as dictionaries.
    """
    logger.info("Loading OWASP Top 10 2021 vulnerabilities...")

    records: list[OwaspRecord] = []

    for vuln_id, url in OWASP_VULNERABILITIES.items():
        logger.info(f"Processing {vuln_id}...")

        # Extract title from URL
        title = extract_title_from_url(url)
        if not title:
            logger.warning(f"Could not extract title for {vuln_id}")
            continue

        # Fetch detailed content
        description = fetch_vulnerability_content(vuln_id, url)
        if not description:
            logger.warning(f"Could not fetch content for {vuln_id}")
            continue

        record = OwaspRecord(
            id=vuln_id,
            title=title,
            description=description,
            url=url
        )

        records.append(record)

    logger.info(f"Successfully extracted {len(records)} OWASP Top 10 records")

    # Convert to dictionaries for consistent interface
    return [asdict(record) for record in records]


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print summary without writing output file"
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSONL file path (default: data/raw/owasp.jsonl)"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
def main(dry_run: bool, output: Path | None, log_level: str) -> None:
    """Ingest OWASP Top 10 2021 data."""

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        # Load OWASP data
        records = load_owasp_vulnerabilities()

        # Print summary
        click.echo("\n📊 OWASP Top 10 2021 Ingestion Summary:")
        click.echo(f"   • Total records extracted: {len(records)}")
        click.echo("   • Source: OWASP Top 10 2021")

        if records:
            # Show sample of extracted IDs
            sample_ids = [r["id"] for r in records[:5]]
            click.echo(f"   • Sample IDs: {', '.join(sample_ids)}")
            if len(records) > 5:
                remaining_ids = [r["id"] for r in records[5:]]
                click.echo(f"   • Remaining: {', '.join(remaining_ids)}")

        if not dry_run:
            # Determine output path
            if output is None:
                output = Path("data/raw/owasp.jsonl")

            # Ensure output directory exists
            output.parent.mkdir(parents=True, exist_ok=True)

            # Write JSONL output
            with open(output, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

            click.echo(f"   • Output written to: {output}")
        else:
            click.echo("   • Dry run - no output written")

    except Exception as e:
        logger.error(f"Failed to ingest OWASP data: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
