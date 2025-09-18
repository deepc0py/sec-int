"""Basic smoke test for the hello module."""

from app.hello import hello


def test_hello():
    """Test that hello function returns expected greeting."""
    result = hello()
    assert "Hello from the Vulnerability Analysis RAG Bot!" in result
    assert isinstance(result, str)
