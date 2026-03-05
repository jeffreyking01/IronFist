"""
Tenable Dummy Data Generator
Generates realistic Tenable-schema scan results for dev/testing.
Seeded with real CVE IDs from the KEV catalog so cross-referencing works.

In production: replace this with the real Tenable connector
that calls the Tenable.sc or Tenable.io API.
"""

import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import BaseConnector
from app.models.models import (
    Vulnerability, VulnSource, Asset, Severity, VulnStatus, ConnectorStatus
)

logger = logging.getLogger(__name__)

# Real CVE IDs — mix of KEV entries and common vulns for realistic data
SAMPLE_CVES = [
    {"cve_id": "CVE-2024-21762", "severity": Severity.CRITICAL, "cvss": 9.8,
     "desc": "Fortinet FortiOS SSL VPN out-of-bound write vulnerability allows remote code execution"},
    {"cve_id": "CVE-2023-44487",  "severity": Severity.HIGH,     "cvss": 7.5,
     "desc": "HTTP/2 Rapid Reset Attack allows distributed denial of service"},
    {"cve_id": "CVE-2024-3400",   "severity": Severity.CRITICAL, "cvss": 10.0,
     "desc": "PAN-OS command injection vulnerability in GlobalProtect"},
    {"cve_id": "CVE-2024-0519",   "severity": Severity.HIGH,     "cvss": 8.8,
     "desc": "Google Chrome V8 engine out-of-bounds memory access"},
    {"cve_id": "CVE-2024-1709",   "severity": Severity.CRITICAL, "cvss": 10.0,
     "desc": "ConnectWise ScreenConnect authentication bypass vulnerability"},
    {"cve_id": "CVE-2023-20198",  "severity": Severity.CRITICAL, "cvss": 10.0,
     "desc": "Cisco IOS XE web UI privilege escalation vulnerability"},
    {"cve_id": "CVE-2024-21887",  "severity": Severity.CRITICAL, "cvss": 9.1,
     "desc": "Ivanti Connect Secure command injection vulnerability"},
    {"cve_id": "CVE-2023-46805",  "severity": Severity.HIGH,     "cvss": 8.2,
     "desc": "Ivanti Connect Secure authentication bypass vulnerability"},
    {"cve_id": "CVE-2024-6387",   "severity": Severity.CRITICAL, "cvss": 8.1,
     "desc": "OpenSSH regreSSHion remote code execution vulnerability"},
    {"cve_id": "CVE-2021-44228",  "severity": Severity.CRITICAL, "cvss": 10.0,
     "desc": "Apache Log4j2 JNDI remote code execution (Log4Shell)"},
    {"cve_id": "CVE-2023-4966",   "severity": Severity.CRITICAL, "cvss": 9.4,
     "desc": "Citrix Bleed - NetScaler sensitive information disclosure"},
    {"cve_id": "CVE-2024-23897",  "severity": Severity.CRITICAL, "cvss": 9.8,
     "desc": "Jenkins arbitrary file read vulnerability via CLI"},
]

# Fake asset pool — will be matched against CMDB if assets exist
SAMPLE_ASSETS = [
    {"ip": "10.0.2.10", "hostname": "dc01.agency.local",   "owner": "Infra",   "boundary": "HVA-Core"},
    {"ip": "10.0.2.11", "hostname": "dc02.agency.local",   "owner": "Infra",   "boundary": "HVA-Core"},
    {"ip": "10.0.2.20", "hostname": "app-srv-01",          "owner": "AppDev",  "boundary": "Prod-DMZ"},
    {"ip": "10.0.2.21", "hostname": "app-srv-02",          "owner": "AppDev",  "boundary": "Prod-DMZ"},
    {"ip": "10.0.2.30", "hostname": "db-cluster-01",       "owner": "Data",    "boundary": "HVA-Core"},
    {"ip": "10.0.2.31", "hostname": "db-cluster-02",       "owner": "Data",    "boundary": "HVA-Core"},
    {"ip": "10.0.2.40", "hostname": "fw-edge-01",          "owner": "Infra",   "boundary": "Perimeter"},
    {"ip": "10.0.2.50", "hostname": "k8s-node-01",         "owner": "AppDev",  "boundary": "Containers"},
    {"ip": "10.0.2.51", "hostname": "k8s-node-02",         "owner": "AppDev",  "boundary": "Containers"},
    {"ip": "10.0.2.60", "hostname": "jump-box-01",         "owner": "Infra",   "boundary": "Mgmt"},
]


