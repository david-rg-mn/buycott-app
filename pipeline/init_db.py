#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def _postgres_dsn() -> str:
    import sys

    backend_path = ROOT / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.config import settings

    return settings.database_url.replace("postgresql+psycopg", "postgresql")


def main() -> None:
    schema_path = ROOT / "database" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    dsn = _postgres_dsn()
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)

    print("Schema applied from database/schema.sql")


if __name__ == "__main__":
    main()
