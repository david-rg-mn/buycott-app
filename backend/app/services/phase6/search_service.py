from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import settings
from ...models import (
    Business,
    BusinessMicrograph,
    EvidenceIndexTerm,
    GlobalFootprint,
    VerifiedClaim,
    VerticalSlice,
)
from ...services.distance_service import compute_travel_minutes, haversine_km
from ...services.time_service import is_open_now
from ..business_model_service import (
    BusinessModelFilters,
    normalize_business_model_document,
    passes_business_model_filters,
)
from .graph_utils import build_on_demand_subgraph, graph_adjacency
from .taxonomy import Phase6Taxonomy
from .utils import DeterministicVectorizer, normalize_text, tokenize


@dataclass
class PrecisionSearchParams:
    query: str
    lat: float
    lng: float
    include_chains: bool = False
    consumer_facing_only: bool = True
    include_service_area_businesses: bool = False
    require_delivery: bool = False
    require_takeout: bool = False
    require_dine_in: bool = False
    require_curbside_pickup: bool = False
    open_now: bool = False
    walking_distance: bool = False
    walking_threshold_minutes: int = settings.walking_threshold_minutes
    limit: int = settings.search_result_limit


class PrecisionSearchService:
    """Precision-weighted search over precomputed Phase A layers."""

    MAX_SUBGRAPH_HOPS = 2

    def __init__(self, taxonomy: Phase6Taxonomy | None = None):
        self.taxonomy = taxonomy or Phase6Taxonomy()
        self.vectorizer = DeterministicVectorizer(dim=384)

    @staticmethod
    def _to_business_model_filters(params: PrecisionSearchParams) -> BusinessModelFilters:
        return BusinessModelFilters(
            consumer_facing_only=params.consumer_facing_only,
            include_service_area_businesses=params.include_service_area_businesses,
            require_delivery=params.require_delivery,
            require_takeout=params.require_takeout,
            require_dine_in=params.require_dine_in,
            require_curbside_pickup=params.require_curbside_pickup,
            open_now=False,
        )

    @staticmethod
    def _places_open_now(business_model: dict) -> bool | None:
        value = (
            business_model.get("business_model", {})
            .get("operational", {})
            .get("open_now")
        )
        if isinstance(value, bool):
            return value
        return None

    def _query_concepts(self, query: str) -> list[str]:
        normalized = normalize_text(query)
        phrases = [normalized]
        query_tokens = tokenize(normalized)
        for width in range(1, min(4, len(query_tokens)) + 1):
            for start in range(0, len(query_tokens) - width + 1):
                phrases.append(" ".join(query_tokens[start : start + width]))

        concepts: list[str] = []
        seen: set[str] = set()
        for phrase in phrases:
            concept = self.taxonomy.concept_for_phrase(phrase)
            if concept and concept not in seen:
                seen.add(concept)
                concepts.append(concept)
        return concepts

    def _query_vector(self, query: str, query_concepts: list[str]) -> list[float]:
        weighted_terms: dict[str, float] = {}
        for concept in query_concepts:
            feature_key = ".".join(concept.split(".")[:2]) if "." in concept else concept
            weighted_terms[feature_key] = weighted_terms.get(feature_key, 0.0) + 1.0

        if not weighted_terms:
            for token in tokenize(query):
                weighted_terms[token] = weighted_terms.get(token, 0.0) + 1.0

        if not weighted_terms:
            weighted_terms[normalize_text(query) or "empty"] = 1.0

        return self.vectorizer.encode_weighted_terms(weighted_terms)

    def _layer1_candidates(
        self,
        db: Session,
        *,
        params: PrecisionSearchParams,
        query_vector: list[float],
    ) -> list[tuple[Business, float]]:
        distance_expr = GlobalFootprint.feature_vector.cosine_distance(query_vector)
        similarity_expr = (1 - distance_expr).label("similarity")

        stmt = (
            select(Business, similarity_expr)
            .join(GlobalFootprint, GlobalFootprint.business_id == Business.id)
            .where(GlobalFootprint.feature_vector.is_not(None))
            .order_by(distance_expr.asc())
            .limit(max(40, params.limit * 8))
        )
        if not params.include_chains:
            stmt = stmt.where(Business.is_chain.is_(False))

        rows = db.execute(stmt).all()
        output: list[tuple[Business, float]] = []
        for business, similarity in rows:
            if similarity is None:
                continue
            output.append((business, float(similarity)))
        return output

    @staticmethod
    def _fetch_vertical_map(db: Session, business_ids: list[int]) -> dict[int, list[VerticalSlice]]:
        if not business_ids:
            return {}
        rows = db.execute(select(VerticalSlice).where(VerticalSlice.business_id.in_(business_ids))).scalars().all()
        grouped: dict[int, list[VerticalSlice]] = defaultdict(list)
        for row in rows:
            grouped[int(row.business_id)].append(row)
        return grouped

    @staticmethod
    def _fetch_evidence_term_map(db: Session, business_ids: list[int]) -> dict[int, list[EvidenceIndexTerm]]:
        if not business_ids:
            return {}
        rows = db.execute(select(EvidenceIndexTerm).where(EvidenceIndexTerm.business_id.in_(business_ids))).scalars().all()
        grouped: dict[int, list[EvidenceIndexTerm]] = defaultdict(list)
        for row in rows:
            grouped[int(row.business_id)].append(row)
        return grouped

    @staticmethod
    def _fetch_micrographs(db: Session, business_ids: list[int]) -> dict[int, BusinessMicrograph]:
        if not business_ids:
            return {}
        rows = db.execute(select(BusinessMicrograph).where(BusinessMicrograph.business_id.in_(business_ids))).scalars().all()
        return {int(row.business_id): row for row in rows}

    @staticmethod
    def _fetch_verified_claims(db: Session, business_ids: list[int]) -> dict[int, list[VerifiedClaim]]:
        if not business_ids:
            return {}
        rows = db.execute(
            select(VerifiedClaim)
            .where(VerifiedClaim.business_id.in_(business_ids))
            .order_by(VerifiedClaim.business_id.asc(), VerifiedClaim.confidence.desc())
        ).scalars().all()
        grouped: dict[int, list[VerifiedClaim]] = defaultdict(list)
        for row in rows:
            grouped[int(row.business_id)].append(row)
        return grouped

    def _layer2_slice_match(
        self,
        *,
        query_slice_keys: set[str],
        slices: list[VerticalSlice],
    ) -> tuple[bool, list[str]]:
        if not query_slice_keys:
            return True, []

        matched_keys: list[str] = []
        for row in slices:
            slice_key = str(row.slice_key)
            if slice_key in query_slice_keys:
                matched_keys.append(slice_key)
                continue
            weights = row.category_weights if isinstance(row.category_weights, dict) else {}
            if set(weights.keys()).intersection(query_slice_keys):
                matched_keys.append(slice_key)
        return bool(matched_keys), sorted(set(matched_keys))

    @staticmethod
    def _layer3_literal_verify(
        *,
        query_tokens: set[str],
        evidence_terms: list[EvidenceIndexTerm],
    ) -> tuple[list[str], float]:
        if not query_tokens:
            return [], 0.0
        indexed_terms = {str(row.term) for row in evidence_terms}
        hits = sorted(query_tokens.intersection(indexed_terms))
        score = 0.0 if not query_tokens else min(1.0, len(hits) / max(1, len(query_tokens)))
        return hits, round(score, 4)

    def _layer4_micrograph_check(
        self,
        *,
        graph: dict[str, Any],
        query_concepts: set[str],
        query_tokens: set[str],
    ) -> tuple[bool, float, list[list[str]], list[str]]:
        nodes = graph.get("nodes") if isinstance(graph, dict) else []
        if not isinstance(nodes, list):
            return False, 0.0, [], []

        node_ids: set[str] = set()
        label_map: dict[str, str] = {}
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            if not isinstance(node_id, str):
                continue
            node_ids.add(node_id)
            label_map[node_id] = normalize_text(str(node.get("label") or ""))

        direct_matches = sorted(node_ids.intersection(query_concepts)) if query_concepts else []
        if direct_matches:
            return True, 1.0, [[match] for match in direct_matches[:4]], direct_matches[:8]

        token_matches: list[str] = []
        for node_id, label in label_map.items():
            label_tokens = set(tokenize(label))
            if query_tokens.intersection(label_tokens):
                token_matches.append(node_id)
        if token_matches and not query_concepts:
            return True, 0.72, [[node_id] for node_id in token_matches[:4]], token_matches[:8]

        adjacency = graph_adjacency(graph)
        if not query_concepts:
            return False, 0.0, [], []

        matched_claims: set[str] = set()
        matched_paths: list[list[str]] = []

        for seed in query_concepts:
            queue: deque[tuple[str, int, list[str]]] = deque()
            queue.append((seed, 0, [seed]))
            visited_depth: dict[str, int] = {seed: 0}

            while queue:
                node, depth, path = queue.popleft()
                if depth >= self.MAX_SUBGRAPH_HOPS:
                    continue
                for nxt in adjacency.get(node, set()):
                    next_depth = depth + 1
                    if next_depth > self.MAX_SUBGRAPH_HOPS:
                        continue
                    prev = visited_depth.get(nxt)
                    if prev is not None and prev <= next_depth:
                        continue
                    visited_depth[nxt] = next_depth
                    new_path = path + [nxt]
                    queue.append((nxt, next_depth, new_path))

                    if nxt in node_ids:
                        matched_claims.add(nxt)
                        matched_paths.append(new_path)

        if not matched_claims:
            return False, 0.0, [], []

        best_hops = min((len(path) - 1 for path in matched_paths), default=self.MAX_SUBGRAPH_HOPS)
        score = 0.76 if best_hops == 1 else 0.62
        return True, score, matched_paths[:6], sorted(matched_claims)[:12]

    def search(self, db: Session, params: PrecisionSearchParams) -> dict[str, Any]:
        normalized_query = normalize_text(params.query)
        if not normalized_query:
            return {
                "query": params.query,
                "normalized_query": "",
                "matched_concepts": [],
                "results": [],
            }

        query_concepts = self._query_concepts(normalized_query)
        query_tokens = set(tokenize(normalized_query))
        query_vector = self._query_vector(normalized_query, query_concepts)

        layer1 = self._layer1_candidates(db, params=params, query_vector=query_vector)
        business_ids = [business.id for business, _similarity in layer1]

        vertical_map = self._fetch_vertical_map(db, business_ids)
        evidence_map = self._fetch_evidence_term_map(db, business_ids)
        micrographs = self._fetch_micrographs(db, business_ids)
        verified_map = self._fetch_verified_claims(db, business_ids)

        query_slice_keys = self.taxonomy.query_slice_keys(query_concepts)
        business_model_filters = self._to_business_model_filters(params)

        results: list[dict[str, Any]] = []

        for business, similarity in layer1:
            distance_km = haversine_km(params.lat, params.lng, business.lat, business.lng)
            walking_minutes, driving_minutes, fastest_minutes = compute_travel_minutes(distance_km)

            if params.walking_distance and walking_minutes > params.walking_threshold_minutes:
                continue

            business_model = normalize_business_model_document(
                business.business_model if isinstance(business.business_model, dict) else None
            )
            passes_filters, _reasons = passes_business_model_filters(
                business_model,
                business_model_filters,
            )
            if not passes_filters:
                continue

            places_open_now = self._places_open_now(business_model)
            open_flag = places_open_now if places_open_now is not None else is_open_now(business.hours_json, business.timezone)
            if params.open_now and places_open_now is not True:
                continue

            slice_match, slice_keys = self._layer2_slice_match(
                query_slice_keys=query_slice_keys,
                slices=vertical_map.get(int(business.id), []),
            )
            literal_hits, literal_score = self._layer3_literal_verify(
                query_tokens=query_tokens,
                evidence_terms=evidence_map.get(int(business.id), []),
            )

            graph_row = micrographs.get(int(business.id))
            graph = graph_row.graph_json if graph_row and isinstance(graph_row.graph_json, dict) else {}
            deep_confirmed, deep_score, deep_paths, matched_claim_ids = self._layer4_micrograph_check(
                graph=graph,
                query_concepts=set(query_concepts),
                query_tokens=query_tokens,
            )

            verified_rows = verified_map.get(int(business.id), [])
            relevant_verified: list[dict[str, Any]] = []
            for row in verified_rows:
                claim_key = str(row.claim_id)
                label_tokens = set(tokenize(str(row.label)))
                claim_related = claim_key in set(query_concepts) or bool(query_tokens.intersection(label_tokens))
                if claim_related or claim_key in set(matched_claim_ids):
                    relevant_verified.append(
                        {
                            "claim_id": row.claim_id,
                            "label": row.label,
                            "evidence": row.evidence if isinstance(row.evidence, list) else [],
                            "confidence": round(float(row.confidence), 4),
                            "timestamp": row.timestamp,
                        }
                    )

            if not relevant_verified and verified_rows:
                top_row = verified_rows[0]
                relevant_verified.append(
                    {
                        "claim_id": top_row.claim_id,
                        "label": top_row.label,
                        "evidence": top_row.evidence if isinstance(top_row.evidence, list) else [],
                        "confidence": round(float(top_row.confidence), 4),
                        "timestamp": top_row.timestamp,
                    }
                )

            verified_score = max((float(item["confidence"]) for item in relevant_verified), default=0.0)

            # Precision-weighted score from deterministic layer outputs.
            precision_score = (
                0.35 * max(0.0, similarity)
                + 0.15 * (1.0 if slice_match else 0.0)
                + 0.2 * literal_score
                + 0.3 * max(verified_score, deep_score)
            )
            precision_score = max(0.0, min(1.0, precision_score))

            if precision_score < 0.28:
                continue

            seed_nodes = set(query_concepts).union(set(matched_claim_ids))
            on_demand_subgraph = build_on_demand_subgraph(
                graph=graph,
                seed_nodes=seed_nodes,
                max_hops=self.MAX_SUBGRAPH_HOPS,
            )

            results.append(
                {
                    "id": int(business.id),
                    "name": business.name,
                    "lat": float(business.lat),
                    "lng": float(business.lng),
                    "distance_km": round(distance_km, 2),
                    "minutes_away": int(fastest_minutes),
                    "walking_minutes": int(walking_minutes),
                    "driving_minutes": int(driving_minutes),
                    "open_now": bool(open_flag),
                    "is_chain": bool(business.is_chain),
                    "chain_name": business.chain_name,
                    "precision_score": round(precision_score, 4),
                    "evidence_score": int(round(precision_score * 100)),
                    "verified_claims": relevant_verified,
                    "audit_chain": {
                        "layer_1_similarity": round(float(similarity), 4),
                        "layer_2_slice_match": slice_match,
                        "layer_2_slice_keys": slice_keys,
                        "layer_3_literal_hits": literal_hits,
                        "layer_3_literal_score": literal_score,
                        "layer_4_deep_confirmed": deep_confirmed,
                        "layer_4_paths": deep_paths,
                        "layer_4_deep_score": deep_score,
                        "layer_5_verified_count": len(relevant_verified),
                        "layer_6_subgraph": on_demand_subgraph,
                        "constraints": {
                            "max_hops": 2,
                            "ml_inference": False,
                            "global_ontology_changes": False,
                        },
                    },
                    "last_updated": business.last_updated,
                }
            )

        results.sort(key=lambda row: (-row["precision_score"], row["distance_km"], row["name"].lower()))
        return {
            "query": params.query,
            "normalized_query": normalized_query,
            "matched_concepts": query_concepts,
            "results": results[: params.limit],
        }

    def verified_claims_for_business(self, db: Session, business_id: int) -> list[dict[str, Any]]:
        rows = db.execute(
            select(VerifiedClaim)
            .where(VerifiedClaim.business_id == business_id)
            .order_by(VerifiedClaim.confidence.desc(), VerifiedClaim.claim_id.asc())
        ).scalars().all()

        output: list[dict[str, Any]] = []
        for row in rows:
            output.append(
                {
                    "claim_id": row.claim_id,
                    "label": row.label,
                    "evidence": row.evidence if isinstance(row.evidence, list) else [],
                    "confidence": round(float(row.confidence), 4),
                    "timestamp": row.timestamp,
                }
            )
        return output


precision_search_service = PrecisionSearchService()
