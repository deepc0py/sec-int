"""Basic tests for OWASP Top 10 data ingestion."""

from app.ingestion.ingest_owasp import OwaspRecord, extract_title_from_url


class TestOwaspRecord:
    """Test OwaspRecord dataclass."""

    def test_owasp_record_creation(self):
        """Test creating an OwaspRecord with all fields."""
        record = OwaspRecord(
            id="A01:2021",
            title="Broken Access Control",
            description="Access control enforces policy...",
            url="https://owasp.org/Top10/A01_2021-Broken_Access_Control/"
        )

        assert record.source == "owasp"
        assert record.id == "A01:2021"
        assert record.title == "Broken Access Control"
        assert record.description.startswith("Access control")
        assert record.url == "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"

    def test_owasp_record_defaults(self):
        """Test OwaspRecord with default values."""
        record = OwaspRecord()

        assert record.source == "owasp"
        assert record.id == ""
        assert record.title == ""
        assert record.description == ""
        assert record.url is None


class TestTitleExtraction:
    """Test title extraction from URLs."""

    def test_extract_title_from_url(self):
        """Test extracting vulnerability title from OWASP URL."""
        url = "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"
        title = extract_title_from_url(url)
        assert title == "Broken Access Control"

    def test_extract_title_with_underscores(self):
        """Test extracting title with underscores."""
        url = "https://owasp.org/Top10/A05_2021-Security_Misconfiguration/"
        title = extract_title_from_url(url)
        assert title == "Security Misconfiguration"

    def test_extract_title_with_parentheses(self):
        """Test extracting title with URL-encoded parentheses."""
        url = "https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/"
        title = extract_title_from_url(url)
        assert title == "Server Side Request Forgery (SSRF)"

    def test_extract_title_invalid_url(self):
        """Test extracting title from invalid URL."""
        url = "https://example.com/invalid"
        title = extract_title_from_url(url)
        assert title == ""
