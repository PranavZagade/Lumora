"""
Lumora Backend API

A story-first data understanding API.
All analysis is deterministic. AI only narrates.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from routers import upload, health, insights, question_suggestions, chat
from services.storage import storage


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

# CORS configuration for frontend
# Allow multiple ports for development (Next.js increments port if 3000 is in use)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
    ],
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

