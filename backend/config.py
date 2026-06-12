"""Shared runtime configuration for SenAI backend services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("SENAI_DB_HOST", "localhost")
    db_port: int = int(os.getenv("SENAI_DB_PORT", "5432"))
    db_name: str = os.getenv("SENAI_DB_NAME", "crm_ai")
    db_user: str = os.getenv("SENAI_DB_USER", "postgres")
    db_password: str = os.getenv("SENAI_DB_PASSWORD", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    embedding_model: str = os.getenv(
        "SENAI_EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    email_data_file: Path = Path(
        os.getenv("SENAI_EMAIL_DATA_FILE", str(PROJECT_ROOT / "email-data-advanced.json"))
    )
    policies_dir: Path = Path(
        os.getenv("SENAI_POLICIES_DIR", str(PROJECT_ROOT / "backend" / "policies"))
    )

    @property
    def db_config(self) -> dict:
        return {
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
        }


settings = Settings()
