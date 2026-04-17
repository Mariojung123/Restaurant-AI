"""
FastAPI entry point for Restaurant AI Partner backend.
Loads environment, sets up CORS, registers routers, and exposes health check.
"""

from dotenv import load_dotenv

# Load environment variables at the very top before any other imports that may need them
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, inventory, vision, recipe


app = FastAPI(
    title="Restaurant AI Partner",
    description="Natural language AI operations partner for small Canadian restaurants.",
    version="0.1.0",
)

# CORS configuration for local Vite dev server and production frontend
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

extra_origin = os.getenv("FRONTEND_ORIGIN")
if extra_origin:
    allowed_origins.append(extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register feature routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(vision.router, prefix="/api/vision", tags=["vision"])
app.include_router(recipe.router, prefix="/api/recipe", tags=["recipe"])


@app.get("/")
def read_root():
    """Root endpoint returning a friendly service banner."""
    return {
        "service": "Restaurant AI Partner",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint used by deployment platforms and monitors."""
    return {"status": "healthy"}
