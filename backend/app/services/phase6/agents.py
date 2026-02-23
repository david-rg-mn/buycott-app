from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from math import log1p
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..business_model_service import normalize_business_model_document
from .contracts import ClaimDraft, EvidenceSpan
from .taxonomy import Phase6Taxonomy
from .utils import DeterministicVectorizer, ngrams, normalize_text, tokenize


class ExtractionAgent:
    """Collect raw spans and provenance from persisted business records."""

    def extract(
        self,
        *,
        business: Any,
        evidence_packets: list[Any],
        menu_items: list[Any],
        business_sources: list[Any],
    ) -> list[EvidenceSpan]:
        spans: list[EvidenceSpan] = []

        for item in menu_items:
            item_name = str(item.item_name or "").strip()
            if item_name:
                spans.append(
                    EvidenceSpan(
                        span_id=f"menu:{item.id}:name",
                        business_id=int(business.id),
                        text=item_name,
                        source_kind="menu_item",
                        source_id=f"menu:{item.id}",
                        source_url=getattr(item, "source_url", None),
                        snippet=str(getattr(item, "source_snippet", "") or item_name),
                        extraction_confidence=float(getattr(item, "extraction_confidence", 1.0)),
                        credibility_score=float(getattr(item, "credibility_score", 85.0)),
                        provenance={
                            "table": "menu_items",
                            "row_id": int(item.id),
                            "field": "item_name",
                        },
                    )
                )

            description = str(getattr(item, "description", "") or "").strip()
            if description:
                spans.append(
                    EvidenceSpan(
                        span_id=f"menu:{item.id}:description",
                        business_id=int(business.id),
                        text=description,
                        source_kind="menu_description",
                        source_id=f"menu:{item.id}",
                        source_url=getattr(item, "source_url", None),
                        snippet=str(getattr(item, "source_snippet", "") or description),
                        extraction_confidence=float(getattr(item, "extraction_confidence", 1.0)),
                        credibility_score=float(getattr(item, "credibility_score", 80.0)),
                        provenance={
                            "table": "menu_items",
                            "row_id": int(item.id),
                            "field": "description",
                        },
                    )
                )

        for packet in evidence_packets:
            claim_text = str(getattr(packet, "sanitized_claim_text", None) or getattr(packet, "claim_text", "")).strip()
            if not claim_text:
                continue
            spans.append(
                EvidenceSpan(
                    span_id=f"evidence:{packet.id}",
                    business_id=int(business.id),
                    text=claim_text,
                    source_kind="evidence_packet",
                    source_id=f"evidence:{packet.id}",
                    source_url=getattr(packet, "source_url", None),
                    snippet=str(getattr(packet, "source_snippet", "") or claim_text),
                    extraction_confidence=float(getattr(packet, "extraction_confidence", 0.7)),
                    credibility_score=float(getattr(packet, "credibility_score", 70.0)),
                    provenance={
                        "table": "evidence_packets",
                        "row_id": int(packet.id),
                        "field": "sanitized_claim_text",
                    },
                )
            )

        business_types = business.types if isinstance(getattr(business, "types", None), list) else []
        for idx, place_type in enumerate(business_types):
            if not isinstance(place_type, str):
                continue
            spans.append(
                EvidenceSpan(
                    span_id=f"type:{business.id}:{idx}",
                    business_id=int(business.id),
                    text=place_type,
                    source_kind="category_tag",
                    source_id=f"place_type:{idx}",
                    source_url=None,
                    snippet=place_type,
                    extraction_confidence=1.0,
                    credibility_score=72.0,
                    provenance={
                        "table": "businesses",
                        "row_id": int(business.id),
                        "field": "types",
                        "index": idx,
                    },
                )
            )

        business_name = str(getattr(business, "name", "") or "").strip()
        if business_name:
            spans.append(
                EvidenceSpan(
                    span_id=f"bizname:{business.id}",
                    business_id=int(business.id),
                    text=business_name,
                    source_kind="business_name",
                    source_id=f"business:{business.id}",
                    source_url=getattr(business, "website", None),
                    snippet=business_name,
                    extraction_confidence=1.0,
                    credibility_score=70.0,
                    provenance={
                        "table": "businesses",
                        "row_id": int(business.id),
                        "field": "name",
                    },
                )
            )

        content_text = str(getattr(business, "text_content", "") or "").strip()
        if content_text:
            spans.append(
                EvidenceSpan(
                    span_id=f"text:{business.id}",
                    business_id=int(business.id),
                    text=content_text,
                    source_kind="web_text",
                    source_id=f"text:{business.id}",
                    source_url=getattr(business, "website", None),
                    snippet=content_text[:300],
                    extraction_confidence=0.55,
                    credibility_score=55.0,
                    provenance={
                        "table": "businesses",
                        "row_id": int(business.id),
                        "field": "text_content",
                    },
                )
            )

        for src in business_sources:
            snippet = str(getattr(src, "snippet", "") or "").strip()
            if not snippet:
                continue
            spans.append(
                EvidenceSpan(
                    span_id=f"source:{src.id}",
                    business_id=int(business.id),
                    text=snippet,
                    source_kind="source_snippet",
                    source_id=f"source:{src.id}",
                    source_url=getattr(src, "source_url", None),
                    snippet=snippet,
                    extraction_confidence=0.6,
                    credibility_score=60.0,
                    provenance={
                        "table": "business_sources",
                        "row_id": int(src.id),
                        "field": "snippet",
                    },
                )
            )

        return spans


