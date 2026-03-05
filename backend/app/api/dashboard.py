from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.session import get_db
from app.models.models import Vulnerability, Asset, Connector, Severity, VulnStatus
from app.auth.dependencies import require_auth

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db:   AsyncSession = Depends(get_db),
    user = Depends(require_auth),
):
    """Top-line KPIs for the main dashboard."""

    # Vulnerability counts by severity
    sev_counts = await db.execute(
        select(Vulnerability.severity, func.count())
        .where(Vulnerability.status == VulnStatus.OPEN)
        .group_by(Vulnerability.severity)
    )
    by_severity = {row[0]: row[1] for row in sev_counts}

    # KEV counts
    kev_total = await db.execute(
        select(func.count()).where(
            and_(Vulnerability.kev_member == True, Vulnerability.status == VulnStatus.OPEN)
        )
    )
    kev_overdue = await db.execute(
        select(func.count()).where(
            and_(
                Vulnerability.kev_member == True,
                Vulnerability.status == VulnStatus.OPEN,
                Vulnerability.kev_due_date < func.now(),
            )
        )
    )

    # Asset counts
    asset_total  = await db.execute(select(func.count()).select_from(Asset))
    stale_assets = await db.execute(select(func.count()).where(Asset.is_stale == True))

    # Active connectors
    active_connectors = await db.execute(
        select(func.count()).where(Connector.enabled == True)
    )

    return {
        "vulnerabilities": {
            "critical": by_severity.get(Severity.CRITICAL, 0),
            "high":     by_severity.get(Severity.HIGH, 0),
            "medium":   by_severity.get(Severity.MEDIUM, 0),
            "low":      by_severity.get(Severity.LOW, 0),
        },
        "kev": {
            "total":   kev_total.scalar(),
            "overdue": kev_overdue.scalar(),
        },
        "assets": {
            "total":  asset_total.scalar(),
            "stale":  stale_assets.scalar(),
        },
        "connectors": {
            "active": active_connectors.scalar(),
        },
    }
