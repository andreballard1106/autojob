"""
Job Application System - Main FastAPI Application
"""

import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import setup_logging, get_logger

# Configure logging FIRST before any other imports that might use logging
setup_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info("Starting Job Application System...")

    # Ensure storage directories exist
    storage_dirs = ["resumes", "cover_letters", "screenshots", "logs", "work_documents"]
    for subdir in storage_dirs:
        path = os.path.join(settings.storage_path, subdir)
        os.makedirs(path, exist_ok=True)

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.error(traceback.format_exc())
        raise

    logger.info(f"Dashboard: http://localhost:{settings.api_port}")
    logger.info(f"API Docs: http://localhost:{settings.api_port}/docs")

    yield

    # Graceful shutdown
    logger.info("Shutting down...")
    
    # Cancel background tasks
    try:
        from automation.task_tracker import task_tracker
        cancelled = await task_tracker.cancel_all_tasks()
        if cancelled > 0:
            logger.info(f"Cancelled {cancelled} background task(s)")
    except Exception as e:
        logger.warning(f"Error cancelling tasks: {e}")
    
    # Shutdown orchestrator (closes all browsers)
    try:
        from automation.orchestrator_manager import shutdown_orchestrator, is_orchestrator_running
        if is_orchestrator_running():
            await shutdown_orchestrator()
            logger.info("Orchestrator shutdown complete")
    except Exception as e:
        logger.warning(f"Error shutting down orchestrator: {e}")
    
    # Flush pending application logs
    try:
        from automation.application_logger import application_logger
        flushed = await application_logger.flush_pending_logs()
        if flushed > 0:
            logger.info(f"Flushed {flushed} pending log(s)")
    except Exception as e:
        logger.warning(f"Error flushing logs: {e}")
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Job Application System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# HTTP Exception handler - logs 4xx and 5xx errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP exception handler that logs client and server errors.
    """
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    elif exc.status_code >= 400:
        logger.warning(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# Global exception handler - catches ALL unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs all unhandled errors to the terminal.
    """
    # Log the full error with traceback
    logger.error(f"Unhandled exception on {request.method} {request.url.path}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")
    
    # Also print to stdout to ensure visibility
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"UNHANDLED EXCEPTION: {type(exc).__name__}", file=sys.stderr)
    print(f"Path: {request.method} {request.url.path}", file=sys.stderr)
    print(f"Message: {str(exc)}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    
    # Return a proper error response
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "An unexpected error occurred",
            "type": type(exc).__name__ if settings.debug else None,
        }
    )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error logging middleware
class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log errors that occur during request processing."""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            
            # Log server errors (5xx)
            if response.status_code >= 500:
                logger.error(
                    f"Server error {response.status_code} on {request.method} {request.url.path}"
                )
            
            return response
        except Exception as e:
            # Log the error
            logger.error(f"Middleware caught error on {request.method} {request.url.path}")
            logger.error(f"Error: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise


app.add_middleware(ErrorLoggingMiddleware)

# Import routes
from app.api.routes import profiles, jobs, dashboard, applications, ai_settings
from app.api.routes.websocket import router as websocket_router

# Include API routers
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(ai_settings.router, prefix="/api/ai-settings", tags=["AI Settings"])
app.include_router(websocket_router)

# Mount storage
if os.path.exists(settings.storage_path):
    app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")

# Mount static files for testing
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy"}
