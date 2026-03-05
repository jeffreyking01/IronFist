"""
IronFist Connector Scheduler
Runs connectors on their configured schedules using APScheduler.
Starts automatically with the FastAPI app via the lifespan hook.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.db.session import AsyncSessionLocal
from app.connectors.kev import KEVConnector
from app.connectors.nvd import NVDConnector
from app.connectors.tenable_dummy import TenableDummyConnector
from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def _run_kev():
    async with AsyncSessionLocal() as db:
        connector = KEVConnector(db)
        result    = await connector.run()
        logger.info("KEV scheduler result: %s", result)

        # After KEV runs, immediately run NVD to enrich any new matches
        nvd       = NVDConnector(db)
        nvd_result = await nvd.run()
        logger.info("NVD enrichment result: %s", nvd_result)


async def _run_tenable():
    async with AsyncSessionLocal() as db:
        connector = TenableDummyConnector(db)
        result    = await connector.run()
        logger.info("Tenable scheduler result: %s", result)


def start_scheduler():
    """Register all connector jobs and start the scheduler."""

    # KEV — every 6 hours
    scheduler.add_job(
        _run_kev,
        trigger   = IntervalTrigger(hours=settings.kev_sync_hours),
        id        = "kev-sync",
        name      = "CISA KEV Sync",
        replace_existing = True,
    )

    # Tenable dummy — every 24 hours
    scheduler.add_job(
        _run_tenable,
        trigger   = IntervalTrigger(hours=settings.nvd_sync_hours),
        id        = "tenable-sync",
        name      = "Tenable Scan Sync",
        replace_existing = True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started — KEV every %dh, Tenable every %dh",
        settings.kev_sync_hours,
        settings.nvd_sync_hours,
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
