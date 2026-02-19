from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import OntologyTerm
from app.phase0_identity_lock.ontology_guard import bounded_expansion_depth
from app.phase1_semantic_pipeline.embeddings import cosine_similarity, embedding_service


@dataclass(frozen=True)
class OntologyExpansion:
    anchor_term: str
    expanded_terms: list[str]


def resolve_anchor_term(db: Session, query: str, query_embedding: list[float]) -> str:
    exact = db.scalar(
        select(OntologyTerm.term).where(func.lower(OntologyTerm.term) == query.strip().lower()).limit(1)
    )
    if exact:
        return exact

    candidates = db.execute(select(OntologyTerm.term, OntologyTerm.embedding)).all()
    if not candidates:
        return query

    best_term = query
    best_score = -1.0
    for term, embedding in candidates:
        score = cosine_similarity(query_embedding, embedding)
        if score > best_score:
            best_score = score
            best_term = term
    return best_term


def expand_query_hierarchy(db: Session, query: str) -> OntologyExpansion:
    settings = get_settings()
    query_embedding = embedding_service.embed_text(query)
    anchor = resolve_anchor_term(db, query, query_embedding)

    parents = {
        term: parent
        for term, parent in db.execute(select(OntologyTerm.term, OntologyTerm.parent_term)).all()
    }

    terms = [anchor]
    visited = {anchor}
    cursor = anchor

    max_depth = settings.ontology_max_depth
    while len(terms) < max_depth:
        parent = parents.get(cursor)
        if parent is None:
            break
        if parent in visited:
            break
        terms.append(parent)
        visited.add(parent)
        cursor = parent

    capped_len = bounded_expansion_depth(len(terms))
    terms = terms[:capped_len]

    if query not in terms:
        terms.insert(0, query)
        if len(terms) > settings.ontology_max_depth:
            terms = terms[: settings.ontology_max_depth]

    return OntologyExpansion(anchor_term=anchor, expanded_terms=terms)


def related_items(db: Session, term: str, limit: int = 5) -> list[str]:
    canonical = db.scalar(
        select(OntologyTerm.term).where(func.lower(OntologyTerm.term) == term.strip().lower()).limit(1)
    )
    if canonical is None:
        query_embedding = embedding_service.embed_text(term)
        canonical = resolve_anchor_term(db, term, query_embedding)

    parent = db.scalar(select(OntologyTerm.parent_term).where(OntologyTerm.term == canonical).limit(1))

    siblings: list[str] = []
    if parent:
        siblings = [
            row[0]
            for row in db.execute(
                select(OntologyTerm.term)
                .where(OntologyTerm.parent_term == parent)
                .where(OntologyTerm.term != canonical)
                .limit(limit)
            ).all()
        ]

    children = [
        row[0]
        for row in db.execute(
            select(OntologyTerm.term).where(OntologyTerm.parent_term == canonical).limit(limit)
        ).all()
    ]

    ordered: list[str] = []
    for item in children + siblings:
        if item not in ordered:
            ordered.append(item)
        if len(ordered) >= limit:
            break

    return ordered
