"""
IronFist — Application Configuration
Reads settings from environment variables.
In production (EC2), these are injected from AWS Secrets Manager via the
startup script. In local dev, they come from docker-compose .env file.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    app_name:        str = "IronFist"
    app_version:     str = "0.1.0"
    environment:     str = os.getenv("ENVIRONMENT", "dev")
    debug:           bool = os.getenv("DEBUG", "true").lower() == "true"
    log_level:       str = os.getenv("LOG_LEVEL", "INFO")

    # ── Database ──────────────────────────────────────────────────────────────
    db_host:         str = os.getenv("DB_HOST", "db")
    db_port:         int = int(os.getenv("DB_PORT", "5432"))
    db_name:         str = os.getenv("DB_NAME", "ironfist")
    db_username:     str = os.getenv("DB_USERNAME", "ironfist_admin")
    db_password:     str = os.getenv("DB_PASSWORD", "devpassword")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic migrations."""
        return (
            f"postgresql://{self.db_username}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ── Auth ──────────────────────────────────────────────────────────────────
    auth_mode:            str = os.getenv("AUTH_MODE", "local")
    jwt_secret:           str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    jwt_expire_hours:     int = int(os.getenv("JWT_EXPIRE_HOURS", "8"))
    local_auth_username:  str = os.getenv("LOCAL_AUTH_USERNAME", "admin")
    local_auth_password:  str = os.getenv("LOCAL_AUTH_PASSWORD", "ironfist")

    # Entra ID (only needed in production)
    entra_tenant_id:      str = os.getenv("ENTRA_TENANT_ID", "")
    entra_client_id:      str = os.getenv("ENTRA_CLIENT_ID", "")
    entra_client_secret:  str = os.getenv("ENTRA_CLIENT_SECRET", "")

    # ── External APIs ─────────────────────────────────────────────────────────
    openai_api_key:       str = os.getenv("OPENAI_API_KEY", "")
    openai_model:         str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    nvd_api_key:          str = os.getenv("NVD_API_KEY", "")

    # ── CMDB Agent ────────────────────────────────────────────────────────────
    cmdb_agent_token:     str = os.getenv("CMDB_AGENT_TOKEN", "dev-agent-token")

    # ── Connector schedules (cron expressions) ────────────────────────────────
    kev_sync_hours:       int = int(os.getenv("KEV_SYNC_HOURS", "6"))
    nvd_sync_hours:       int = int(os.getenv("NVD_SYNC_HOURS", "24"))

    class Config:
        env_file = ".env"
        extra    = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
