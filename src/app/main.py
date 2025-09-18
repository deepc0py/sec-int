"""FastAPI application for the Vulnerability Analysis RAG Bot.

This module provides the web API interface for vulnerability analysis,
allowing users to submit vulnerability IDs and receive comprehensive analysis.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent import create_agent_dependencies, cleanup_agent_dependencies, get_agent
from app.models import AnalysisRequest, AnalyzedVulnerability
from app.orchestrator import VulnerabilityAnalysisOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dependencies - will be initialized in lifespan
agent_deps = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global agent_deps

    try:
        # Startup: Initialize agent dependencies
        logger.info("Initializing agent dependencies...")
        agent_deps = await create_agent_dependencies()
        logger.info("Agent dependencies initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize agent dependencies: {e}")
        raise
    finally:
        # Shutdown: Cleanup agent dependencies
        if agent_deps:
            logger.info("Cleaning up agent dependencies...")
            await cleanup_agent_dependencies(agent_deps)
            logger.info("Agent dependencies cleaned up")


# Create FastAPI application
app = FastAPI(
    title="Vulnerability Analysis RAG Bot",
    description="AI-powered vulnerability analysis using retrieval-augmented generation",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Vulnerability Analysis RAG Bot API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if agent_deps is None:
        raise HTTPException(status_code=503, detail="Agent dependencies not initialized")

    return {"status": "healthy", "dependencies": "ready"}


@app.post("/analyze", response_model=AnalyzedVulnerability)
async def analyze_vulnerability(request: AnalysisRequest) -> AnalyzedVulnerability:
    """Analyze a vulnerability using the AI agent.

    This endpoint accepts vulnerability analysis requests and returns comprehensive
    analysis using the RAG-powered AI agent.
    """
    if agent_deps is None:
        raise HTTPException(status_code=503, detail="Agent dependencies not initialized")

    # For now, handle single vulnerability ID analysis
    if not request.vulnerability_ids:
        raise HTTPException(status_code=400, detail="No vulnerability IDs provided")

    if len(request.vulnerability_ids) > 1:
        raise HTTPException(status_code=400, detail="Multiple vulnerability analysis not yet supported")

    vulnerability_id = request.vulnerability_ids[0]

    try:
        # Use orchestrator for structured analysis
        orchestrator = VulnerabilityAnalysisOrchestrator(agent_deps)
        result = await orchestrator.analyze_vulnerability(vulnerability_id)

        logger.info(f"Successfully analyzed vulnerability {vulnerability_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to analyze vulnerability {vulnerability_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/chat")
async def chat_with_agent(message: str) -> dict:
    """Chat interface for conversational vulnerability analysis.

    This endpoint provides a more flexible chat interface where users can
    have conversations with the vulnerability analysis agent.
    """
    if agent_deps is None:
        raise HTTPException(status_code=503, detail="Agent dependencies not initialized")

    if not message.strip():
        raise HTTPException(status_code=400, detail="Empty message provided")

    try:
        # Use orchestrator for chat analysis
        orchestrator = VulnerabilityAnalysisOrchestrator(agent_deps)
        result = await orchestrator.chat_analysis(message)

        logger.info(f"Chat response generated for message: {message[:50]}...")
        return {
            "message": message,
            "response": result,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Failed to process chat message: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)