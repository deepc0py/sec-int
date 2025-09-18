"""MITRE ATT&CK data ingestion service.

This module fetches the latest MITRE ATT&CK Enterprise matrix data,
extracts technique and sub-technique records, and outputs normalized
objects ready for chunking and embedding.
"""

import json
import logging
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click
from mitreattack.stix20 import MitreAttackData

logger = logging.getLogger(__name__)


@dataclass
class MitreRecord:
    """Normalized MITRE ATT&CK technique record."""

    source: str = "mitre"
    id: str = ""
    title: str = ""
    description: str = ""
    url: str | None = None
    stix_id: str = ""


def load_enterprise_objects() -> list[dict[str, Any]]:
    """Load and extract MITRE ATT&CK Enterprise techniques.

    Returns:
        List of normalized MITRE technique records as dictionaries.
    """
    logger.info("Loading MITRE ATT&CK Enterprise dataset...")

    # Download the latest Enterprise ATT&CK STIX data
    enterprise_url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

    logger.info(f"Downloading STIX data from {enterprise_url}")

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
        try:
            with urllib.request.urlopen(enterprise_url) as response:
                stix_data = response.read().decode('utf-8')
                temp_file.write(stix_data)
                temp_file.flush()

            logger.info(f"Downloaded STIX data to temporary file: {temp_file.name}")

            # Initialize MITRE Attack Data with the downloaded file
            mad = MitreAttackData(temp_file.name)

        except Exception as e:
            logger.error(f"Failed to download STIX data: {e}")
            raise

    # Get all techniques (which includes attack patterns)
    logger.info("Retrieving techniques and sub-techniques...")
    techniques = mad.get_techniques()

    logger.info(f"Found {len(techniques)} total techniques")

    # Remove revoked and deprecated objects using the instance method
    active_techniques = mad.remove_revoked_deprecated(techniques)

    logger.info(f"After filtering revoked/deprecated: {len(active_techniques)} techniques")

    records: list[MitreRecord] = []

    for technique in active_techniques:
        # Extract ATT&CK ID and URL from external references
        external_refs = technique.get("external_references", [])
        mitre_ref = next(
            (ref for ref in external_refs if ref.get("source_name") == "mitre-attack"),
            None
        )

        if not mitre_ref:
            logger.warning(f"No MITRE reference found for technique {technique.get('id', 'unknown')}")
            continue

        attack_id = mitre_ref.get("external_id")
        if not attack_id:
            logger.warning(f"No ATT&CK ID found for technique {technique.get('id', 'unknown')}")
            continue

        url = mitre_ref.get("url")
        name = technique.get("name", "").strip()
        description = technique.get("description", "").strip()
        stix_id = technique.get("id", "")

        if not name or not description:
            logger.warning(f"Missing name or description for {attack_id}")
            continue

        record = MitreRecord(
            id=attack_id,
            title=name,
            description=description,
            url=url,
            stix_id=stix_id
        )

        records.append(record)

    logger.info(f"Successfully extracted {len(records)} MITRE ATT&CK records")

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
    help="Output JSONL file path (default: data/raw/mitre.jsonl)"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
def main(dry_run: bool, output: Path | None, log_level: str) -> None:
    """Ingest MITRE ATT&CK Enterprise data."""

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        # Load MITRE data
        records = load_enterprise_objects()

        # Print summary
        click.echo("\n📊 MITRE ATT&CK Ingestion Summary:")
        click.echo(f"   • Total records extracted: {len(records)}")
        click.echo("   • Source: MITRE ATT&CK Enterprise")

        if records:
            # Show sample of extracted IDs
            sample_ids = [r["id"] for r in records[:10]]
            click.echo(f"   • Sample IDs: {', '.join(sample_ids)}")
            if len(records) > 10:
                click.echo(f"     ... and {len(records) - 10} more")

        if not dry_run:
            # Determine output path
            if output is None:
                output = Path("data/raw/mitre.jsonl")

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
        logger.error(f"Failed to ingest MITRE data: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
