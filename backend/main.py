"""
FastAPI entry point for Restaurant AI Partner backend.
Loads environment, sets up CORS, registers routers, and exposes health check.
"""

from dotenv import load_dotenv

# Load environment variables at the very top before any other imports that may need them
load_dotenv()

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, inventory, vision, recipe
from routers import invoice as invoice_router
from routers import receipt as receipt_router
from models.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Restaurant AI Partner",
    description="Natural language AI operations partner for small Canadian restaurants.",
    version="0.1.0",
    lifespan=lifespan,
)

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

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["inventory"])
app.include_router(vision.router, prefix="/api/vision", tags=["vision"])
app.include_router(invoice_router.router, prefix="/api/vision/invoice", tags=["invoice"])
app.include_router(receipt_router.router, prefix="/api/vision/receipt", tags=["receipt"])
app.include_router(recipe.router, prefix="/api/recipe", tags=["recipe"])


@app.get("/")
def read_root():
    return {
        "service": "Restaurant AI Partner",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
