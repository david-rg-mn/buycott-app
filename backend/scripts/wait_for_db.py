from __future__ import annotations

import sys
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import engine


def main() -> None:
    attempts = 60
    delay_seconds = 2

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database is ready.")
            return
        except OperationalError:
            print(f"Waiting for database ({attempt}/{attempts})...")
            time.sleep(delay_seconds)

    raise SystemExit("Database did not become ready in time.")


if __name__ == "__main__":
    main()
