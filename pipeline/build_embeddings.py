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

    from app.models import Business, CapabilityProfile, MenuItem, OntologyNode, OntologyTerm
    from app.services.embedding_service import get_embedding_service

    embedding_service = get_embedding_service()
    session = get_session()

    try:
        ontology_rows = session.execute(select(OntologyTerm).order_by(OntologyTerm.id.asc())).scalars().all()
        ontology_vectors = embedding_service.encode_many([row.term for row in ontology_rows])
        for row, vector in zip(ontology_rows, ontology_vectors, strict=False):
            row.embedding = vector

        ontology_node_rows = session.execute(select(OntologyNode).order_by(OntologyNode.id.asc())).scalars().all()
        ontology_node_vectors = embedding_service.encode_many([row.canonical_term for row in ontology_node_rows])
        for row, vector in zip(ontology_node_rows, ontology_node_vectors, strict=False):
            row.embedding = vector

        menu_rows = session.execute(select(MenuItem).order_by(MenuItem.id.asc())).scalars().all()
        menu_texts = [
            f"{row.item_name}. {row.description or ''}. {' '.join(row.dietary_tags if isinstance(row.dietary_tags, list) else [])}".strip()
            for row in menu_rows
        ]
        menu_vectors = embedding_service.encode_many(menu_texts)
        for row, vector in zip(menu_rows, menu_vectors, strict=False):
            row.embedding = vector

        capability_rows = session.execute(select(CapabilityProfile).order_by(CapabilityProfile.id.asc())).scalars().all()
        capability_vectors = embedding_service.encode_many([row.canonical_text for row in capability_rows])
        for row, vector in zip(capability_rows, capability_vectors, strict=False):
            row.embedding = vector

        business_rows = session.execute(select(Business).order_by(Business.id.asc())).scalars().all()
        business_texts: list[str] = []
        for row in business_rows:
            if row.canonical_summary_text:
                business_texts.append(row.canonical_summary_text)
            else:
                business_texts.append(row.text_content)
        business_vectors = embedding_service.encode_many(business_texts)
        for row, vector in zip(business_rows, business_vectors, strict=False):
            row.embedding = vector

        session.commit()
        print(
            "Embeddings generated: "
            f"businesses={len(business_rows)}, "
            f"ontology_terms={len(ontology_rows)}, "
            f"ontology_nodes={len(ontology_node_rows)}, "
            f"menu_items={len(menu_rows)}, "
            f"capabilities={len(capability_rows)}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
