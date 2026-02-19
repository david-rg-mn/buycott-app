#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
from sqlalchemy import delete, select

from common import get_session, utcnow

MIN_SIMILARITY = 0.18
TOP_TERMS = 10


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def main() -> None:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.models import Business, BusinessCapability, OntologyTerm

    session = get_session()
    try:
        ontology_rows = session.execute(
            select(OntologyTerm).where(OntologyTerm.embedding.is_not(None)).order_by(OntologyTerm.id.asc())
        ).scalars().all()

        if not ontology_rows:
            print("No ontology embeddings found. Run build_embeddings.py first.")
            return

        term_vectors = np.array([row.embedding for row in ontology_rows], dtype=np.float32)
        term_norms = np.linalg.norm(term_vectors, axis=1, keepdims=True)
        term_vectors = term_vectors / np.clip(term_norms, 1e-9, None)

        parent_map = {_normalize(row.term): _normalize(row.parent_term) if row.parent_term else None for row in ontology_rows}

        def root_term(term: str) -> str:
            key = _normalize(term)
            seen = set()
            while parent_map.get(key):
                if key in seen:
                    break
                seen.add(key)
                key = parent_map[key] or key
            return key

        business_rows = session.execute(
            select(Business).where(Business.embedding.is_not(None)).order_by(Business.id.asc())
        ).scalars().all()

        total_links = 0
        for business in business_rows:
            session.execute(delete(BusinessCapability).where(BusinessCapability.business_id == business.id))

            business_vec = np.array(business.embedding, dtype=np.float32)
            business_norm = np.linalg.norm(business_vec)
            if business_norm == 0:
                business.specialty_score = 0
                continue
            business_vec = business_vec / business_norm

            similarities = term_vectors @ business_vec
            best_indexes = np.argsort(similarities)[::-1][:TOP_TERMS]

            chosen_terms: list[tuple[OntologyTerm, float]] = []
            for index in best_indexes:
                sim = float(similarities[index])
                if sim < MIN_SIMILARITY:
                    continue
                chosen_terms.append((ontology_rows[int(index)], sim))

            for term_row, sim in chosen_terms:
                confidence = max(0.0, min(1.0, (sim + 1.0) / 2.0))
                session.add(
                    BusinessCapability(
                        business_id=business.id,
                        ontology_term=term_row.term,
                        confidence_score=confidence,
                        source_reference="semantic embedding proximity from public business text",
                        last_updated=utcnow(),
                    )
                )
                total_links += 1

            if chosen_terms:
                roots = [root_term(term_row.term) for term_row, _ in chosen_terms[:6]]
                counts: dict[str, int] = {}
                for root in roots:
                    counts[root] = counts.get(root, 0) + 1
                business.specialty_score = max(counts.values()) / len(roots)
            else:
                business.specialty_score = 0

            business.last_updated = utcnow()

        session.commit()
        print(f"Capability mapping complete: businesses={len(business_rows)}, capability_links={total_links}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