class NormalizerAgent:
    """Deterministic text normalization with accent-folding and n-gram expansion."""

    def normalize(self, spans: list[EvidenceSpan]) -> list[EvidenceSpan]:
        output: list[EvidenceSpan] = []
        for span in spans:
            normalized = normalize_text(span.text)
            if not normalized:
                continue
            span.normalized_text = normalized
            span.tokens = tokenize(normalized)
            span.ngrams = ngrams(span.tokens, min_n=1, max_n=4)
            output.append(span)
        return output


class ConceptMapperAgent:
    """Alias-table concept mapping without ML inference."""

    def __init__(self, taxonomy: Phase6Taxonomy):
        self.taxonomy = taxonomy

    def map(self, spans: list[EvidenceSpan]) -> dict[str, ClaimDraft]:
        claims: dict[str, ClaimDraft] = {}

        for span in spans:
            candidates = [span.normalized_text] + sorted(set(span.ngrams), key=len, reverse=True)
            seen_concepts: set[str] = set()

            for phrase in candidates:
                concept_id = self.taxonomy.concept_for_phrase(phrase)
                if concept_id is None or concept_id in seen_concepts:
                    continue
                seen_concepts.add(concept_id)

                claim = claims.setdefault(
                    concept_id,
                    ClaimDraft(claim_id=concept_id, label=self.taxonomy.label_for(concept_id)),
                )
                evidence_value = max(
                    0.0,
                    min(1.0, (float(span.extraction_confidence) + (float(span.credibility_score) / 100.0)) / 2.0),
                )
                claim.add_evidence(
                    {
                        "kind": span.source_kind,
                        "text": span.text,
                        "normalized": span.normalized_text,
                        "alias": phrase,
                        "evidence": round(evidence_value, 4),
                        "hops": 0,
                        "source_key": f"{span.source_id}|{span.source_url or ''}|{span.span_id}",
                        "source_id": span.source_id,
                        "source_url": span.source_url,
                        "provenance": span.provenance,
                    }
                )

        return claims


class RelationArbiterAgent:
    """Curated relation application with strict <=2-hop inference."""

    MAX_HOPS = 2

    def __init__(self, taxonomy: Phase6Taxonomy):
        self.taxonomy = taxonomy

    @staticmethod
    def _serialize_path(concepts: list[str], relations: list[str]) -> list[str]:
        payload: list[str] = []
        for idx, concept in enumerate(concepts):
            payload.append(concept)
            if idx < len(relations):
                payload.append(relations[idx])
        return payload

    def apply(self, claims: dict[str, ClaimDraft]) -> dict[str, ClaimDraft]:
        seed_concepts = list(claims.keys())
        for seed in seed_concepts:
            queue: deque[tuple[str, int, list[str], list[str]]] = deque()
            queue.append((seed, 0, [seed], []))
            best_depth: dict[str, int] = {seed: 0}

            while queue:
                node, depth, concept_path, relation_path = queue.popleft()
                if depth >= self.MAX_HOPS:
                    continue

                for edge in self.taxonomy.adjacency.get(node, []):
                    next_depth = depth + 1
                    if next_depth > self.MAX_HOPS:
                        continue

                    target = edge.target
                    existing_depth = best_depth.get(target)
                    if existing_depth is not None and existing_depth <= next_depth:
                        continue
                    best_depth[target] = next_depth

                    new_concept_path = concept_path + [target]
                    new_relation_path = relation_path + [edge.relation]
                    queue.append((target, next_depth, new_concept_path, new_relation_path))

                    if target == seed:
                        continue

                    seed_claim = claims.get(seed)
                    if seed_claim is None or not seed_claim.evidence:
                        continue

                    seed_strength = max(float(item.get("evidence") or 0.0) for item in seed_claim.evidence)
                    hop_penalty = 0.78 if next_depth == 1 else 0.58
                    inferred_strength = max(0.0, min(1.0, seed_strength * hop_penalty))

                    target_claim = claims.setdefault(
                        target,
                        ClaimDraft(claim_id=target, label=self.taxonomy.label_for(target)),
                    )
                    target_claim.is_inferred = True
                    target_claim.add_evidence(
                        {
                            "kind": "relation",
                            "path": self._serialize_path(new_concept_path, new_relation_path),
                            "from_claim": seed,
                            "relation": edge.relation,
                            "hops": next_depth,
                            "evidence": round(inferred_strength, 4),
                            "source_key": f"relation:{seed}:{target}:{next_depth}",
                            "source_id": f"relation:{seed}:{target}",
                            "source_url": None,
                            "provenance": {
                                "relation_provenance": edge.provenance,
                                "max_hops_enforced": self.MAX_HOPS,
                            },
                        }
                    )

        return claims


class CompositionAgent:
    """Deterministic composition rules with required multi-source support."""

    @staticmethod
    def _distinct_source_keys(evidence: list[dict[str, Any]]) -> set[str]:
        output: set[str] = set()
        for item in evidence:
            source_key = str(item.get("source_key") or "")
            if source_key:
                output.add(source_key)
        return output

    def apply(self, claims: dict[str, ClaimDraft]) -> dict[str, ClaimDraft]:
        taco_claim = claims.get("food.taco")
        if taco_claim is not None:
            for claim_id, filling_claim in list(claims.items()):
                if not claim_id.startswith("food.filling."):
                    continue
                filler = claim_id.split("food.filling.", 1)[1]
                composed_id = f"food.taco.filling.{filler}"
                source_keys = self._distinct_source_keys(taco_claim.evidence + filling_claim.evidence)
                if len(source_keys) < 2:
                    continue

                composed = claims.setdefault(
                    composed_id,
                    ClaimDraft(claim_id=composed_id, label=f"tacos de {filler.replace('_', ' ')}"),
                )
                composed.is_composed = True
                for item in taco_claim.evidence[:2] + filling_claim.evidence[:2]:
                    composed.add_evidence(dict(item))
                composed.add_evidence(
                    {
                        "kind": "composition",
                        "rule": "taco_filling",
                        "path": ["food.taco", "+", claim_id, "=>", composed_id],
                        "hops": 0,
                        "evidence": 0.92,
                        "source_key": f"composition:taco_filling:{filler}",
                        "source_id": "composition:taco_filling",
                        "source_url": None,
                        "provenance": {
                            "rule": "food.taco + food.filling.X => food.taco.filling.X",
                            "multi_source_required": True,
                            "source_count": len(source_keys),
                        },
                    }
                )

        nailpolish_claim = claims.get("service.nailpolish")
        pedicure_claim = claims.get("service.pedicure")
        if nailpolish_claim is not None and pedicure_claim is not None:
            source_keys = self._distinct_source_keys(nailpolish_claim.evidence + pedicure_claim.evidence)
            if len(source_keys) >= 2:
                combo_id = "service.pedi_mani_combo"
                combo = claims.setdefault(
                    combo_id,
                    ClaimDraft(claim_id=combo_id, label="pedi mani combo"),
                )
                combo.is_composed = True
                for item in nailpolish_claim.evidence[:2] + pedicure_claim.evidence[:2]:
                    combo.add_evidence(dict(item))
                combo.add_evidence(
                    {
                        "kind": "composition",
                        "rule": "pedi_mani_combo",
                        "path": ["service.nailpolish", "+", "service.pedicure", "=>", combo_id],
                        "hops": 0,
                        "evidence": 0.9,
                        "source_key": "composition:pedi_mani_combo",
                        "source_id": "composition:pedi_mani_combo",
                        "source_url": None,
                        "provenance": {
                            "rule": "service.nailpolish + service.pedicure => service.pedi_mani_combo",
                            "multi_source_required": True,
                            "source_count": len(source_keys),
                        },
                    }
                )

        return claims


class ScoringAgent:
    """Weighted evidence scoring: Score = sum(weight * evidence)."""

    WEIGHTS: dict[str, float] = {
        "menu_item": 0.65,
        "menu_description": 0.35,
        "evidence_packet": 0.58,
        "business_name": 0.42,
        "category_tag": 0.45,
        "web_text": 0.22,
        "source_snippet": 0.2,
        "relation": 0.28,
        "composition": 0.32,
    }

    INDEPENDENT_SUPPORT_WEIGHT = 0.24
    SCORE_CAP = 1.35

    def score(self, claims: dict[str, ClaimDraft]) -> dict[str, ClaimDraft]:
        now = datetime.now(UTC)

        for claim in claims.values():
            raw_score = 0.0
            for evidence in claim.evidence:
                weight = self.WEIGHTS.get(str(evidence.get("kind") or ""), 0.12)
                evidence_value = max(0.0, min(1.0, float(evidence.get("evidence") or 0.0)))
                raw_score += weight * evidence_value

            independent_support = min(1.0, max(0.0, (claim.source_count - 1) / 3.0))
            raw_score += self.INDEPENDENT_SUPPORT_WEIGHT * independent_support

            claim.score = round(raw_score, 4)
            claim.confidence = round(min(1.0, raw_score / self.SCORE_CAP), 4)
            claim.created_at = now

        return claims


