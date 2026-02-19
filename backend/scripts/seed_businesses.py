from __future__ import annotations

import sys
import uuid
from datetime import time
from pathlib import Path

from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.models import Business, BusinessCapability, BusinessHour, BusinessSource, OntologyTerm
from app.db.session import SessionLocal
from app.phase1_semantic_pipeline.embeddings import embedding_service

NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")

BUSINESSES = [
    {
        "name": "Panaderia La Esperanza",
        "lat": 44.9699,
        "lng": -93.2715,
        "is_chain": False,
        "chain_name": None,
        "website": "https://la-esperanza.example",
        "phone": "+1-612-555-0101",
        "text": "Custom birthday cakes, celebration desserts, cake decorations, and bakery supplies.",
        "sources": [
            ("website", "https://la-esperanza.example"),
            ("public_directory", "https://directory.example/la-esperanza"),
        ],
        "capabilities": [
            ("birthday candle", 0.76),
            ("cake decoration", 0.89),
            ("baking supplies", 0.71),
        ],
    },
    {
        "name": "TechFix Phone Repair",
        "lat": 44.9800,
        "lng": -93.2635,
        "is_chain": False,
        "chain_name": None,
        "website": "https://techfix.example",
        "phone": "+1-612-555-0102",
        "text": "Phone repair services, USB cables, charging accessories, iPhone screen protectors and adapters.",
        "sources": [
            ("website", "https://techfix.example"),
            ("google_places", "https://maps.example/techfix"),
        ],
        "capabilities": [
            ("usb-c to lightning cable", 0.93),
            ("phone charger", 0.9),
            ("screen protector", 0.88),
        ],
    },
    {
        "name": "Midwest Camera Exchange",
        "lat": 44.9751,
        "lng": -93.2566,
        "is_chain": False,
        "chain_name": None,
        "website": "https://midwestcamera.example",
        "phone": "+1-612-555-0103",
        "text": "Film cameras, 35mm film rolls, camera batteries, chargers, photo printing, and camera accessories.",
        "sources": [
            ("website", "https://midwestcamera.example"),
            ("public_directory", "https://directory.example/midwestcamera"),
        ],
        "capabilities": [
            ("35mm film roll", 0.94),
            ("camera battery charger", 0.87),
            ("camera strap", 0.78),
            ("photo printing", 0.82),
        ],
    },
    {
        "name": "Joe's Hardware",
        "lat": 44.9881,
        "lng": -93.2741,
        "is_chain": False,
        "chain_name": None,
        "website": "https://joeshardware.example",
        "phone": "+1-612-555-0104",
        "text": "Hardware tools, moving supplies, packaging supplies, packing tape, and hand tools.",
        "sources": [
            ("website", "https://joeshardware.example"),
            ("google_places", "https://maps.example/joeshardware"),
        ],
        "capabilities": [
            ("packing tape", 0.91),
            ("moving box tape", 0.84),
            ("precision screwdriver", 0.83),
        ],
    },
    {
        "name": "Jeff's Electronics",
        "lat": 44.9640,
        "lng": -93.2488,
        "is_chain": False,
        "chain_name": None,
        "website": "https://jeffselectronics.example",
        "phone": "+1-612-555-0105",
        "text": "Electronics accessories, AA batteries, charging cables, USB adapters, and portable power.",
        "sources": [
            ("website", "https://jeffselectronics.example"),
            ("public_directory", "https://directory.example/jeffs-electronics"),
        ],
        "capabilities": [
            ("aa batteries", 0.92),
            ("phone charger", 0.85),
            ("usb cable", 0.8),
        ],
    },
    {
        "name": "Andy's Moving Supply",
        "lat": 44.9568,
        "lng": -93.2689,
        "is_chain": False,
        "chain_name": None,
        "website": "https://andysmoving.example",
        "phone": "+1-612-555-0106",
        "text": "Moving and storage supplies including boxes, bubble wrap, packing tape, and shipping materials.",
        "sources": [
            ("website", "https://andysmoving.example"),
            ("public_directory", "https://directory.example/andys-moving"),
        ],
        "capabilities": [
            ("moving supplies", 0.88),
            ("boxes", 0.83),
            ("bubble wrap", 0.82),
            ("packing tape", 0.79),
        ],
    },
    {
        "name": "Vikings Bakery",
        "lat": 44.9834,
        "lng": -93.2444,
        "is_chain": False,
        "chain_name": None,
        "website": "https://vikingsbakery.example",
        "phone": "+1-612-555-0107",
        "text": "Birthday cakes, celebration cakes, and custom candle-ready cake decoration services.",
        "sources": [
            ("website", "https://vikingsbakery.example"),
            ("google_places", "https://maps.example/vikingsbakery"),
        ],
        "capabilities": [
            ("birthday cake candles", 0.86),
            ("cake decoration", 0.87),
        ],
    },
    {
        "name": "Abdul's Phone Repair MOA Kiosk #3",
        "lat": 44.8554,
        "lng": -93.2422,
        "is_chain": False,
        "chain_name": None,
        "website": "https://abdulsrepair.example",
        "phone": "+1-612-555-0108",
        "text": "Phone repair, screen protectors, charging cables, and mobile accessories for iPhone and Android.",
        "sources": [
            ("website", "https://abdulsrepair.example"),
            ("public_directory", "https://directory.example/abduls-repair"),
        ],
        "capabilities": [
            ("screen protector", 0.9),
            ("usb-c to lightning cable", 0.82),
            ("phone accessory", 0.8),
        ],
    },
    {
        "name": "Best Buy Downtown",
        "lat": 44.9717,
        "lng": -93.2869,
        "is_chain": True,
        "chain_name": "Best Buy",
        "website": "https://bestbuy.example",
        "phone": "+1-612-555-0109",
        "text": "National electronics retail with broad inventory for cables, batteries, chargers, and accessories.",
        "sources": [
            ("website", "https://bestbuy.example"),
            ("google_places", "https://maps.example/bestbuy-downtown"),
        ],
        "capabilities": [
            ("usb cable", 0.85),
            ("aa batteries", 0.9),
            ("phone charger", 0.88),
        ],
    },
]


