"""
Job Application System - Main FastAPI Application
"""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    print("Starting Job Application System...")

    # Ensure storage directories exist
    storage_dirs = ["resumes", "cover_letters", "screenshots", "logs", "work_documents"]
    for subdir in storage_dirs:
        path = os.path.join(settings.storage_path, subdir)
        os.makedirs(path, exist_ok=True)

    # Initialize database
    await init_db()
    print("Database initialized")

    print(f"Dashboard: http://localhost:{settings.api_port}")
    print(f"API Docs: http://localhost:{settings.api_port}/docs")

    yield

    print("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Job Application System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
