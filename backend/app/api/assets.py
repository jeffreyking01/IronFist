from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timezone
import uuid
import re

from app.db.session import get_db
from app.models.models import Asset, Vulnerability, Criticality, VulnStatus, Severity
from app.auth.dependencies import require_auth
from app.core.config import get_settings
from pydantic import BaseModel

router   = APIRouter(prefix="/api/assets", tags=["assets"])
settings = get_settings()


# ── Schemas ────────────────────────────────────────────────────────────────────
class AssetIngest(BaseModel):
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

class AssetUpdate(BaseModel):
    """Fields editable by analysts in the UI."""
    system_owner:   Optional[str] = None
    fisma_boundary: Optional[str] = None
    criticality:    Optional[str] = None
    hostname:       Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────
@router.get("/")
async def list_assets(
    boundary:    Optional[str] = Query(None),
    criticality: Optional[str] = Query(None),
    stale_only:  bool = Query(False),
    search:      Optional[str] = Query(None),
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
    if search:
        q = q.where(
            Asset.hostname.ilike(f"%{search}%") |
            Asset.ip_address.ilike(f"%{search}%") |
            Asset.fqdn.ilike(f"%{search}%")
        )

    total  = await db.execute(select(func.count()).select_from(q.subquery()))
    result = await db.execute(q.offset(offset).limit(limit).order_by(Asset.hostname))
    assets = result.scalars().all()

    return {
        "total":  total.scalar(),
        "offset": offset,
        "limit":  limit,
        "items":  [_asset_to_dict(a) for a in assets],
    }


@router.get("/stats/boundaries")
async def boundary_stats(
    db:   AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    result = await db.execute(
        select(Asset.fisma_boundary, func.count())
        .group_by(Asset.fisma_boundary)
        .order_by(func.count().desc())
    )
    return [{"boundary": row[0] or "Unassigned", "count": row[1]} for row in result]


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

    # Vuln summary counts
    vuln_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    kev_count   = 0
    for v in asset.vulnerabilities:
        if v.status == VulnStatus.OPEN:
            vuln_counts[v.severity.value] = vuln_counts.get(v.severity.value, 0) + 1
            if v.kev_member:
                kev_count += 1

    d = _asset_to_dict(asset)
    d["vuln_summary"] = {**vuln_counts, "kev": kev_count}
    d["vulnerabilities"] = [_vuln_brief(v) for v in asset.vulnerabilities if v.status == VulnStatus.OPEN]
    return d


@router.patch("/{asset_id}")
async def update_asset(
    asset_id: uuid.UUID,
    payload:  AssetUpdate,
    db:       AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    """Update analyst-managed fields: owner, boundary, criticality."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset  = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if payload.system_owner   is not None: asset.system_owner   = payload.system_owner
    if payload.fisma_boundary is not None: asset.fisma_boundary = payload.fisma_boundary
    if payload.hostname       is not None: asset.hostname       = payload.hostname
    if payload.criticality    is not None:
        asset.criticality = payload.criticality.upper()

    await db.commit()
    return _asset_to_dict(asset)


@router.post("/ingest")
async def ingest_asset(
    payload: AssetIngest,
    db:      AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Asset).where(Asset.ip_address == payload.ip_address)
    )
    asset = result.scalar_one_or_none()
    now   = datetime.now(timezone.utc)

    if asset:
        asset.hostname       = payload.hostname or asset.hostname
        asset.fqdn           = payload.fqdn or asset.fqdn
        asset.os_name        = payload.os_name or asset.os_name
        asset.os_version     = payload.os_version or asset.os_version
        # Don't overwrite manually-set owner/boundary from agent
        if payload.system_owner:   asset.system_owner   = payload.system_owner
        if payload.fisma_boundary: asset.fisma_boundary = payload.fisma_boundary
        asset.criticality    = payload.criticality or asset.criticality
        asset.tags           = payload.tags or asset.tags
        asset.last_seen      = now
        asset.is_stale       = False
        asset.agent_version  = payload.agent_version
        asset.raw_data       = payload.raw_data
        action = "updated"
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
        action = "created"

    await db.commit()
    return {"status": "ok", "asset_id": str(asset.id), "action": action}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _asset_to_dict(asset: Asset) -> dict:
    tags = asset.tags or {}
    return {
        "id":             str(asset.id),
        "ip_address":     asset.ip_address,
        "hostname":       asset.hostname,
        "fqdn":           asset.fqdn,
        "os_name":        asset.os_name,
        "os_version":     asset.os_version,
        "os_pretty":      _pretty_os(asset.os_name, asset.os_version),
        "system_owner":   asset.system_owner,
        "fisma_boundary": asset.fisma_boundary,
        "criticality":    asset.criticality,
        "tags":           tags,
        "hardware": {
            "manufacturer":          tags.get("manufacturer"),
            "model":                 tags.get("model"),
            "serial_number":         tags.get("serial_number"),
            "cpu_model":             tags.get("cpu_model"),
            "cpu_cores_logical":     tags.get("cpu_cores_logical"),
            "ram_gb":                tags.get("ram_gb"),
            "architecture":          tags.get("architecture"),
            "bios_version":          tags.get("bios_version"),
            "is_virtual":            tags.get("is_virtual"),
            "virtualization_platform": tags.get("virtualization_platform"),
        },
        "software": {
            "package_count":      tags.get("package_count", 0),
            "eol_package_count":  tags.get("eol_package_count", 0),
            "eol_packages":       tags.get("eol_packages", []),
            "cpe_matched_count":  tags.get("cpe_matched_count", 0),
        },
        "network_interfaces": _clean_interfaces(tags.get("network_interfaces", [])),
        "first_seen":     asset.first_seen.isoformat() if asset.first_seen else None,
        "last_seen":      asset.last_seen.isoformat()  if asset.last_seen  else None,
        "collected_at":   tags.get("collected_at"),
        "agent_version":  asset.agent_version,
        "is_stale":       asset.is_stale,
    }


def _vuln_brief(v: Vulnerability) -> dict:
    return {
        "id":         str(v.id),
        "cve_id":     v.cve_id,
        "severity":   v.severity,
        "cvss_score": v.cvss_score,
        "kev_member": v.kev_member,
        "status":     v.status,
    }


def _pretty_os(os_name: Optional[str], os_version: Optional[str]) -> str:
    """
    Convert raw OS fields into a human-readable string.
    Handles the ugly Ubuntu kernel build string from HostHarvest.
    """
    if not os_name:
        return "Unknown"

    # Linux — try to extract distro name from /etc/os-release style version strings
    if os_name == "Linux":
        if os_version:
            # e.g. "#14~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC..."
            ubuntu = re.search(r"(\d+\.\d+[\.\d]*)-Ubuntu", os_version)
            if ubuntu:
                return f"Ubuntu {ubuntu.group(1)}"
            debian = re.search(r"Debian", os_version, re.IGNORECASE)
            if debian:
                return f"Debian Linux"
            # Generic kernel version fallback
            kernel = re.search(r"(\d+\.\d+\.\d+)", os_version)
            if kernel:
                return f"Linux {kernel.group(1)}"
        return "Linux"

    # Windows
    if os_name == "Windows":
        if os_version:
            win11 = re.search(r"10\.0\.2[2-9]\d{3}", os_version)
            win10 = re.search(r"10\.0\.1\d{4}", os_version)
            if win11: return "Windows 11"
            if win10: return "Windows 10"
        return f"Windows {os_version or ''}".strip()

    # macOS
    if os_name == "Darwin":
        if os_version:
            ver = re.search(r"(\d+\.\d+)", os_version)
            if ver:
                return f"macOS {ver.group(1)}"
        return "macOS"

    return f"{os_name} {os_version or ''}".strip()


# Docker bridges, veth pairs, loopback — not useful in the UI
_SKIP_IFACE_PREFIXES = ("veth", "br-", "docker", "lo")

def _clean_interfaces(interfaces: list) -> list:
    """Filter out Docker/loopback interfaces, keep real ones."""
    return [
        iface for iface in interfaces
        if not any(iface.get("name", "").startswith(p) for p in _SKIP_IFACE_PREFIXES)
    ]