class TenableDummyConnector(BaseConnector):
    name           = "tenable-dummy"
    connector_type = "scanner"
    tls_verified   = True
    schedule_hours = 24

    def __init__(self, db: AsyncSession, seed: Optional[int] = None):
        super().__init__(db)
        if seed is not None:
            random.seed(seed)

    async def fetch(self) -> list[dict]:
        """
        Generate realistic dummy scan results.
        Each asset gets a random subset of CVEs assigned to it.
        """
        self.logger.info("Generating dummy Tenable scan data")
        findings = []

        for asset in SAMPLE_ASSETS:
            # Each asset gets 2-6 random CVEs
            num_vulns = random.randint(2, 6)
            assigned_cves = random.sample(SAMPLE_CVES, min(num_vulns, len(SAMPLE_CVES)))

            for cve in assigned_cves:
                # Simulate scan detection time
                detected_days_ago = random.randint(1, 90)
                detected_at = datetime.now(timezone.utc) - timedelta(days=detected_days_ago)

                findings.append({
                    "asset":       asset,
                    "cve":         cve,
                    "detected_at": detected_at,
                    "plugin_id":   random.randint(100000, 199999),
                    "source":      "tenable-dummy",
                })

        self.logger.info("Generated %d dummy findings across %d assets", len(findings), len(SAMPLE_ASSETS))
        return findings

    async def normalize(self, raw: list[dict]) -> list[dict]:
        """Pass through — dummy data is already in normalized form."""
        return raw

    async def save(self, records: list[dict]) -> int:
        """
        Upsert assets and vulnerability findings.
        This simulates what the real Tenable connector will do.
        """
        saved = 0
        now   = datetime.now(timezone.utc)

        for record in records:
            asset_data = record["asset"]
            cve_data   = record["cve"]

            # ── Upsert Asset ────────────────────────────────────────────────
            result = await self.db.execute(
                select(Asset).where(Asset.ip_address == asset_data["ip"])
            )
            asset = result.scalar_one_or_none()

            if not asset:
                asset = Asset(
                    ip_address     = asset_data["ip"],
                    hostname       = asset_data["hostname"],
                    system_owner   = asset_data["owner"],
                    fisma_boundary = asset_data["boundary"],
                    last_seen      = now,
                    is_stale       = False,
                )
                self.db.add(asset)
                await self.db.flush()   # get asset.id without full commit
                self.logger.debug("Created asset: %s", asset_data["hostname"])
            else:
                asset.last_seen = now
                asset.is_stale  = False

            # ── Upsert Vulnerability ────────────────────────────────────────
            result = await self.db.execute(
                select(Vulnerability).where(
                    Vulnerability.cve_id   == cve_data["cve_id"],
                    Vulnerability.asset_id == asset.id,
                )
            )
            vuln = result.scalar_one_or_none()

            if not vuln:
                vuln = Vulnerability(
                    cve_id         = cve_data["cve_id"],
                    asset_id       = asset.id,
                    severity       = cve_data["severity"],
                    cvss_score     = cve_data["cvss"],
                    description    = cve_data["desc"],
                    status         = VulnStatus.OPEN,
                    first_detected = record["detected_at"],
                    last_seen      = now,
                )
                self.db.add(vuln)
                await self.db.flush()

                # Record source
                self.db.add(VulnSource(
                    vuln_id     = vuln.id,
                    source_name = self.name,
                    raw_data    = {"plugin_id": record["plugin_id"]},
                ))
                saved += 1
            else:
                vuln.last_seen = now

        await self.db.commit()
        self.logger.info("Tenable dummy: %d new findings saved", saved)
        return saved
