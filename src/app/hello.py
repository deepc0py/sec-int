"""Simple hello world module for smoke testing the project setup."""

def hello() -> str:
    """Return a greeting message."""
    return "Hello from the Vulnerability Analysis RAG Bot!"

def main() -> None:
    """Main entry point for the hello module."""
    print(hello())

if __name__ == "__main__":
    main()
