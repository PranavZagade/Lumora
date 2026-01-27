"""
Lumora Backend API

A story-first data understanding API.
All analysis is deterministic. AI only narrates.
"""

import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import upload, health, insights, question_suggestions, chat, mappings
from services.storage import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Clean up expired sessions
    removed = storage.cleanup_expired()
    if removed > 0:
        print(f"Cleaned up {removed} expired sessions")
    
    yield
    
    # Shutdown: Nothing to do for now
    pass


app = FastAPI(
    title="Lumora API",
    description="Story-first data understanding API. Rules decide, AI explains.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production, restrict later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(health.router)
app.include_router(insights.router)
app.include_router(question_suggestions.router)
app.include_router(chat.router)
app.include_router(mappings.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "Lumora API",
        "status": "healthy",
        "version": "0.1.0",
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "storage": "ok",
            "analyzer": "ok",
        }
    }

