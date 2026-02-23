from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class EvidenceSpan:
    span_id: str
    business_id: int
    text: str
    source_kind: str
    source_id: str
    source_url: str | None
    snippet: str
    extraction_confidence: float
    credibility_score: float
    provenance: dict[str, Any]
    normalized_text: str = ""
    tokens: list[str] = field(default_factory=list)
    ngrams: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RelationEdge:
    source: str
    relation: str
    target: str
    provenance: str


@dataclass(slots=True)
class ClaimDraft:
    claim_id: str
    label: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    confidence: float = 0.0
    max_hops: int = 0
    is_inferred: bool = False
    is_composed: bool = False
    source_count: int = 0
    direct_support: bool = False
    created_at: datetime | None = None
    _source_keys: set[str] = field(default_factory=set, repr=False)

    def add_evidence(self, evidence_item: dict[str, Any]) -> None:
        self.evidence.append(evidence_item)
        source_key = str(evidence_item.get("source_key") or "")
        if source_key:
            self._source_keys.add(source_key)
            self.source_count = len(self._source_keys)
        if evidence_item.get("kind") in {"span", "menu_item", "evidence_packet", "category_tag", "business_name"}:
            self.direct_support = True
        hops = int(evidence_item.get("hops") or 0)
        self.max_hops = max(self.max_hops, hops)

    def as_verified_claim(self, timestamp: datetime) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "label": self.label,
            "evidence": self.evidence,
            "confidence": round(float(self.confidence), 4),
            "timestamp": timestamp,
        }
