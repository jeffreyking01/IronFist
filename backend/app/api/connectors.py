from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import Connector
from app.auth.dependencies import require_auth

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("/")
async def list_connectors(
    db:   AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    result = await db.execute(select(Connector).order_by(Connector.name))
    connectors = result.scalars().all()
    return [_connector_to_dict(c) for c in connectors]


@router.get("/{connector_id}/status")
async def connector_status(
    connector_id: str,
    db:   AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    import uuid
    result = await db.execute(
        select(Connector).where(Connector.id == uuid.UUID(connector_id))
    )
    connector = result.scalar_one_or_none()
    if not connector:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Connector not found")
    return _connector_to_dict(connector)


def _connector_to_dict(c: Connector) -> dict:
    return {
        "id":             str(c.id),
        "name":           c.name,
        "type":           c.connector_type,
        "status":         c.status,
        "enabled":        c.enabled,
        "tls_verified":   c.tls_verified,
        "schedule_hours": c.schedule_hours,
        "last_sync_at":   c.last_sync_at.isoformat() if c.last_sync_at else None,
        "last_sync_count": c.last_sync_count,
        "last_error":     c.last_error,
    }
