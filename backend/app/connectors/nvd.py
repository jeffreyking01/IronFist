"""
NVD / NIST Connector
Enriches existing CVE records with CVSS scores, descriptions, and CWE data.

Source:  https://services.nvd.nist.gov/rest/json/cves/2.0
Auth:    API key (free, register at https://nvd.nist.gov/developers/request-an-api-key)
TLS:     Native HTTPS
Schedule: Every 24 hours

Without an API key: 5 requests/30s (slow but works for dev)
With an API key:    50 requests/30s
"""

import asyncio
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import BaseConnector
from app.models.models import Vulnerability, Severity
from app.core.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

NVD_BASE_URL  = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RESULTS_PER_PAGE = 100


class NVDConnector(BaseConnector):
    name           = "nvd-nist"
    connector_type = "api"
    tls_verified   = True
    schedule_hours = 24

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.api_key = settings.nvd_api_key

    async def fetch(self) -> list[dict]:
        """
        Fetch NVD data only for CVEs we already have in the database.
        This is more efficient than pulling the entire NVD catalog.
        """
        # Get all unique CVE IDs we need to enrich
        result = await self.db.execute(
            select(Vulnerability.cve_id).distinct()
            .where(Vulnerability.cvss_score == None)  # noqa — only fetch unenriched
        )
        cve_ids = [row[0] for row in result]

        if not cve_ids:
            self.logger.info("No CVEs need NVD enrichment")
            return []

        self.logger.info("Fetching NVD data for %d CVEs", len(cve_ids))

        headers = {}
        if self.api_key:
            headers["apiKey"] = self.api_key

        enriched = []
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for i, cve_id in enumerate(cve_ids):
                try:
                    # NVD rate limit: sleep between requests
                    if i > 0:
                        await asyncio.sleep(0.6 if self.api_key else 6.0)

                    response = await client.get(
                        NVD_BASE_URL,
                        params={"cveId": cve_id},
                    )
                    response.raise_for_status()
                    data = response.json()
                    vulns = data.get("vulnerabilities", [])
                    if vulns:
                        enriched.append(vulns[0])
                        self.logger.debug("Fetched NVD data for %s", cve_id)

                except httpx.HTTPStatusError as e:
                    self.logger.warning("NVD HTTP error for %s: %s", cve_id, e)
                except Exception as e:
                    self.logger.warning("NVD fetch error for %s: %s", cve_id, e)

        self.logger.info("Fetched %d NVD records", len(enriched))
        return enriched

    async def normalize(self, raw: list[dict]) -> list[dict]:
        """Extract CVSS score, description, and CWE from NVD response."""
        records = []
        for item in raw:
            cve = item.get("cve", {})
            cve_id = cve.get("id", "")

            # Description (English preferred)
            description = ""
            for desc in cve.get("descriptions", []):
                if desc.get("lang") == "en":
                    description = desc.get("value", "")
                    break

            # CVSS — prefer v3.1, fall back to v3.0, then v2
            cvss_score  = None
            cvss_vector = None
            severity    = None

            metrics = cve.get("metrics", {})
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                metric_list = metrics.get(key, [])
                if metric_list:
                    cvss_data   = metric_list[0].get("cvssData", {})
                    cvss_score  = cvss_data.get("baseScore")
                    cvss_vector = cvss_data.get("vectorString")
                    severity    = _cvss_to_severity(cvss_score)
                    break

            # CWE
            cwe_id = None
            for weakness in cve.get("weaknesses", []):
                for desc in weakness.get("description", []):
                    if desc.get("lang") == "en" and desc.get("value", "").startswith("CWE-"):
                        cwe_id = desc["value"]
                        break
                if cwe_id:
                    break

            # CPEs
            cpes = []
            for config in cve.get("configurations", []):
                for node in config.get("nodes", []):
                    for match in node.get("cpeMatch", []):
                        if match.get("vulnerable"):
                            cpes.append(match.get("criteria", ""))

            records.append({
                "cve_id":      cve_id,
                "description": description,
                "cvss_score":  cvss_score,
                "cvss_vector": cvss_vector,
                "severity":    severity,
                "cwe_id":      cwe_id,
                "cpes":        cpes[:20],  # cap at 20
            })

        return records

    async def save(self, records: list[dict]) -> int:
        """Update existing vulnerability records with NVD enrichment data."""
        updated = 0
        for record in records:
            result = await self.db.execute(
                select(Vulnerability).where(Vulnerability.cve_id == record["cve_id"])
            )
            vulns = result.scalars().all()

            for vuln in vulns:
                if record["cvss_score"] is not None:
                    vuln.cvss_score  = record["cvss_score"]
                    vuln.cvss_vector = record["cvss_vector"]
                if record["severity"]:
                    vuln.severity    = record["severity"]
                if record["description"] and not vuln.description:
                    vuln.description = record["description"]
                if record["cwe_id"] and not vuln.cwe_id:
                    vuln.cwe_id      = record["cwe_id"]
                if record["cpes"]:
                    vuln.affected_cpes = record["cpes"]
                updated += 1

        await self.db.commit()
        self.logger.info("NVD enrichment: %d vulnerability records updated", updated)
        return updated


def _cvss_to_severity(score: Optional[float]) -> Optional[Severity]:
    """Convert CVSS base score to severity enum."""
    if score is None:
        return None
    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    return Severity.LOW
