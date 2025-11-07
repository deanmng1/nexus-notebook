"""
PDF Comparison Service - Main Application

FastAPI application for comparing PDF documents with LLM-powered analysis.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.api_title,
        version=settings.api_version,
        debug=settings.debug
    )

    yield

    # Shutdown
    logger.info("application_shutting_down")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
    A scalable service for comparing PDF documents with AI-powered analysis.

    ## Features

    * **PDF to Markdown Conversion**: High-quality conversion preserving layout, tables, and images
    * **Intelligent Diff Analysis**: Identifies and categorizes all differences
    * **LLM Integration**: AI-powered analysis to identify important changes
    * **Citations & Proof**: Every difference includes citations and proof
    * **Async Processing**: Queue-based processing for scalability
    * **Tax Document Focused**: Optimized for tax and legal document comparison

    ## Workflow

    1. **Submit**: POST two PDFs to `/api/v1/compare`
    2. **Poll**: Check status at `/api/v1/jobs/{job_id}`
    3. **Retrieve**: Get results from `/api/v1/results/{job_id}`
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.debug
)

# Add CORS middleware
if settings.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("cors_enabled", allowed_origins=settings.allowed_origins)

# Include API routes
app.include_router(
    api_router,
    prefix="/api/v1",
    tags=["PDF Comparison"]
)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