def business_id_from_name(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, name)


def main() -> None:
    session = SessionLocal()
    try:
        available_terms = {row[0] for row in session.execute(select(OntologyTerm.term)).all()}

        for item in BUSINESSES:
            business_id = business_id_from_name(item["name"])
            embedding = embedding_service.embed_text(item["text"])

            business = session.get(Business, business_id)
            if business is None:
                business = Business(
                    id=business_id,
                    name=item["name"],
                    lat=item["lat"],
                    lng=item["lng"],
                    text_content=item["text"],
                    embedding=embedding,
                    is_chain=item["is_chain"],
                    chain_name=item["chain_name"],
                    website=item["website"],
                    phone=item["phone"],
                )
                session.add(business)
            else:
                business.name = item["name"]
                business.lat = item["lat"]
                business.lng = item["lng"]
                business.text_content = item["text"]
                business.embedding = embedding
                business.is_chain = item["is_chain"]
                business.chain_name = item["chain_name"]
                business.website = item["website"]
                business.phone = item["phone"]

            session.flush()

            session.execute(delete(BusinessSource).where(BusinessSource.business_id == business_id))
            for source_type, source_url in item["sources"]:
                session.add(
                    BusinessSource(
                        business_id=business_id,
                        source_type=source_type,
                        source_url=source_url,
                    )
                )

            session.execute(delete(BusinessCapability).where(BusinessCapability.business_id == business_id))
            for term, confidence in item["capabilities"]:
                if term not in available_terms:
                    continue
                session.add(
                    BusinessCapability(
                        business_id=business_id,
                        ontology_term=term,
                        confidence_score=confidence,
                        source_reference=item["website"],
                        source_snippet=item["text"],
                        semantic_similarity_score=confidence,
                        ontology_matches={"seed": [term]},
                    )
                )

            session.execute(delete(BusinessHour).where(BusinessHour.business_id == business_id))
            for day in range(7):
                opens = time(hour=9, minute=0)
                closes = time(hour=20, minute=0)
                if business.is_chain:
                    opens = time(hour=8, minute=0)
                    closes = time(hour=22, minute=0)
                session.add(
                    BusinessHour(
                        business_id=business_id,
                        day_of_week=day,
                        opens_at=opens,
                        closes_at=closes,
                        timezone="America/Chicago",
                    )
                )

        session.commit()
        print(f"Seeded businesses: {len(BUSINESSES)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
