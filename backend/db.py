"""Database helpers for SenAI backend services."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.config import settings


@contextmanager
def db_connection(cursor_factory=None) -> Iterator:
    conn = psycopg2.connect(**settings.db_config)
    try:
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def dict_cursor() -> Iterator:
    with db_connection(cursor_factory=RealDictCursor) as pair:
        yield pair
