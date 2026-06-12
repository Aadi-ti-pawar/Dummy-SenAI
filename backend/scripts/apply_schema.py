"""
Apply backend/database_schema.sql to the configured PostgreSQL database.

Run from the backend directory:
    python scripts/apply_schema.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402

REQUIRED_TABLES = (
    "contacts",
    "threads",
    "emails",
    "processing_jobs",
    "audit_log",
)


def main() -> None:
    settings = get_settings()
    schema_path = BACKEND_DIR / "database_schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    safe_url = make_url(settings.database_url).render_as_string(hide_password=True)
    print(f"Applying schema to {safe_url}")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.exec_driver_sql(schema_sql)

    with engine.connect() as connection:
        found = set(
            connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = ANY(:table_names)
                    """
                ),
                {"table_names": list(REQUIRED_TABLES)},
            ).scalars()
        )

    missing = sorted(set(REQUIRED_TABLES) - found)
    if missing:
        raise RuntimeError(f"Schema apply finished, but tables are missing: {missing}")

    print("Schema applied successfully.")


if __name__ == "__main__":
    main()
