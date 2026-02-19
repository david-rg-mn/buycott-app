from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.phase0_identity_lock.constraints import MAX_ONTOLOGY_DEPTH, MIN_ONTOLOGY_DEPTH
from app.db.models import OntologyTerm


class OntologyCycleError(ValueError):
    pass


def validate_hierarchy(db: Session) -> None:
    terms = db.execute(select(OntologyTerm.term, OntologyTerm.parent_term, OntologyTerm.depth)).all()
    parent_of = {term: parent for term, parent, _depth in terms}

    for term, _parent, depth in terms:
        if depth < 0:
            raise ValueError(f"Ontology depth must be non-negative for term '{term}'")
        seen: set[str] = set()
        cursor = term
        while cursor is not None:
            if cursor in seen:
                raise OntologyCycleError(f"Cycle detected for ontology term '{term}'")
            seen.add(cursor)
            cursor = parent_of.get(cursor)


def bounded_expansion_depth(path_length: int) -> int:
    if path_length < MIN_ONTOLOGY_DEPTH:
        return MIN_ONTOLOGY_DEPTH
    if path_length > MAX_ONTOLOGY_DEPTH:
        return MAX_ONTOLOGY_DEPTH
    return path_length
