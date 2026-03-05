"""
IronFist Database Models
All SQLAlchemy ORM models for the platform.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum


# ── Enums ──────────────────────────────────────────────────────────────────────
class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"

class Criticality(str, enum.Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"

class VulnStatus(str, enum.Enum):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED    = "RESOLVED"
    ACCEPTED    = "ACCEPTED"

class ConnectorStatus(str, enum.Enum):
    ACTIVE      = "ACTIVE"
    INACTIVE    = "INACTIVE"
    ERROR       = "ERROR"
    CONFIGURING = "CONFIGURING"


# ── Assets (CMDB) ──────────────────────────────────────────────────────────────
class Asset(Base):
    __tablename__ = "assets"

    id:              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address:      Mapped[str]             = mapped_column(String(45), nullable=False, index=True)
    hostname:        Mapped[Optional[str]]   = mapped_column(String(255), index=True)
    fqdn:            Mapped[Optional[str]]   = mapped_column(String(255))
    os_name:         Mapped[Optional[str]]   = mapped_column(String(255))
    os_version:      Mapped[Optional[str]]   = mapped_column(String(100))
    system_owner:    Mapped[Optional[str]]   = mapped_column(String(255))
    fisma_boundary:  Mapped[Optional[str]]   = mapped_column(String(255), index=True)
    criticality:     Mapped[Criticality]     = mapped_column(SAEnum(Criticality), default=Criticality.MEDIUM)
    tags:            Mapped[Optional[dict]]  = mapped_column(JSON, default=dict)
    first_seen:      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen:       Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_stale:        Mapped[bool]            = mapped_column(Boolean, default=False)
    agent_version:   Mapped[Optional[str]]   = mapped_column(String(50))
    raw_data:        Mapped[Optional[dict]]  = mapped_column(JSON)

    # Relationships
    vulnerabilities: Mapped[list["Vulnerability"]] = relationship("Vulnerability", back_populates="asset")

    __table_args__ = (
        Index("ix_assets_ip_hostname", "ip_address", "hostname"),
    )


# ── Vulnerabilities ────────────────────────────────────────────────────────────
class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id:              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cve_id:          Mapped[str]             = mapped_column(String(30), nullable=False, index=True)
    asset_id:        Mapped[uuid.UUID]       = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)

    # Severity and scoring
    severity:        Mapped[Severity]        = mapped_column(SAEnum(Severity), nullable=False, index=True)
    cvss_score:      Mapped[Optional[float]] = mapped_column(Float)
    cvss_vector:     Mapped[Optional[str]]   = mapped_column(String(100))

    # CVE metadata (enriched from NVD)
    description:     Mapped[Optional[str]]   = mapped_column(Text)
    cwe_id:          Mapped[Optional[str]]   = mapped_column(String(30))
    affected_cpes:   Mapped[Optional[list]]  = mapped_column(JSON, default=list)

    # KEV tracking
    kev_member:      Mapped[bool]            = mapped_column(Boolean, default=False, index=True)
    kev_due_date:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    kev_added_date:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status
    status:          Mapped[VulnStatus]      = mapped_column(SAEnum(VulnStatus), default=VulnStatus.OPEN, index=True)
    first_detected:  Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen:       Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    asset:           Mapped["Asset"]         = relationship("Asset", back_populates="vulnerabilities")
    sources:         Mapped[list["VulnSource"]] = relationship("VulnSource", back_populates="vulnerability")

    __table_args__ = (
        Index("ix_vuln_cve_asset", "cve_id", "asset_id", unique=True),
        Index("ix_vuln_kev_status", "kev_member", "status"),
    )


# ── Vulnerability Sources ──────────────────────────────────────────────────────
class VulnSource(Base):
    """Tracks which connectors reported a given vulnerability."""
    __tablename__ = "vuln_sources"

    id:              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vuln_id:         Mapped[uuid.UUID]       = mapped_column(ForeignKey("vulnerabilities.id"), nullable=False, index=True)
    source_name:     Mapped[str]             = mapped_column(String(100), nullable=False)
    raw_data:        Mapped[Optional[dict]]  = mapped_column(JSON)
    ingested_at:     Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())

    vulnerability:   Mapped["Vulnerability"] = relationship("Vulnerability", back_populates="sources")


# ── Connectors ─────────────────────────────────────────────────────────────────
class Connector(Base):
    __tablename__ = "connectors"

    id:              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:            Mapped[str]             = mapped_column(String(100), nullable=False, unique=True)
    connector_type:  Mapped[str]             = mapped_column(String(50), nullable=False)
    status:          Mapped[ConnectorStatus] = mapped_column(SAEnum(ConnectorStatus), default=ConnectorStatus.INACTIVE)
    enabled:         Mapped[bool]            = mapped_column(Boolean, default=True)
    tls_verified:    Mapped[bool]            = mapped_column(Boolean, default=True)
    schedule_hours:  Mapped[int]             = mapped_column(Integer, default=24)
    config:          Mapped[Optional[dict]]  = mapped_column(JSON, default=dict)
    last_sync_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_sync_count: Mapped[int]             = mapped_column(Integer, default=0)
    last_error:      Mapped[Optional[str]]   = mapped_column(Text)
    created_at:      Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Audit Log ──────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id:              Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp:       Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id:         Mapped[Optional[str]]   = mapped_column(String(255), index=True)
    action:          Mapped[str]             = mapped_column(String(100), nullable=False)
    resource_type:   Mapped[Optional[str]]   = mapped_column(String(100))
    resource_id:     Mapped[Optional[str]]   = mapped_column(String(255))
    source_ip:       Mapped[Optional[str]]   = mapped_column(String(45))
    details:         Mapped[Optional[dict]]  = mapped_column(JSON)
