"""
IronFist — FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.db.session import engine, Base, AsyncSessionLocal
from app.api import health, assets, vulnerabilities, connectors, dashboard
from app.auth.auth import router as auth_router
from app.auth.dependencies import require_auth
from app.connectors.scheduler import start_scheduler, stop_scheduler
from app.connectors.kev import KEVConnector
from app.connectors.nvd import NVDConnector
from app.connectors.tenable_dummy import TenableDummyConnector

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting IronFist %s in %s mode", settings.app_version, settings.environment)
    logger.info("Auth mode: %s", settings.auth_mode)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready")

    start_scheduler()

    logger.info("Running initial connector sync on startup...")
    async with AsyncSessionLocal() as db:
        tenable = TenableDummyConnector(db, seed=42)
        await tenable.run()

    async with AsyncSessionLocal() as db:
        kev = KEVConnector(db)
        await kev.run()

    yield

    stop_scheduler()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(health.router)
app.include_router(assets.router)
app.include_router(vulnerabilities.router)
app.include_router(connectors.router)
app.include_router(dashboard.router)


@app.post("/api/sync/kev", tags=["sync"])
async def sync_kev(background_tasks: BackgroundTasks, user=Depends(require_auth)):
    async def _run():
        async with AsyncSessionLocal() as db:
            await KEVConnector(db).run()
        async with AsyncSessionLocal() as db:
            await NVDConnector(db).run()
    background_tasks.add_task(_run)
    return {"status": "queued", "connector": "kev"}


@app.post("/api/sync/tenable", tags=["sync"])
async def sync_tenable(background_tasks: BackgroundTasks, user=Depends(require_auth)):
    async def _run():
        async with AsyncSessionLocal() as db:
            await TenableDummyConnector(db).run()
    background_tasks.add_task(_run)
    return {"status": "queued", "connector": "tenable-dummy"}


@app.post("/api/sync/all", tags=["sync"])
async def sync_all(background_tasks: BackgroundTasks, user=Depends(require_auth)):
    async def _run():
        async with AsyncSessionLocal() as db:
            await TenableDummyConnector(db).run()
        async with AsyncSessionLocal() as db:
            await KEVConnector(db).run()
        async with AsyncSessionLocal() as db:
            await NVDConnector(db).run()
    background_tasks.add_task(_run)
    return {"status": "queued", "connectors": ["tenable-dummy", "kev", "nvd"]}


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse("static/index.html")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
        }
    }
    for path in schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi
