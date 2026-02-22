from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


@dataclass(slots=True)
class CapabilityDraft:
    capability_type: str
    canonical_items: list[str]
    source_claim_ids: list[int]
    confidence_score: float
    evidence_score: float
    canonical_text: str


class OntologyNormalizationService:
    def __init__(self, session: Session, embedding_service: Any):
        self.session = session
        self.embedding_service = embedding_service
        self._nodes_cache: list[Any] = []
        self._canonical_map: dict[str, Any] = {}
        self._synonym_map: dict[str, Any] = {}

    def _bootstrap_from_legacy_terms(self) -> None:
        from app.models import OntologyNode, OntologyTerm

        has_rows = self.session.execute(select(func.count(OntologyNode.id))).scalar_one()
        if int(has_rows) > 0:
            return

        terms = self.session.execute(select(OntologyTerm).order_by(OntologyTerm.id.asc())).scalars().all()
        if not terms:
            return

        nodes_by_term: dict[str, Any] = {}
        for term in terms:
            canonical = normalize_text(term.term)
            node = OntologyNode(
                canonical_term=canonical,
                source="seed_from_ontology_terms",
                synonyms=[canonical],
            )
            self.session.add(node)
            self.session.flush()
            nodes_by_term[canonical] = node

        for term in terms:
            canonical = normalize_text(term.term)
            parent = normalize_text(term.parent_term) if term.parent_term else None
            node = nodes_by_term.get(canonical)
            parent_node = nodes_by_term.get(parent) if parent else None
            if node is not None:
                node.parent_id = parent_node.id if parent_node else None

        self.session.flush()

    def refresh(self) -> None:
        from app.models import OntologyNode

        self._bootstrap_from_legacy_terms()
        self._nodes_cache = self.session.execute(select(OntologyNode).order_by(OntologyNode.id.asc())).scalars().all()
        self._canonical_map = {normalize_text(node.canonical_term): node for node in self._nodes_cache}
        self._synonym_map = {}
        for node in self._nodes_cache:
            synonyms = node.synonyms if isinstance(node.synonyms, list) else []
            for synonym in synonyms:
                if not isinstance(synonym, str):
                    continue
                self._synonym_map[normalize_text(synonym)] = node

    def _ensure_node_embeddings(self) -> None:
        missing = [node for node in self._nodes_cache if node.embedding is None]
        if not missing:
            return
        vectors = self.embedding_service.encode_many([node.canonical_term for node in missing])
        for node, vector in zip(missing, vectors, strict=False):
            node.embedding = vector
        self.session.flush()

    def _create_node(self, canonical_term: str) -> Any:
        from app.models import OntologyNode

        node = OntologyNode(
            canonical_term=canonical_term,
            source="auto_generated",
            synonyms=[canonical_term],
        )
        self.session.add(node)
        self.session.flush()
        self._nodes_cache.append(node)
        self._canonical_map[canonical_term] = node
        self._synonym_map[canonical_term] = node
        return node

    def _append_synonym(self, node: Any, synonym: str) -> None:
        current = node.synonyms if isinstance(node.synonyms, list) else []
        normalized_existing = {normalize_text(value) for value in current if isinstance(value, str)}
        if normalize_text(synonym) in normalized_existing:
            return
        current.append(synonym)
        node.synonyms = current
        self._synonym_map[normalize_text(synonym)] = node

    def normalize_term(self, raw_term: str) -> tuple[str, int, str]:
        candidate = normalize_text(raw_term)
        if not candidate:
            raise ValueError("Cannot normalize empty term")

        if not self._nodes_cache:
            self.refresh()

        exact = self._canonical_map.get(candidate)
        if exact is not None:
            return exact.canonical_term, exact.id, "exact_canonical"

        synonym_match = self._synonym_map.get(candidate)
        if synonym_match is not None:
            return synonym_match.canonical_term, synonym_match.id, "exact_synonym"

        fuzzy_node = None
        fuzzy_score = 0.0
        for node in self._nodes_cache:
            score = difflib.SequenceMatcher(a=candidate, b=normalize_text(node.canonical_term)).ratio()
            if score > fuzzy_score:
                fuzzy_score = score
                fuzzy_node = node
        if fuzzy_node is not None and fuzzy_score >= 0.84:
            self._append_synonym(fuzzy_node, raw_term)
            return fuzzy_node.canonical_term, fuzzy_node.id, "fuzzy_lexical"

        self._ensure_node_embeddings()
        if self._nodes_cache:
            term_vector = np.array(self.embedding_service.encode(candidate), dtype=np.float32)
            term_norm = np.linalg.norm(term_vector)
            if term_norm > 0:
                term_vector /= term_norm
                best_node = None
                best_score = -1.0
                for node in self._nodes_cache:
                    if node.embedding is None:
                        continue
                    node_vector = np.array(node.embedding, dtype=np.float32)
                    node_norm = np.linalg.norm(node_vector)
                    if node_norm == 0:
                        continue
                    similarity = float((node_vector / node_norm) @ term_vector)
                    if similarity > best_score:
                        best_score = similarity
                        best_node = node
                if best_node is not None and best_score >= 0.62:
                    self._append_synonym(best_node, raw_term)
                    return best_node.canonical_term, best_node.id, "embedding_similarity"

        # New terms still pass through normalization service and become canonical nodes.
        created = self._create_node(candidate)
        created.embedding = self.embedding_service.encode(candidate)
        self.session.flush()
        return created.canonical_term, created.id, "new_node"


class InferenceLayer:
    CAPABILITY_TYPES = ("sells", "services", "attributes", "operations", "suitability")

    SERVICE_KEYWORDS = {
        "catering": "catering",
        "delivery": "delivery",
        "pickup": "pickup",
        "takeout": "takeout",
        "reservation": "reservation",
        "repair": "repair",
        "custom": "custom order",
    }
    ATTRIBUTE_KEYWORDS = {
        "vegan": "vegan",
        "vegetarian": "vegetarian",
        "organic": "organic",
        "gluten": "gluten-free",
        "halal": "halal",
        "kosher": "kosher",
        "woman-owned": "woman-owned",
        "minority-owned": "minority-owned",
    }
    OPERATION_KEYWORDS = {
        "breakfast": "serves breakfast",
        "lunch": "serves lunch",
        "dinner": "serves dinner",
        "patio": "outdoor seating",
        "late night": "late night hours",
        "hours": "published hours",
    }
    SUITABILITY_KEYWORDS = {
        "family": "family-friendly",
        "kids": "kid-friendly",
        "date": "date-night suitable",
        "quick": "quick-service suitable",
    }

    def __init__(self, normalizer: OntologyNormalizationService):
        self.normalizer = normalizer

    @staticmethod
    def _unique_preserve(items: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for item in items:
            key = normalize_text(item)
            if not key or key in seen:
                continue
            seen.add(key)
            output.append(item)
        return output

    def _claim_terms(self, claim_text: str) -> dict[str, list[str]]:
        text = normalize_text(claim_text)
        output = {key: [] for key in self.CAPABILITY_TYPES}

        for keyword, canonical in self.SERVICE_KEYWORDS.items():
            if keyword in text:
                output["services"].append(canonical)
        for keyword, canonical in self.ATTRIBUTE_KEYWORDS.items():
            if keyword in text:
                output["attributes"].append(canonical)
        for keyword, canonical in self.OPERATION_KEYWORDS.items():
            if keyword in text:
                output["operations"].append(canonical)
        for keyword, canonical in self.SUITABILITY_KEYWORDS.items():
            if keyword in text:
                output["suitability"].append(canonical)

        if "extracted" in text and "menu item" in text:
            output["operations"].append("menu available")

        return output

    def _normalize_bucket_terms(self, terms: list[str]) -> list[str]:
        normalized: list[str] = []
        for term in terms:
            canonical, _node_id, _method = self.normalizer.normalize_term(term)
            normalized.append(canonical)
        return self._unique_preserve(normalized)

    def build_capabilities(
        self,
        *,
        evidence_packets: list[Any],
        menu_items: list[Any],
    ) -> list[CapabilityDraft]:
        # Always normalize through ontology layer before capability generation.
        buckets: dict[str, list[str]] = {key: [] for key in self.CAPABILITY_TYPES}
        sources: dict[str, set[int]] = {key: set() for key in self.CAPABILITY_TYPES}
        confidence_acc: dict[str, list[float]] = {key: [] for key in self.CAPABILITY_TYPES}
        evidence_acc: dict[str, list[float]] = {key: [] for key in self.CAPABILITY_TYPES}

        for item in menu_items:
            item_name = str(item.item_name).strip()
            if not item_name:
                continue
            buckets["sells"].append(item_name)
            sources["sells"].add(int(item.id))
            confidence_acc["sells"].append(float(item.extraction_confidence))
            evidence_acc["sells"].append(float(item.credibility_score))

            tags = item.dietary_tags if isinstance(item.dietary_tags, list) else []
            for tag in tags:
                if isinstance(tag, str):
                    buckets["attributes"].append(tag)
                    sources["attributes"].add(int(item.id))
                    confidence_acc["attributes"].append(float(item.extraction_confidence))
                    evidence_acc["attributes"].append(float(item.credibility_score))

        for packet in evidence_packets:
            claim_terms = self._claim_terms(str(packet.sanitized_claim_text))
            for cap_type, terms in claim_terms.items():
                if not terms:
                    continue
                buckets[cap_type].extend(terms)
                sources[cap_type].add(int(packet.id))
                confidence_acc[cap_type].append(float(packet.extraction_confidence))
                evidence_acc[cap_type].append(float(packet.credibility_score))

        output: list[CapabilityDraft] = []
        for cap_type in self.CAPABILITY_TYPES:
            normalized_terms = self._normalize_bucket_terms(buckets[cap_type])
            if not normalized_terms:
                continue

            avg_confidence = float(np.mean(confidence_acc[cap_type])) if confidence_acc[cap_type] else 0.5
            avg_evidence = float(np.mean(evidence_acc[cap_type])) if evidence_acc[cap_type] else 50.0
            canonical_text = f"{cap_type}: {', '.join(normalized_terms)}"
            output.append(
                CapabilityDraft(
                    capability_type=cap_type,
                    canonical_items=normalized_terms,
                    source_claim_ids=sorted(sources[cap_type]),
                    confidence_score=max(0.0, min(1.0, round(avg_confidence, 4))),
                    evidence_score=max(0.0, min(100.0, round(avg_evidence, 2))),
                    canonical_text=canonical_text,
                )
            )

        return output