class IndexerAgent:
    """Populate Layers 1-4 for deterministic precision retrieval."""

    def __init__(self, vectorizer: DeterministicVectorizer | None = None):
        self.vectorizer = vectorizer or DeterministicVectorizer(dim=384)

    @staticmethod
    def _feature_key(claim_id: str) -> str:
        parts = claim_id.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return claim_id

    @staticmethod
    def _slice_key(claim_id: str) -> str:
        if claim_id.startswith("food."):
            return "food"
        if claim_id.startswith("service."):
            return "service"
        if claim_id.startswith("biz.type."):
            return "business_type"
        if claim_id.startswith("biz.category."):
            return "business_category"
        parts = claim_id.split(".")
        return parts[0] if parts else "general"

    def index(
        self,
        *,
        session: Session,
        business: Any,
        claims: dict[str, ClaimDraft],
        normalized_spans: list[EvidenceSpan],
    ) -> None:
        from ...models import (
            BusinessMicrograph,
            EvidenceIndexTerm,
            GlobalFootprint,
            VerticalSlice,
        )

        claim_rows = sorted(claims.values(), key=lambda item: item.confidence, reverse=True)

        feature_weights: dict[str, float] = {}
        for claim in claim_rows:
            if claim.confidence < 0.35:
                continue
            key = self._feature_key(claim.claim_id)
            feature_weights[key] = feature_weights.get(key, 0.0) + log1p(claim.confidence * 8.0)

        if not feature_weights:
            feature_weights = {"fallback.none": 1.0}

        feature_vector = self.vectorizer.encode_weighted_terms(feature_weights)
        feature_flags = {key: round(value, 4) for key, value in sorted(feature_weights.items())}
        coverage_score = min(1.0, len(feature_flags) / 14.0)

        footprint = session.get(GlobalFootprint, int(business.id))
        if footprint is None:
            footprint = GlobalFootprint(
                business_id=int(business.id),
                feature_vector=feature_vector,
                feature_flags=feature_flags,
                coverage_score=coverage_score,
                updated_at=datetime.now(UTC),
            )
            session.add(footprint)
        else:
            footprint.feature_vector = feature_vector
            footprint.feature_flags = feature_flags
            footprint.coverage_score = coverage_score
            footprint.updated_at = datetime.now(UTC)

        session.execute(delete(VerticalSlice).where(VerticalSlice.business_id == business.id))
        by_slice: dict[str, dict[str, float]] = {}
        by_slice_terms: dict[str, set[str]] = {}

        for claim in claim_rows:
            if claim.confidence <= 0:
                continue
            slice_key = self._slice_key(claim.claim_id)
            category = self._feature_key(claim.claim_id)
            by_slice.setdefault(slice_key, {})
            by_slice[slice_key][category] = by_slice[slice_key].get(category, 0.0) + claim.confidence
            by_slice_terms.setdefault(slice_key, set()).add(claim.claim_id)

        for slice_key, weights in by_slice.items():
            session.add(
                VerticalSlice(
                    business_id=int(business.id),
                    slice_key=slice_key,
                    category_weights={key: round(value, 4) for key, value in sorted(weights.items())},
                    slice_terms=sorted(by_slice_terms.get(slice_key, set())),
                    updated_at=datetime.now(UTC),
                )
            )

        session.execute(delete(EvidenceIndexTerm).where(EvidenceIndexTerm.business_id == business.id))
        evidence_keys: set[tuple[str, str, str]] = set()
        for claim in claim_rows:
            for evidence in claim.evidence:
                normalized = str(evidence.get("normalized") or normalize_text(str(evidence.get("text") or ""))).strip()
                terms = set(tokenize(normalized) + tokenize(claim.label))
                for term in terms:
                    if len(term) < 2:
                        continue
                    source_kind = str(evidence.get("kind") or "unknown")
                    key = (term, claim.claim_id, source_kind)
                    if key in evidence_keys:
                        continue
                    evidence_keys.add(key)
                    session.add(
                        EvidenceIndexTerm(
                            business_id=int(business.id),
                            term=term,
                            claim_id=claim.claim_id,
                            source_kind=source_kind,
                            evidence_ref={
                                "source_id": evidence.get("source_id"),
                                "source_key": evidence.get("source_key"),
                                "text": evidence.get("text"),
                            },
                            provenance={
                                "claim_id": claim.claim_id,
                                "provenance": evidence.get("provenance") or {},
                            },
                            weight=max(0.0, min(1.0, claim.confidence)),
                        )
                    )

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        for claim in claim_rows:
            nodes.append(
                {
                    "id": claim.claim_id,
                    "label": claim.label,
                    "confidence": claim.confidence,
                    "score": claim.score,
                    "max_hops": claim.max_hops,
                    "is_inferred": claim.is_inferred,
                    "is_composed": claim.is_composed,
                    "source_count": claim.source_count,
                    "evidence": claim.evidence,
                }
            )
            for evidence in claim.evidence:
                if str(evidence.get("kind")) == "relation":
                    path = evidence.get("path")
                    if isinstance(path, list) and len(path) >= 3:
                        for idx in range(0, len(path) - 2, 2):
                            source = path[idx]
                            relation = path[idx + 1]
                            target = path[idx + 2]
                            if not isinstance(source, str) or not isinstance(relation, str) or not isinstance(target, str):
                                continue
                            edges.append(
                                {
                                    "source": source,
                                    "relation": relation,
                                    "target": target,
                                    "hops": int(evidence.get("hops") or 1),
                                    "provenance": evidence.get("provenance") or {},
                                }
                            )
                if str(evidence.get("kind")) == "composition":
                    path = evidence.get("path")
                    if isinstance(path, list) and len(path) >= 5:
                        left = path[0]
                        right = path[2]
                        target = path[4]
                        if isinstance(left, str) and isinstance(right, str) and isinstance(target, str):
                            edges.append(
                                {
                                    "source": left,
                                    "relation": "composes_with",
                                    "target": target,
                                    "hops": 1,
                                    "provenance": evidence.get("provenance") or {},
                                }
                            )
                            edges.append(
                                {
                                    "source": right,
                                    "relation": "composes_with",
                                    "target": target,
                                    "hops": 1,
                                    "provenance": evidence.get("provenance") or {},
                                }
                            )

        graph_json = {
            "business_id": int(business.id),
            "generated_at": datetime.now(UTC).isoformat(),
            "constraints": {
                "phase": "A",
                "ml_inference": False,
                "max_hops": 2,
                "global_ontology_changes": False,
            },
            "nodes": nodes,
            "edges": edges,
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "label": claim.label,
                    "score": claim.score,
                    "confidence": claim.confidence,
                    "source_count": claim.source_count,
                    "max_hops": claim.max_hops,
                    "is_composed": claim.is_composed,
                }
                for claim in claim_rows
            ],
            "span_count": len(normalized_spans),
            "business_model": normalize_business_model_document(
                business.business_model if isinstance(business.business_model, dict) else None
            ),
        }

        micrograph = session.get(BusinessMicrograph, int(business.id))
        if micrograph is None:
            micrograph = BusinessMicrograph(
                business_id=int(business.id),
                graph_json=graph_json,
                updated_at=datetime.now(UTC),
            )
            session.add(micrograph)
        else:
            micrograph.graph_json = graph_json
            micrograph.updated_at = datetime.now(UTC)


