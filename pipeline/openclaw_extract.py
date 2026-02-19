#!/usr/bin/env python3
from __future__ import annotations

from sqlalchemy import func, select

from common import RAW_DIR, get_session, load_json, utcnow


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> None:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.models import Business, BusinessSource

    data = load_json(RAW_DIR / "businesses.json")

    session = get_session()
    inserted = 0
    updated = 0
    try:
        for item in data:
            name = str(item["name"]).strip()
            stmt = select(Business).where(func.lower(Business.name) == _normalize(name))
            business = session.execute(stmt).scalar_one_or_none()

            if business is None:
                business = Business(name=name, text_content=item["text_content"])
                session.add(business)
                inserted += 1
            else:
                updated += 1

            business.lat = float(item["lat"])
            business.lng = float(item["lng"])
            business.text_content = item["text_content"]
            business.is_chain = bool(item.get("is_chain", False))
            business.chain_name = item.get("chain_name")
            business.phone = item.get("phone")
            business.website = item.get("website")
            business.hours_json = item.get("hours_json") or {}
            business.timezone = item.get("timezone") or "America/Chicago"
            business.last_updated = utcnow()

            session.flush()

            existing_sources = {
                (src.source_type, src.source_url): src
                for src in session.execute(
                    select(BusinessSource).where(BusinessSource.business_id == business.id)
                ).scalars()
            }

            seen_keys: set[tuple[str, str | None]] = set()
            for source in item.get("sources", []):
                key = (source["source_type"], source.get("source_url"))
                seen_keys.add(key)
                source_row = existing_sources.get(key)
                if source_row is None:
                    session.add(
                        BusinessSource(
                            business_id=business.id,
                            source_type=source["source_type"],
                            source_url=source.get("source_url"),
                            snippet=source.get("snippet"),
                            last_fetched=utcnow(),
                        )
                    )
                else:
                    source_row.snippet = source.get("snippet")
                    source_row.last_fetched = utcnow()

            for key, source_row in existing_sources.items():
                if key not in seen_keys:
                    session.delete(source_row)

        session.commit()
        print(f"OpenClaw extract complete: inserted={inserted}, updated={updated}, total={len(data)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
