#!/usr/bin/env python3
from __future__ import annotations

from sqlalchemy import func, select

from common import RAW_DIR, get_session, load_json


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _compute_depth_map(items: list[dict[str, str | None]]) -> dict[str, int]:
    parent_map: dict[str, str | None] = {}
    for item in items:
        term = _normalize(str(item["term"]))
        parent = item.get("parent_term")
        parent_map[term] = _normalize(parent) if parent else None

    memo: dict[str, int] = {}

    def depth(term_key: str) -> int:
        if term_key in memo:
            return memo[term_key]
        parent_key = parent_map.get(term_key)
        if not parent_key:
            memo[term_key] = 0
            return 0
        memo[term_key] = min(50, 1 + depth(parent_key))
        return memo[term_key]

    for key in parent_map:
        depth(key)

    return memo


def main() -> None:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.models import OntologyTerm

    payload: list[dict[str, str | None]] = load_json(RAW_DIR / "ontology_terms.json")
    depth_map = _compute_depth_map(payload)

    session = get_session()
    try:
        for item in payload:
            term = str(item["term"]).strip()
            parent = item.get("parent_term")
            depth = depth_map[_normalize(term)]

            stmt = select(OntologyTerm).where(func.lower(OntologyTerm.term) == _normalize(term))
            existing = session.execute(stmt).scalar_one_or_none()

            if existing is None:
                session.add(
                    OntologyTerm(
                        term=term,
                        parent_term=parent,
                        depth=depth,
                        source="seed",
                    )
                )
            else:
                existing.parent_term = parent
                existing.depth = depth
                existing.source = "seed"

        session.commit()
        print(f"Loaded ontology terms: {len(payload)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
