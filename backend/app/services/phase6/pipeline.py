from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import (
    CompositionAgent,
    ConceptMapperAgent,
    ExtractionAgent,
    IndexerAgent,
    NormalizerAgent,
    RelationArbiterAgent,
    ScoringAgent,
    VerifierAgent,
)
from .taxonomy import Phase6Taxonomy


@dataclass(slots=True)
class Phase6PipelineStats:
    businesses_processed: int = 0
    spans_extracted: int = 0
    claims_mapped: int = 0
    claims_verified: int = 0


class Phase6PrecisionPipeline:
    """Phase A deterministic nightly precompute pipeline."""

    def __init__(self, taxonomy: Phase6Taxonomy | None = None):
        self.taxonomy = taxonomy or Phase6Taxonomy()
        self.extraction_agent = ExtractionAgent()
        self.normalizer_agent = NormalizerAgent()
        self.mapper_agent = ConceptMapperAgent(taxonomy=self.taxonomy)
        self.relation_arbiter_agent = RelationArbiterAgent(taxonomy=self.taxonomy)
        self.composition_agent = CompositionAgent()
        self.scoring_agent = ScoringAgent()
        self.indexer_agent = IndexerAgent()
        self.verifier_agent = VerifierAgent()

    def _load_business_inputs(self, session: Session, business_id: int) -> tuple[Any | None, list[Any], list[Any], list[Any]]:
        from ...models import Business, BusinessSource, EvidencePacket, MenuItem

        business = session.get(Business, business_id)
        if business is None:
            return None, [], [], []

        evidence_packets = session.execute(
            select(EvidencePacket).where(EvidencePacket.business_id == business_id).order_by(EvidencePacket.id.asc())
        ).scalars().all()
        menu_items = session.execute(
            select(MenuItem).where(MenuItem.business_id == business_id).order_by(MenuItem.id.asc())
        ).scalars().all()
        business_sources = session.execute(
            select(BusinessSource).where(BusinessSource.business_id == business_id).order_by(BusinessSource.id.asc())
        ).scalars().all()
        return business, evidence_packets, menu_items, business_sources

    def process_business(self, *, session: Session, business_id: int) -> tuple[int, int, int]:
        business, evidence_packets, menu_items, business_sources = self._load_business_inputs(session, business_id)
        if business is None:
            return 0, 0, 0

        spans = self.extraction_agent.extract(
            business=business,
            evidence_packets=evidence_packets,
            menu_items=menu_items,
            business_sources=business_sources,
        )
        normalized_spans = self.normalizer_agent.normalize(spans)

        claims = self.mapper_agent.map(normalized_spans)
        claims = self.relation_arbiter_agent.apply(claims)
        claims = self.composition_agent.apply(claims)
        claims = self.scoring_agent.score(claims)

        self.indexer_agent.index(
            session=session,
            business=business,
            claims=claims,
            normalized_spans=normalized_spans,
        )
        verified = self.verifier_agent.verify(session=session, business=business, claims=claims)
        return len(claims), len(verified), len(normalized_spans)

    def run(
        self,
        *,
        session: Session,
        business_ids: list[int] | None = None,
        limit: int | None = None,
    ) -> Phase6PipelineStats:
        from ...models import Business

        stats = Phase6PipelineStats()

        stmt = select(Business.id).order_by(Business.id.asc())
        if business_ids:
            stmt = stmt.where(Business.id.in_(business_ids))
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        target_ids = [int(row[0]) for row in session.execute(stmt).all()]
        for business_id in target_ids:
            claim_count, verified_count, span_count = self.process_business(session=session, business_id=business_id)
            stats.businesses_processed += 1
            stats.claims_mapped += claim_count
            stats.claims_verified += verified_count
            stats.spans_extracted += span_count

        return stats
