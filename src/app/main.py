"""FastAPI application with simple dependency injection."""

import json
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Body, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.dependencies import get_app_dependencies, get_agent_dependencies
from app.models import AnalysisRequest, AnalyzedVulnerability
from app.orchestrator import VulnerabilityAnalysisOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    try:
        # Startup: Initialize dependencies
        logger.info("Initializing application dependencies...")
        settings = get_settings()
        app_deps = await get_app_dependencies()
        await app_deps.initialize(settings)
        logger.info("Application dependencies initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize dependencies: {e}")
        raise
    finally:
        # Shutdown: Cleanup dependencies
        logger.info("Cleaning up application dependencies...")
        app_deps = await get_app_dependencies()
        await app_deps.cleanup()
        logger.info("Application dependencies cleaned up")


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
    # Try to get dependencies to verify they're initialized
    try:
        app_deps = await get_app_dependencies()
        if app_deps._initialized:
            return {"status": "healthy", "dependencies": "ready"}
    except Exception:
        pass

    raise HTTPException(status_code=503, detail="Dependencies not initialized")


@app.post("/analyze", response_model=AnalyzedVulnerability)
async def analyze_vulnerability(
    request: AnalysisRequest,
    agent_deps=Depends(get_agent_dependencies)
) -> AnalyzedVulnerability:
    """Analyze a vulnerability using the AI agent."""
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
async def chat_with_agent(
    message: str,
    agent_deps=Depends(get_agent_dependencies)
) -> dict:
    """Chat interface for conversational vulnerability analysis."""
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


@app.post("/analyze-report", response_model=List[AnalyzedVulnerability])
async def analyze_report(
    report_content: str = Body(..., description="Raw scan report content"),
    max_concurrent: int = Query(3, description="Maximum concurrent analyses", ge=1, le=10),
    timeout_per_analysis: float = Query(30.0, description="Timeout per analysis in seconds", ge=5.0, le=120.0),
    agent_deps=Depends(get_agent_dependencies)
):
    """Analyze a complete scan report and extract all vulnerability findings."""
    logger.info("Scan report analysis endpoint called")

    try:
        # Try to parse as JSON if it looks like JSON
        try:
            if report_content.strip().startswith('{'):
                report_data = json.loads(report_content)
            else:
                report_data = report_content
        except json.JSONDecodeError:
            report_data = report_content

        orchestrator = VulnerabilityAnalysisOrchestrator(agent_deps)
        results = await orchestrator.analyze_scan_report(
            report_data,
            max_concurrent=max_concurrent,
            timeout_per_analysis=timeout_per_analysis
        )

        logger.info(f"Scan report analysis completed: {len(results)} vulnerabilities analyzed")
        return results

    except Exception as e:
        logger.error(f"Scan report analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)