#!/usr/bin/env python3
from __future__ import annotations

from sqlalchemy import select

from common import get_session


def main() -> None:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    from app.models import Business, OntologyTerm
    from app.services.embedding_service import get_embedding_service

    embedding_service = get_embedding_service()
    session = get_session()

    try:
        ontology_rows = session.execute(select(OntologyTerm).order_by(OntologyTerm.id.asc())).scalars().all()
        ontology_vectors = embedding_service.encode_many([row.term for row in ontology_rows])
        for row, vector in zip(ontology_rows, ontology_vectors, strict=False):
            row.embedding = vector

        business_rows = session.execute(select(Business).order_by(Business.id.asc())).scalars().all()
        business_vectors = embedding_service.encode_many([row.text_content for row in business_rows])
        for row, vector in zip(business_rows, business_vectors, strict=False):
            row.embedding = vector

        session.commit()
        print(
            f"Embeddings generated: businesses={len(business_rows)}, ontology_terms={len(ontology_rows)}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
