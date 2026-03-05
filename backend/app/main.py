"""
IronFist — FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.db.session import engine, Base
from app.api import health, assets, vulnerabilities, connectors, dashboard
from app.auth.auth import router as auth_router

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting IronFist %s in %s mode", settings.app_version, settings.environment)
    logger.info("Auth mode: %s", settings.auth_mode)

    # Create tables if they don't exist (Alembic handles migrations in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")

    yield

    logger.info("Shutting down IronFist")
    await engine.dispose()


app = FastAPI(
    title="IronFist",
    description="Federal Vulnerability Management Platform",
    version=settings.app_version,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# ── CORS (dev only — tighten in production) ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ─────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(health.router)
app.include_router(assets.router)
app.include_router(vulnerabilities.router)
app.include_router(connectors.router)
app.include_router(dashboard.router)

# ── Serve wireframe UI ─────────────────────────────────────────────────────────
# Serves the static HTML wireframe at the root URL.
# Replace with React build output when frontend is ready.
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse("static/index.html")