class VerifierAgent:
    """Populate Layer 5 verified-claim registry."""

    VERIFIED_THRESHOLD = 0.85

    def verify(
        self,
        *,
        session: Session | None,
        business: Any,
        claims: dict[str, ClaimDraft],
        persist: bool = True,
    ) -> list[dict[str, Any]]:
        VerifiedClaim = None
        if persist:
            from ...models import VerifiedClaim as VerifiedClaimModel

            VerifiedClaim = VerifiedClaimModel
            assert session is not None
            session.execute(delete(VerifiedClaim).where(VerifiedClaim.business_id == business.id))

        verified_payloads: list[dict[str, Any]] = []
        timestamp = datetime.now(UTC)
        claim_rows = sorted(claims.values(), key=lambda item: item.confidence, reverse=True)

        for claim in claim_rows:
            if claim.max_hops > 2:
                continue
            if not claim.direct_support:
                continue
            if claim.confidence < self.VERIFIED_THRESHOLD:
                continue
            if claim.source_count < 1:
                continue
            if claim.is_composed and claim.source_count < 2:
                continue

            has_traceable_provenance = any(bool(item.get("provenance")) for item in claim.evidence)
            if not has_traceable_provenance:
                continue

            payload = claim.as_verified_claim(timestamp=timestamp)
            verified_payloads.append(payload)
            if persist and VerifiedClaim is not None and session is not None:
                session.add(
                    VerifiedClaim(
                        business_id=int(business.id),
                        claim_id=payload["claim_id"],
                        label=payload["label"],
                        evidence=payload["evidence"],
                        confidence=float(payload["confidence"]),
                        timestamp=timestamp,
                        audit_chain={
                            "score": claim.score,
                            "source_count": claim.source_count,
                            "max_hops": claim.max_hops,
                            "direct_support": claim.direct_support,
                            "phase": "A",
                        },
                    )
                )

        return verified_payloads
