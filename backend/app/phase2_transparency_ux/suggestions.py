from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import OntologyTerm
from app.phase1_semantic_pipeline.ontology import related_items


def search_suggestions(db: Session, query_prefix: str, limit: int = 8) -> list[str]:
    prefix = query_prefix.strip().lower()
    if not prefix:
        return []

    rows = db.execute(
        select(OntologyTerm.term)
        .where(func.lower(OntologyTerm.term).like(f"{prefix}%"))
        .order_by(OntologyTerm.depth.asc(), OntologyTerm.term.asc())
        .limit(limit)
    ).all()
    return [row[0] for row in rows]


def related_item_suggestions(db: Session, query: str, limit: int = 5) -> list[str]:
    return related_items(db, query, limit=limit)
