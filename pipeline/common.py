from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def get_session() -> Session:
    import sys

    backend_path = ROOT / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.database import SessionLocal

    return SessionLocal()
