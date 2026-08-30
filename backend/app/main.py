"""ControlPlane.ai — Enterprise AI Governance & Runtime Risk Control Plane.

FastAPI application: middleware-style analysis pipeline + governance APIs.
Run with:  uvicorn app.main:app --reload --port 8000  (from backend/)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api import analytics, interactions, misc, policies, reviews
from .database import models  # noqa: F401 (register models)
from .database.seed import seed_all
from .database.session import Base, SessionLocal, engine
from .rag.kb import get_kb


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    get_kb()  # build the retrieval index once
    db = SessionLocal()
    try:
        await seed_all(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="ControlPlane.ai",
    description="Enterprise AI governance and runtime risk control plane (Round 2 prototype).",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactions.router)
app.include_router(reviews.router)
app.include_router(policies.router)
app.include_router(analytics.router)
app.include_router(misc.router)
