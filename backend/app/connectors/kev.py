"""
CISA KEV Connector
Pulls the CISA Known Exploited Vulnerabilities catalog.

Source:  https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
Auth:    None
TLS:     Native HTTPS
Schedule: Every 6 hours
"""

import httpx
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import BaseConnector
from app.models.models import Vulnerability, VulnSource, Asset, Severity, VulnStatus

logger = logging.getLogger(__name__)

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# Map KEV severity hints to our internal enum
# KEV doesn't include severity directly — we default CRITICAL for all KEV entries
# NVD connector will enrich with actual CVSS later
KEV_DEFAULT_SEVERITY = Severity.CRITICAL


class KEVConnector(BaseConnector):
    name           = "cisa-kev"
    connector_type = "feed"
    tls_verified   = True
    schedule_hours = 6

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def fetch(self) -> dict:
        """Download the KEV JSON catalog from CISA."""
        self.logger.info("Fetching KEV catalog from CISA")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(KEV_URL)
            response.raise_for_status()
            data = response.json()
            self.logger.info(
                "Fetched KEV catalog: %d entries (catalog version: %s)",
                len(data.get("vulnerabilities", [])),
                data.get("catalogVersion", "unknown"),
            )
            return data

    async def normalize(self, raw: dict) -> list[dict]:
        """Transform KEV entries into normalized records."""
        records = []
        for entry in raw.get("vulnerabilities", []):
            # Parse due date
            due_date   = None
            added_date = None
            try:
                if entry.get("dueDate"):
                    due_date = datetime.strptime(entry["dueDate"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if entry.get("dateAdded"):
                    added_date = datetime.strptime(entry["dateAdded"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError as e:
                self.logger.warning("Could not parse date for %s: %s", entry.get("cveID"), e)

            records.append({
                "cve_id":       entry.get("cveID", "").strip(),
                "description":  entry.get("shortDescription", ""),
                "vendor":       entry.get("vendorProject", ""),
                "product":      entry.get("product", ""),
                "kev_due_date": due_date,
                "kev_added_date": added_date,
                "required_action": entry.get("requiredAction", ""),
                "raw":          entry,
            })

        self.logger.info("Normalized %d KEV entries", len(records))
        return records

    async def save(self, records: list[dict]) -> int:
        """
        Upsert KEV data:
        - For CVEs already in our vulnerability table: mark kev_member=True, set due date
        - Store all KEV entries for cross-reference during future ingestion
        - Does NOT create vulnerability records without a matching asset
          (that's the normalization engine's job)
        """
        updated = 0
        for record in records:
            cve_id = record["cve_id"]
            if not cve_id:
                continue

            # Find all existing vulnerability records for this CVE
            result = await self.db.execute(
                select(Vulnerability).where(Vulnerability.cve_id == cve_id)
            )
            existing_vulns = result.scalars().all()

            for vuln in existing_vulns:
                vuln.kev_member    = True
                vuln.kev_due_date  = record["kev_due_date"]
                vuln.kev_added_date = record["kev_added_date"]
                # Update description if we don't have one yet
                if not vuln.description and record["description"]:
                    vuln.description = record["description"]
                updated += 1

                # Record source
                src_result = await self.db.execute(
                    select(VulnSource).where(
                        VulnSource.vuln_id == vuln.id,
                        VulnSource.source_name == self.name,
                    )
                )
                if not src_result.scalar_one_or_none():
                    self.db.add(VulnSource(
                        vuln_id     = vuln.id,
                        source_name = self.name,
                        raw_data    = record["raw"],
                    ))

        await self.db.commit()
        self.logger.info(
            "KEV sync: %d entries processed, %d existing vulnerabilities updated",
            len(records), updated,
        )
        # Return total catalog size so the connector record shows real count
        return len(records)
