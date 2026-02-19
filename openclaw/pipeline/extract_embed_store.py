from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import delete, select

from app.db.models import Business, BusinessCapability, BusinessSource, OntologyTerm
from app.db.session import SessionLocal
from app.phase1_semantic_pipeline.embeddings import cosine_similarity, embedding_service
from openclaw.agents.public_business_agent import PublicBusinessExtractionAgent, PublicBusinessSeed

NAMESPACE = uuid.UUID("87654321-4321-6789-4321-678943216789")


def _seed_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "public_sources.json"


def load_seeds() -> list[PublicBusinessSeed]:
    payload = json.loads(_seed_path().read_text())
    seeds: list[PublicBusinessSeed] = []
    for row in payload["businesses"]:
        seeds.append(
            PublicBusinessSeed(
                name=row["name"],
                lat=row["lat"],
                lng=row["lng"],
                source_urls=row["source_urls"],
                fallback_text=row["fallback_text"],
                phone=row.get("phone"),
            )
        )
    return seeds


def make_business_id(name: str, lat: float, lng: float) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{name}:{lat}:{lng}")


def _derive_capabilities(
    extracted_text: str,
    business_embedding: list[float],
    ontology_rows: list[tuple[str, list[float]]],
    threshold: float = 0.48,
) -> list[tuple[str, float]]:
    text_lower = extracted_text.lower()
    capabilities: list[tuple[str, float]] = []

    for term, embedding in ontology_rows:
        similarity = cosine_similarity(business_embedding, embedding)
        if term.lower() in text_lower:
            similarity = min(1.0, similarity + 0.08)
        if similarity >= threshold:
            capabilities.append((term, similarity))

    capabilities.sort(key=lambda x: x[1], reverse=True)
    return capabilities[:12]


def main() -> None:
    agent = PublicBusinessExtractionAgent()
    seeds = load_seeds()

    session = SessionLocal()
    try:
        ontology_rows = session.execute(select(OntologyTerm.term, OntologyTerm.embedding)).all()

        for seed in seeds:
            extracted = agent.extract(seed)
            business_id = make_business_id(extracted.name, extracted.lat, extracted.lng)
            embedding = embedding_service.embed_text(extracted.extracted_text)

            business = session.get(Business, business_id)
            primary_source = extracted.source_urls[0] if extracted.source_urls else None
            if business is None:
                business = Business(
                    id=business_id,
                    name=extracted.name,
                    lat=extracted.lat,
                    lng=extracted.lng,
                    text_content=extracted.extracted_text,
                    embedding=embedding,
                    is_chain=extracted.is_chain,
                    chain_name=extracted.chain_name,
                    website=primary_source,
                    phone=extracted.phone,
                )
                session.add(business)
            else:
                business.name = extracted.name
                business.lat = extracted.lat
                business.lng = extracted.lng
                business.text_content = extracted.extracted_text
                business.embedding = embedding
                business.is_chain = extracted.is_chain
                business.chain_name = extracted.chain_name
                business.website = primary_source
                business.phone = extracted.phone

            session.flush()

            session.execute(delete(BusinessSource).where(BusinessSource.business_id == business_id))
            for url in extracted.source_urls:
                source_type = "website" if "//" in url else "public_directory"
                session.add(
                    BusinessSource(
                        business_id=business_id,
                        source_type=source_type,
                        source_url=url,
                    )
                )

            session.execute(delete(BusinessCapability).where(BusinessCapability.business_id == business_id))
            derived = _derive_capabilities(extracted.extracted_text, embedding, ontology_rows)
            for term, confidence in derived:
                session.add(
                    BusinessCapability(
                        business_id=business_id,
                        ontology_term=term,
                        confidence_score=round(confidence, 4),
                        source_reference=primary_source,
                        source_snippet=extracted.extracted_text[:800],
                        semantic_similarity_score=round(confidence, 4),
                        ontology_matches={"derived_from": [term]},
                    )
                )

        session.commit()
        print(f"OpenClaw extracted and stored {len(seeds)} businesses.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
