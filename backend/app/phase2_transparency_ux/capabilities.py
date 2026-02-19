from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BusinessCapability, OntologyTerm


def capability_profile(db: Session, business_id: uuid.UUID, limit: int = 8) -> list[BusinessCapability]:
    rows = db.execute(
        select(BusinessCapability)
        .where(BusinessCapability.business_id == business_id)
        .order_by(BusinessCapability.confidence_score.desc())
        .limit(limit)
    ).scalars()
    return list(rows)


def _root_term_map(db: Session) -> dict[str, str]:
    terms = db.execute(select(OntologyTerm.term, OntologyTerm.parent_term)).all()
    parent_map = {term: parent for term, parent in terms}

    roots: dict[str, str] = {}
    for term in parent_map:
        cursor = term
        seen: set[str] = set()
        while parent_map.get(cursor) is not None and cursor not in seen:
            seen.add(cursor)
            cursor = parent_map[cursor]
        roots[term] = cursor

    return roots


def is_specialist_business(db: Session, capabilities: list[BusinessCapability]) -> bool:
    strong_caps = [cap for cap in capabilities if cap.confidence_score >= 0.65]
    if len(strong_caps) < 2:
        return False

    roots = _root_term_map(db)
    distribution = defaultdict(int)
    for cap in strong_caps:
        distribution[roots.get(cap.ontology_term, cap.ontology_term)] += 1

    dominant_share = max(distribution.values()) / len(strong_caps)
    return dominant_share >= 0.75
