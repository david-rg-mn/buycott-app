#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select

from common import get_session, utcnow
from openclaw.inference import InferenceLayer, OntologyNormalizationService
from openclaw.runtime import (
    OpenClawSessions,
    RetryingHttpClient,
    RouteDecision,
    SourceCandidate,
    build_scraper_registry,
    ensure_docker_sandbox,
    normalize_text,
    sanitize_public_text,
    text_hash,
)

ROOT = Path(__file__).resolve().parents[1]


@dataclass(slots=True)
class PipelineStats:
    businesses_processed: int = 0
    sources_routed: int = 0
    source_docs_inserted: int = 0
    source_docs_skipped_duplicate: int = 0
    claims_written: int = 0
    menu_items_written: int = 0
    capabilities_written: int = 0


class Phase5Pipeline:
    def __init__(
        self,
        *,
        allow_host_execution: bool,
        max_workers: int,
        max_sources_per_business: int,
    ) -> None:
        ensure_docker_sandbox(allow_host_execution=allow_host_execution)
        self.max_sources_per_business = max_sources_per_business
        self.http_client = RetryingHttpClient(timeout_seconds=30.0, max_attempts=4, base_backoff_seconds=1.0)
        self.sessions = OpenClawSessions(max_workers=max_workers)
        self.scrapers = build_scraper_registry(self.http_client)
        self.stats = PipelineStats()

    def close(self) -> None:
        self.sessions.close()
        self.http_client.close()

    @staticmethod
    def _inject_backend_path() -> None:
        backend_path = ROOT / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

    def _resolve_sources(self, business: Any, BusinessSource: Any) -> list[SourceCandidate]:
        candidates: list[SourceCandidate] = []
        seen_urls: set[str] = set()

        def _add(url: str | None, source_type: str, snippet: str) -> None:
            if not url:
                return
            normalized = url.strip()
            if not normalized or normalized in seen_urls:
                return
            seen_urls.add(normalized)
            candidates.append(
                SourceCandidate(
                    source_url=normalized,
                    source_type=source_type,
                    discovered_from="business_profile",
                    source_snippet=snippet[:350],
                )
            )

        _add(business.website, "website", f"{business.name} official website")
        for row in business.sources:
            _add(row.source_url, row.source_type, row.snippet or f"{business.name} source")

        # URL hints from text_content for menu-like links.
        text_content = business.text_content if isinstance(business.text_content, str) else ""
        for token in text_content.split():
            if token.startswith("http://") or token.startswith("https://"):
                _add(token.strip(".,;)]}"), "website", "URL discovered from text_content")

        # If no known source is available, use Google place permalink as low-trust fallback.
        if not candidates and business.google_place_id:
            permalink = f"https://www.google.com/maps/place/?q=place_id:{business.google_place_id}"
            _add(permalink, "directory", "Google Place permalink")

        return candidates[: self.max_sources_per_business]

    def _route_sources(self, sources: list[SourceCandidate]) -> list[RouteDecision]:
        from openclaw.runtime import RouterMasterAgent

        router = RouterMasterAgent(http_client=self.http_client)
        decisions: list[RouteDecision] = []
        for source in sources:
            decision = router.detect(source)
            decisions.append(decision)
            self.stats.sources_routed += 1
        return decisions

    def _spawn_scrapers(self, decisions: list[RouteDecision]) -> list[Any]:
        for decision in decisions:
            for modality in decision.spawn_modalities:
                scraper = self.scrapers.get(modality)
                if scraper is None:
                    continue
                self.sessions.spawn(
                    agent_name=f"{modality}-scraper",
                    fn=lambda scraper=scraper, source=decision.source, probe=decision.probe: scraper.run(
                        source=source,
                        probe=probe,
                    ),
                    source=decision.source,
                )

        completed: list[Any] = []
        for task, result in self.sessions.drain():
            completed.append((task, result))
        return completed

    def _upsert_source_document(self, session: Any, SourceDocument: Any, *, business_id: int, result: Any) -> bool:
        if not result.content_hash:
            return True
        stmt = select(SourceDocument).where(
            SourceDocument.business_id == business_id,
            SourceDocument.source_url == result.source.source_url,
            SourceDocument.content_hash == result.content_hash,
        )
        existing = session.execute(stmt).scalar_one_or_none()
        if existing is not None:
            self.stats.source_docs_skipped_duplicate += 1
            return False

        session.add(
            SourceDocument(
                business_id=business_id,
                source_url=result.source.source_url,
                modality=result.modality,
                etag=None,
                content_hash=result.content_hash,
                http_status=result.status_code,
                fetched_at=utcnow(),
            )
        )
        self.stats.source_docs_inserted += 1
        return True

    def _write_evidence(self, session: Any, EvidencePacket: Any, *, business_id: int, result: Any) -> list[Any]:
        created_rows: list[Any] = []
        for claim in result.claims:
            sanitized_claim = sanitize_public_text(claim.claim_text)
            claim_key = text_hash(f"{result.source.source_url}|{normalize_text(sanitized_claim)}")

            stmt = select(EvidencePacket).where(
                EvidencePacket.business_id == business_id,
                EvidencePacket.source_url == result.source.source_url,
                EvidencePacket.claim_hash == claim_key,
            )
            existing = session.execute(stmt).scalar_one_or_none()
            payload = {
                "source_type": claim.source_type,
                "modality": claim.modality,
                "source_url": claim.source_url,
                "source_snippet": sanitize_public_text(claim.source_snippet or result.source.source_snippet),
                "claim_text": sanitized_claim,
                "sanitized_claim_text": sanitized_claim,
                "claim_hash": claim_key,
                "extraction_confidence": claim.extraction_confidence,
                "credibility_score": claim.credibility_score,
                "metadata_json": claim.metadata,
                "content_hash": claim.content_hash or result.content_hash,
            }
            if existing is None:
                row = EvidencePacket(
                    business_id=business_id,
                    **payload,
                )
                session.add(row)
                created_rows.append(row)
                self.stats.claims_written += 1
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
                created_rows.append(existing)
        return created_rows

    def _write_menu_items(self, session: Any, MenuItem: Any, *, business_id: int, result: Any) -> list[Any]:
        written_rows: list[Any] = []
        for item in result.menu_items:
            sanitized_name = sanitize_public_text(item.item_name)
            sanitized_desc = sanitize_public_text(item.description) if item.description else None
            row_claim_hash = text_hash(
                f"{result.source.source_url}|{normalize_text(sanitized_name)}|{item.price if item.price is not None else 'na'}"
            )
            stmt = select(MenuItem).where(
                MenuItem.business_id == business_id,
                MenuItem.claim_hash == row_claim_hash,
            )
            existing = session.execute(stmt).scalar_one_or_none()
            payload = {
                "source_type": item.source_type,
                "source_url": item.source_url,
                "source_snippet": sanitize_public_text(item.source_snippet),
                "section": sanitize_public_text(item.section) if item.section else None,
                "item_name": sanitized_name,
                "description": sanitized_desc,
                "price": item.price,
                "currency": item.currency,
                "dietary_tags": [sanitize_public_text(tag) for tag in item.dietary_tags],
                "raw_text": sanitize_public_text(item.raw_text),
                "claim_hash": row_claim_hash,
                "extraction_confidence": item.extraction_confidence,
                "credibility_score": item.credibility_score,
                "last_updated": utcnow(),
            }
            if existing is None:
                row = MenuItem(
                    business_id=business_id,
                    **payload,
                )
                session.add(row)
                written_rows.append(row)
                self.stats.menu_items_written += 1
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
                written_rows.append(existing)
        return written_rows

    def _upsert_capabilities(
        self,
        session: Any,
        *,
        business: Any,
        capabilities: list[Any],
        CapabilityProfile: Any,
        BusinessCapability: Any,
        OntologyTerm: Any,
        embedding_service: Any,
    ) -> int:
        session.execute(delete(CapabilityProfile).where(CapabilityProfile.business_id == business.id))
        session.execute(delete(BusinessCapability).where(BusinessCapability.business_id == business.id))

        capability_count = 0
        legacy_terms_seen: set[str] = set()
        for cap in capabilities:
            embedding = embedding_service.encode(cap.canonical_text)
            session.add(
                CapabilityProfile(
                    business_id=business.id,
                    capability_type=cap.capability_type,
                    canonical_items=cap.canonical_items,
                    source_claim_ids=cap.source_claim_ids,
                    confidence_score=cap.confidence_score,
                    evidence_score=cap.evidence_score,
                    canonical_text=cap.canonical_text,
                    embedding=embedding,
                    last_updated=utcnow(),
                )
            )
            capability_count += 1

            # Maintain compatibility with existing API endpoint backed by business_capabilities.
            for term in cap.canonical_items:
                legacy = session.execute(
                    select(OntologyTerm).where(func.lower(OntologyTerm.term) == normalize_text(term))
                ).scalar_one_or_none()
                if legacy is None:
                    continue
                legacy_key = normalize_text(legacy.term)
                if legacy_key in legacy_terms_seen:
                    continue
                legacy_terms_seen.add(legacy_key)
                session.add(
                    BusinessCapability(
                        business_id=business.id,
                        ontology_term=legacy.term,
                        confidence_score=cap.confidence_score,
                        source_reference=f"phase5:{cap.capability_type}",
                        last_updated=utcnow(),
                    )
                )
        return capability_count

    def _embed_menu_items(self, *, session: Any, menu_rows: list[Any], embedding_service: Any) -> None:
        if not menu_rows:
            return
        texts = [
            f"{row.item_name}. {row.description or ''}. {', '.join(row.dietary_tags or [])}".strip()
            for row in menu_rows
        ]
        vectors = embedding_service.encode_many(texts)
        for row, vector in zip(menu_rows, vectors, strict=False):
            row.embedding = vector
            row.last_updated = utcnow()

    def _build_business_summary_text(self, business: Any, capability_rows: list[Any], menu_rows: list[Any]) -> str:
        summary_parts: list[str] = [business.name]
        summary_parts.extend(row.canonical_text for row in capability_rows[:12])
        top_menu = [row.item_name for row in menu_rows[:20] if isinstance(row.item_name, str)]
        if top_menu:
            summary_parts.append("menu_items: " + ", ".join(top_menu))
        return ". ".join(summary_parts)

    def run_for_business(self, *, session: Any, business: Any, models: dict[str, Any], embedding_service: Any) -> None:
        sources = self._resolve_sources(business, models["BusinessSource"])
        if not sources:
            return

        decisions = self._route_sources(sources)
        task_results = self._spawn_scrapers(decisions)

        for _task, result in task_results:
            self._upsert_source_document(
                session=session,
                SourceDocument=models["SourceDocument"],
                business_id=business.id,
                result=result,
            )
            self._write_evidence(
                session=session,
                EvidencePacket=models["EvidencePacket"],
                business_id=business.id,
                result=result,
            )
            self._write_menu_items(
                session=session,
                MenuItem=models["MenuItem"],
                business_id=business.id,
                result=result,
            )

        session.flush()
        evidence_rows = session.execute(
            select(models["EvidencePacket"])
            .where(models["EvidencePacket"].business_id == business.id)
            .order_by(models["EvidencePacket"].id.asc())
        ).scalars().all()
        menu_rows = session.execute(
            select(models["MenuItem"])
            .where(models["MenuItem"].business_id == business.id)
            .order_by(models["MenuItem"].id.asc())
        ).scalars().all()

        self._embed_menu_items(session=session, menu_rows=menu_rows, embedding_service=embedding_service)

        normalizer = OntologyNormalizationService(session=session, embedding_service=embedding_service)
        normalizer.refresh()
        inference = InferenceLayer(normalizer=normalizer)
        capability_drafts = inference.build_capabilities(evidence_packets=evidence_rows, menu_items=menu_rows)
        capability_count = self._upsert_capabilities(
            session=session,
            business=business,
            capabilities=capability_drafts,
            CapabilityProfile=models["CapabilityProfile"],
            BusinessCapability=models["BusinessCapability"],
            OntologyTerm=models["OntologyTerm"],
            embedding_service=embedding_service,
        )
        self.stats.capabilities_written += capability_count

        capability_rows = session.execute(
            select(models["CapabilityProfile"])
            .where(models["CapabilityProfile"].business_id == business.id)
            .order_by(models["CapabilityProfile"].id.asc())
        ).scalars().all()

        summary_text = self._build_business_summary_text(
            business=business,
            capability_rows=capability_rows,
            menu_rows=menu_rows,
        )
        business.canonical_summary_text = summary_text
        business.embedding = embedding_service.encode(summary_text)
        business.last_updated = utcnow()
        session.flush()
        self.stats.businesses_processed += 1

    def run(
        self,
        *,
        business_ids: list[int],
        place_ids: list[str],
        limit: int | None,
    ) -> PipelineStats:
        self._inject_backend_path()
        from app.models import (
            Business,
            BusinessCapability,
            BusinessSource,
            CapabilityProfile,
            EvidencePacket,
            MenuItem,
            OntologyTerm,
            SourceDocument,
        )
        from app.services.embedding_service import get_embedding_service

        embedding_service = get_embedding_service()
        session = get_session()
        models = {
            "BusinessSource": BusinessSource,
            "BusinessCapability": BusinessCapability,
            "CapabilityProfile": CapabilityProfile,
            "EvidencePacket": EvidencePacket,
            "MenuItem": MenuItem,
            "OntologyTerm": OntologyTerm,
            "SourceDocument": SourceDocument,
        }
        try:
            stmt = select(Business).order_by(Business.id.asc())
            if business_ids:
                stmt = stmt.where(Business.id.in_(business_ids))
            if place_ids:
                stmt = stmt.where(Business.google_place_id.in_(place_ids))
            if not business_ids and not place_ids:
                stmt = stmt.where(Business.google_place_id.is_not(None))
            if limit is not None and limit > 0:
                stmt = stmt.limit(limit)
            rows = session.execute(stmt).scalars().all()

            for business in rows:
                self.run_for_business(session=session, business=business, models=models, embedding_service=embedding_service)
            session.commit()
            return self.stats
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 5 OpenClaw multi-agent pipeline for menu and business signal expansion."
    )
    parser.add_argument(
        "--business-id",
        action="append",
        type=int,
        default=[],
        help="Business id to process (can be passed multiple times).",
    )
    parser.add_argument(
        "--google-place-id",
        action="append",
        default=[],
        help="Google place id to process (can be passed multiple times).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of businesses to process when ids are not provided.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=6,
        help="Max concurrent sub-agents (sessions.spawn worker pool).",
    )
    parser.add_argument(
        "--max-sources-per-business",
        type=int,
        default=8,
        help="Cap source fanout per business before router dispatch.",
    )
    parser.add_argument(
        "--allow-host-execution",
        action="store_true",
        help="Override Docker sandbox requirement (not recommended).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    pipeline = Phase5Pipeline(
        allow_host_execution=args.allow_host_execution,
        max_workers=max(1, args.max_workers),
        max_sources_per_business=max(1, args.max_sources_per_business),
    )
    try:
        stats = pipeline.run(
            business_ids=args.business_id,
            place_ids=args.google_place_id,
            limit=args.limit,
        )
        print(
            "Phase 5 OpenClaw pipeline complete: "
            f"businesses_processed={stats.businesses_processed}, "
            f"sources_routed={stats.sources_routed}, "
            f"source_docs_inserted={stats.source_docs_inserted}, "
            f"source_docs_skipped_duplicate={stats.source_docs_skipped_duplicate}, "
            f"claims_written={stats.claims_written}, "
            f"menu_items_written={stats.menu_items_written}, "
            f"capabilities_written={stats.capabilities_written}"
        )
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
