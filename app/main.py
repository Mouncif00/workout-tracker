from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core import scheduler as scheduler_module
from app.core.mongodb import close_mongo
import app.models

from app.routers import auth, exercises, workouts, dashboard, comments, reports

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    from app.core.database import SessionLocal
    from app.models.exercise import Exercise
    db = SessionLocal()
    try:
        if db.query(Exercise).count() == 0:
            from scripts.seed_exercises import seed
            seed()
    finally:
        db.close()

    scheduler_module.start_scheduler()
    yield
    scheduler_module.stop_scheduler()
    await close_mongo()


app = FastAPI(
    title="Workout Tracker API",
    description=(
        "Backend API for tracking workouts, exercises, and progress. "
        "Uses PostgreSQL (structured data), MongoDB (comments & logs), "
        "Redis (caching + JWT blacklist), and free AI-powered weekly summaries."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mouncif00.github.io",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(exercises.router, prefix=API_PREFIX)
app.include_router(workouts.router, prefix=API_PREFIX)
app.include_router(comments.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Workout Tracker API v2 — All Phases Complete"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}