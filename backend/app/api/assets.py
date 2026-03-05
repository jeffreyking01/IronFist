from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.db.session import get_db
from app.models.models import Asset, Criticality
from app.auth.dependencies import require_auth
from app.core.config import get_settings
from pydantic import BaseModel

router   = APIRouter(prefix="/api/assets", tags=["assets"])
settings = get_settings()


# ── Schemas ────────────────────────────────────────────────────────────────────
class AssetIngest(BaseModel):
    """Schema for CMDB agent POST /api/assets/ingest"""
    ip_address:     str
    hostname:       Optional[str] = None
    fqdn:           Optional[str] = None
    os_name:        Optional[str] = None
    os_version:     Optional[str] = None
    system_owner:   Optional[str] = None
    fisma_boundary: Optional[str] = None
    criticality:    Optional[str] = "MEDIUM"
    tags:           Optional[dict] = {}
    agent_version:  Optional[str] = None
    raw_data:       Optional[dict] = {}


# ── Routes ─────────────────────────────────────────────────────────────────────
@router.get("/")
async def list_assets(
    boundary:    Optional[str] = Query(None),
    criticality: Optional[str] = Query(None),
    stale_only:  bool = Query(False),
    limit:       int  = Query(100, le=1000),
    offset:      int  = Query(0),
    db:          AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    q = select(Asset)
    if boundary:
        q = q.where(Asset.fisma_boundary == boundary)
    if criticality:
        q = q.where(Asset.criticality == criticality.upper())
    if stale_only:
        q = q.where(Asset.is_stale == True)

    total  = await db.execute(select(func.count()).select_from(q.subquery()))
    result = await db.execute(q.offset(offset).limit(limit).order_by(Asset.hostname))
    assets = result.scalars().all()

    return {
        "total":  total.scalar(),
        "offset": offset,
        "limit":  limit,
        "items":  [_asset_to_dict(a) for a in assets],
    }


@router.get("/{asset_id}")
async def get_asset(
    asset_id: uuid.UUID,
    db:       AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    result = await db.execute(
        select(Asset)
        .options(selectinload(Asset.vulnerabilities))
        .where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_to_dict(asset, include_vulns=True)


@router.post("/ingest")
async def ingest_asset(
    payload: AssetIngest,
    db:      AsyncSession = Depends(get_db),
    # CMDB agent authenticates with bearer token, not user session
):
    """
    CMDB agent endpoint — upserts asset records.
    Authenticated via bearer token in Authorization header.
    (Token validation added in Phase 2 — using open endpoint for initial dev)
    """
    # Upsert: update if IP exists, insert if not
    result = await db.execute(
        select(Asset).where(Asset.ip_address == payload.ip_address)
    )
    asset = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if asset:
        # Update existing
        asset.hostname       = payload.hostname or asset.hostname
        asset.fqdn           = payload.fqdn or asset.fqdn
        asset.os_name        = payload.os_name or asset.os_name
        asset.os_version     = payload.os_version or asset.os_version
        asset.system_owner   = payload.system_owner or asset.system_owner
        asset.fisma_boundary = payload.fisma_boundary or asset.fisma_boundary
        asset.criticality    = payload.criticality or asset.criticality
        asset.tags           = payload.tags or asset.tags
        asset.last_seen      = now
        asset.is_stale       = False
        asset.agent_version  = payload.agent_version
        asset.raw_data       = payload.raw_data
    else:
        asset = Asset(
            ip_address     = payload.ip_address,
            hostname       = payload.hostname,
            fqdn           = payload.fqdn,
            os_name        = payload.os_name,
            os_version     = payload.os_version,
            system_owner   = payload.system_owner,
            fisma_boundary = payload.fisma_boundary,
            criticality    = payload.criticality or Criticality.MEDIUM,
            tags           = payload.tags or {},
            last_seen      = now,
            is_stale       = False,
            agent_version  = payload.agent_version,
            raw_data       = payload.raw_data or {},
        )
        db.add(asset)

    await db.commit()
    return {"status": "ok", "asset_id": str(asset.id), "action": "updated" if result else "created"}


@router.get("/stats/boundaries")
async def boundary_stats(
    db:   AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    """Asset count per FISMA boundary."""
    result = await db.execute(
        select(Asset.fisma_boundary, func.count())
        .group_by(Asset.fisma_boundary)
        .order_by(func.count().desc())
    )
    return [{"boundary": row[0] or "Unassigned", "count": row[1]} for row in result]


# ── Helpers ────────────────────────────────────────────────────────────────────
def _asset_to_dict(asset: Asset, include_vulns: bool = False) -> dict:
    d = {
        "id":            str(asset.id),
        "ip_address":    asset.ip_address,
        "hostname":      asset.hostname,
        "fqdn":          asset.fqdn,
        "os_name":       asset.os_name,
        "os_version":    asset.os_version,
        "system_owner":  asset.system_owner,
        "fisma_boundary": asset.fisma_boundary,
        "criticality":   asset.criticality,
        "tags":          asset.tags,
        "first_seen":    asset.first_seen.isoformat() if asset.first_seen else None,
        "last_seen":     asset.last_seen.isoformat() if asset.last_seen else None,
        "is_stale":      asset.is_stale,
    }
    if include_vulns:
        d["vulnerabilities"] = [str(v.id) for v in asset.vulnerabilities]
    return d
