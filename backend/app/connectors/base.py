"""
Base Connector
All connectors inherit from this class.
Enforces a consistent interface: fetch() → normalize() → save()
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Connector, ConnectorStatus

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """
    Every connector must implement:
      - name:        str — unique identifier (matches Connector.name in DB)
      - fetch()      — pull raw data from source
      - normalize()  — transform raw data to internal schema
      - run()        — orchestrates fetch → normalize → save, updates connector record
    """

    name:          str = "base"
    connector_type: str = "base"
    tls_verified:  bool = True
    schedule_hours: int = 24

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(f"connector.{self.name}")

    @abstractmethod
    async def fetch(self) -> Any:
        """Fetch raw data from the source. Return raw payload."""
        pass

    @abstractmethod
    async def normalize(self, raw: Any) -> list[dict]:
        """Transform raw payload into list of normalized records."""
        pass

    async def run(self) -> dict:
        """
        Orchestrates a full sync cycle:
        1. Mark connector as syncing
        2. Fetch raw data
        3. Normalize
        4. Save to database
        5. Update connector record with result
        """
        self.logger.info("Starting sync: %s", self.name)
        connector = await self._get_or_create_connector()
        start     = datetime.now(timezone.utc)

        try:
            raw        = await self.fetch()
            records    = await self.normalize(raw)
            count      = await self.save(records)

            connector.status          = ConnectorStatus.ACTIVE
            connector.last_sync_at    = datetime.now(timezone.utc)
            connector.last_sync_count = count
            connector.last_error      = None
            await self.db.commit()

            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            self.logger.info("Sync complete: %s — %d records in %.1fs", self.name, count, elapsed)
            return {"connector": self.name, "status": "ok", "count": count, "elapsed_s": elapsed}

        except Exception as e:
            self.logger.error("Sync failed: %s — %s", self.name, str(e), exc_info=True)
            connector.status     = ConnectorStatus.ERROR
            connector.last_error = str(e)
            await self.db.commit()
            return {"connector": self.name, "status": "error", "error": str(e)}

    @abstractmethod
    async def save(self, records: list[dict]) -> int:
        """Persist normalized records to the database. Return count saved."""
        pass

    async def _get_or_create_connector(self) -> Connector:
        """Upsert the connector record in the database."""
        result = await self.db.execute(
            select(Connector).where(Connector.name == self.name)
        )
        connector = result.scalar_one_or_none()

        if not connector:
            connector = Connector(
                name           = self.name,
                connector_type = self.connector_type,
                status         = ConnectorStatus.CONFIGURING,
                tls_verified   = self.tls_verified,
                schedule_hours = self.schedule_hours,
                enabled        = True,
            )
            self.db.add(connector)
            await self.db.commit()
            await self.db.refresh(connector)
            self.logger.info("Created connector record: %s", self.name)

        return connector
