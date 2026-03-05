from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
import uuid

from app.db.session import get_db
from app.models.models import Vulnerability, Asset, VulnSource, Severity, VulnStatus
from app.auth.dependencies import require_auth

router = APIRouter(prefix="/api/vulnerabilities", tags=["vulnerabilities"])


@router.get("/")
async def list_vulnerabilities(
    severity:   Optional[str]  = Query(None),
    kev_only:   bool           = Query(False),
    overdue:    bool           = Query(False),
    boundary:   Optional[str]  = Query(None),
    status:     Optional[str]  = Query("OPEN"),
    limit:      int            = Query(100, le=1000),
    offset:     int            = Query(0),
    db:         AsyncSession   = Depends(get_db),
    user = Depends(require_auth),
):
    q = select(Vulnerability).join(Asset)

    if severity:
        q = q.where(Vulnerability.severity == severity.upper())
    if kev_only:
        q = q.where(Vulnerability.kev_member == True)
    if overdue:
        q = q.where(
            and_(Vulnerability.kev_member == True, Vulnerability.kev_due_date < func.now())
        )
    if boundary:
        q = q.where(Asset.fisma_boundary == boundary)
    if status:
        q = q.where(Vulnerability.status == status.upper())

    total  = await db.execute(select(func.count()).select_from(q.subquery()))
    result = await db.execute(
        q.offset(offset).limit(limit)
        .order_by(Vulnerability.cvss_score.desc().nullslast())
    )
    vulns = result.scalars().all()

    return {
        "total":  total.scalar(),
        "offset": offset,
        "limit":  limit,
        "items":  [_vuln_to_dict(v) for v in vulns],
    }


@router.get("/kev")
async def kev_watch(
    db:   AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    """KEV watch — all open KEV findings sorted by due date."""
    result = await db.execute(
        select(Vulnerability, Asset)
        .join(Asset)
        .where(
            and_(Vulnerability.kev_member == True, Vulnerability.status == VulnStatus.OPEN)
        )
        .order_by(Vulnerability.kev_due_date.asc().nullslast())
    )
    rows = result.all()
    return [
        {**_vuln_to_dict(v), "asset_hostname": a.hostname, "asset_boundary": a.fisma_boundary}
        for v, a in rows
    ]


@router.get("/{vuln_id}")
async def get_vulnerability(
    vuln_id: uuid.UUID,
    db:      AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.id == vuln_id)
    )
    vuln = result.scalar_one_or_none()
    if not vuln:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    # Get sources
    sources_result = await db.execute(
        select(VulnSource).where(VulnSource.vuln_id == vuln_id)
    )
    sources = sources_result.scalars().all()

    d = _vuln_to_dict(vuln)
    d["sources"] = [{"name": s.source_name, "ingested_at": s.ingested_at.isoformat()} for s in sources]
    return d


def _vuln_to_dict(v: Vulnerability) -> dict:
    return {
        "id":            str(v.id),
        "cve_id":        v.cve_id,
        "asset_id":      str(v.asset_id),
        "severity":      v.severity,
        "cvss_score":    v.cvss_score,
        "description":   v.description,
        "cwe_id":        v.cwe_id,
        "kev_member":    v.kev_member,
        "kev_due_date":  v.kev_due_date.isoformat() if v.kev_due_date else None,
        "status":        v.status,
        "first_detected": v.first_detected.isoformat() if v.first_detected else None,
        "last_seen":     v.last_seen.isoformat() if v.last_seen else None,
    }
