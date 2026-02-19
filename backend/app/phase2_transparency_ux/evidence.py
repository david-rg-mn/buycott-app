from __future__ import annotations

from dataclasses import dataclass

from app.db.models import BusinessCapability, BusinessSource
from app.phase1_semantic_pipeline.embeddings import normalize_similarity_to_score


@dataclass(frozen=True)
class EvidenceComputation:
    evidence_strength: int
    semantic_similarity: float
    ontology_bonus: float
    explicit_evidence_bonus: float


def compute_evidence_strength(
    semantic_similarity: float,
    query: str,
    expanded_terms: list[str],
    capabilities: list[BusinessCapability],
) -> EvidenceComputation:
    query_lc = query.lower()

    best_cap_conf = 0.0
    ontology_overlap = 0.0
    explicit = 0.0

    expanded_lower = {term.lower() for term in expanded_terms}

    for cap in capabilities:
        best_cap_conf = max(best_cap_conf, cap.confidence_score)
        if cap.ontology_term.lower() in expanded_lower:
            ontology_overlap = max(ontology_overlap, cap.confidence_score)
        if cap.source_snippet and query_lc in cap.source_snippet.lower():
            explicit = max(explicit, cap.confidence_score)

    ontology_bonus = min(0.08, 0.08 * ontology_overlap)
    explicit_bonus = min(0.06, 0.06 * max(explicit, best_cap_conf))

    composed_similarity = min(1.0, semantic_similarity + ontology_bonus + explicit_bonus)
    score = normalize_similarity_to_score(composed_similarity)

    return EvidenceComputation(
        evidence_strength=score,
        semantic_similarity=semantic_similarity,
        ontology_bonus=ontology_bonus,
        explicit_evidence_bonus=explicit_bonus,
    )


def evidence_points(
    query: str,
    expanded_terms: list[str],
    capabilities: list[BusinessCapability],
    sources: list[BusinessSource],
    semantic_similarity: float,
) -> list[tuple[str, str]]:
    points: list[tuple[str, str]] = []

    if sources:
        primary = sorted({src.source_type for src in sources})
        points.append(("Evidence sources", ", ".join(primary)))

    for cap in sorted(capabilities, key=lambda c: c.confidence_score, reverse=True)[:3]:
        points.append(
            (
                "Capability inference",
                f"{cap.ontology_term} (confidence {cap.confidence_score:.2f})",
            )
        )

    if expanded_terms:
        points.append(("Ontology expansion", " -> ".join(expanded_terms[:5])))

    points.append(("Semantic similarity", f"Cosine similarity {semantic_similarity:.3f}"))
    return points
