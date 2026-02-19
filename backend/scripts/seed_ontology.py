from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import OntologyTerm
from app.db.session import SessionLocal
from app.phase0_identity_lock.ontology_guard import validate_hierarchy
from app.phase1_semantic_pipeline.embeddings import embedding_service

ONTOLOGY_ROWS: list[tuple[str, str | None, int]] = [
    ("retail capability", None, 0),
    ("electronics accessory", "retail capability", 1),
    ("phone accessory", "electronics accessory", 2),
    ("charging cable", "phone accessory", 3),
    ("usb cable", "charging cable", 4),
    ("usb-c to lightning cable", "usb cable", 5),
    ("phone charger", "charging cable", 4),
    ("screen protector", "phone accessory", 3),
    ("portable power", "electronics accessory", 2),
    ("aa batteries", "portable power", 3),
    ("camera capability", "retail capability", 1),
    ("photography accessory", "camera capability", 2),
    ("camera charger", "photography accessory", 3),
    ("camera battery charger", "camera charger", 4),
    ("camera battery", "photography accessory", 3),
    ("camera film", "camera capability", 2),
    ("35mm film roll", "camera film", 3),
    ("camera strap", "photography accessory", 3),
    ("photo printing", "camera capability", 2),
    ("bakery capability", "retail capability", 1),
    ("baking supplies", "bakery capability", 2),
    ("cake decoration", "baking supplies", 3),
    ("birthday candle", "cake decoration", 4),
    ("birthday candle number 5", "birthday candle", 5),
    ("birthday cake candles", "birthday candle", 5),
    ("hardware capability", "retail capability", 1),
    ("repair tool", "hardware capability", 2),
    ("hand tool", "repair tool", 3),
    ("screwdriver", "hand tool", 4),
    ("precision screwdriver", "screwdriver", 5),
    ("shipping supply", "hardware capability", 2),
    ("packaging supply", "shipping supply", 3),
    ("packing tape", "packaging supply", 4),
    ("moving box tape", "packing tape", 5),
    ("moving supplies", "shipping supply", 3),
    ("boxes", "moving supplies", 4),
    ("bubble wrap", "moving supplies", 4),
    ("art supply capability", "retail capability", 1),
    ("instrument capability", "retail capability", 1),
]


def main() -> None:
    session = SessionLocal()
    try:
        for term, parent_term, depth in ONTOLOGY_ROWS:
            embedding = embedding_service.embed_text(term)
            current = session.scalar(select(OntologyTerm).where(OntologyTerm.term == term))
            if current is None:
                session.add(
                    OntologyTerm(
                        term=term,
                        parent_term=parent_term,
                        depth=depth,
                        embedding=embedding,
                        source="seed_phase1_phase2",
                    )
                )
            else:
                current.parent_term = parent_term
                current.depth = depth
                current.embedding = embedding
                current.source = "seed_phase1_phase2"

        session.commit()
        validate_hierarchy(session)
        print(f"Seeded ontology terms: {len(ONTOLOGY_ROWS)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
