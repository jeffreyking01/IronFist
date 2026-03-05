from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import get_settings

router   = APIRouter(prefix="/api", tags=["health"])
settings = get_settings()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint — used by ALB target group.
    Returns 200 when app and database are reachable.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status":      "ok" if db_status == "ok" else "degraded",
        "app":         settings.app_name,
        "version":     settings.app_version,
        "environment": settings.environment,
        "auth_mode":   settings.auth_mode,
        "database":    db_status,
    }
