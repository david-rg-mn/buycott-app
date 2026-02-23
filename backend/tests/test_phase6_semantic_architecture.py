from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.services.phase6.agents import (
    CompositionAgent,
    ConceptMapperAgent,
    NormalizerAgent,
    RelationArbiterAgent,
    ScoringAgent,
    VerifierAgent,
)
from app.services.phase6.contracts import ClaimDraft, EvidenceSpan
from app.services.phase6.graph_utils import build_on_demand_subgraph
from app.services.phase6.taxonomy import Phase6Taxonomy


def _build_span(*, text: str, source_id: str, source_kind: str = "menu_item") -> EvidenceSpan:
    return EvidenceSpan(
        span_id=f"span:{source_id}",
        business_id=1,
        text=text,
        source_kind=source_kind,
        source_id=source_id,
        source_url="https://example.org/menu",
        snippet=text,
        extraction_confidence=0.9,
        credibility_score=90.0,
        provenance={"table": "menu_items", "row_id": 1},
    )


def test_accent_folding_alias_mapping_is_deterministic() -> None:
    taxonomy = Phase6Taxonomy()
    normalizer = NormalizerAgent()
    mapper = ConceptMapperAgent(taxonomy=taxonomy)

    spans = normalizer.normalize(
        [
            _build_span(text="Taquer\u00eda", source_id="menu:1"),
            _build_span(text="alambres", source_id="menu:2"),
        ]
    )
    claims = mapper.map(spans)

    assert "biz.type.taqueria" in claims
    assert "food.dish.alambre" in claims


def test_relation_arbiter_enforces_two_hop_limit(tmp_path: Path) -> None:
    alias_file = tmp_path / "aliases.json"
    relation_file = tmp_path / "relations.json"

    alias_file.write_text(
        json.dumps(
            {
                "concept.a": ["alpha"],
                "concept.b": ["beta"],
                "concept.c": ["gamma"],
                "concept.d": ["delta"],
            }
        ),
        encoding="utf-8",
    )
    relation_file.write_text(
        json.dumps(
            [
                {"source": "concept.a", "relation": "to", "target": "concept.b", "provenance": "test"},
                {"source": "concept.b", "relation": "to", "target": "concept.c", "provenance": "test"},
                {"source": "concept.c", "relation": "to", "target": "concept.d", "provenance": "test"},
            ]
        ),
        encoding="utf-8",
    )

    taxonomy = Phase6Taxonomy(alias_path=alias_file, relation_path=relation_file)
    normalizer = NormalizerAgent()
    mapper = ConceptMapperAgent(taxonomy=taxonomy)
    arbiter = RelationArbiterAgent(taxonomy=taxonomy)

    spans = normalizer.normalize([_build_span(text="alpha", source_id="menu:alpha")])
    claims = mapper.map(spans)
    claims = arbiter.apply(claims)

    assert "concept.b" in claims
    assert "concept.c" in claims
    assert "concept.d" not in claims
    assert all(claim.max_hops <= 2 for claim in claims.values())


def test_composition_requires_multi_source_support() -> None:
    composition = CompositionAgent()

    taco_claim = ClaimDraft(claim_id="food.taco", label="taco")
    taco_claim.add_evidence(
        {
            "kind": "menu_item",
            "evidence": 0.9,
            "source_key": "menu:1",
            "source_id": "menu:1",
            "provenance": {"table": "menu_items", "row_id": 1},
        }
    )

    filling_claim = ClaimDraft(claim_id="food.filling.carnitas", label="carnitas")
    filling_claim.add_evidence(
        {
            "kind": "menu_item",
            "evidence": 0.88,
            "source_key": "menu:1",
            "source_id": "menu:1",
            "provenance": {"table": "menu_items", "row_id": 1},
        }
    )

    claims = {"food.taco": taco_claim, "food.filling.carnitas": filling_claim}
    composition.apply(claims)
    assert "food.taco.filling.carnitas" not in claims

    filling_claim_2 = ClaimDraft(claim_id="food.filling.carnitas", label="carnitas")
    filling_claim_2.add_evidence(
        {
            "kind": "evidence_packet",
            "evidence": 0.81,
            "source_key": "evidence:44",
            "source_id": "evidence:44",
            "provenance": {"table": "evidence_packets", "row_id": 44},
        }
    )
    claims = {"food.taco": taco_claim, "food.filling.carnitas": filling_claim_2}
    composition.apply(claims)
    assert "food.taco.filling.carnitas" in claims


def test_weighted_scoring_uses_sum_of_weight_times_evidence() -> None:
    scoring = ScoringAgent()

    claim = ClaimDraft(claim_id="food.taco", label="taco")
    claim.add_evidence({"kind": "menu_item", "evidence": 0.8, "source_key": "menu:1", "provenance": {"t": 1}})
    claim.add_evidence({"kind": "relation", "evidence": 0.5, "source_key": "relation:1", "provenance": {"t": 2}})

    claims = scoring.score({"food.taco": claim})
    scored = claims["food.taco"]

    expected = (0.65 * 0.8) + (0.28 * 0.5) + (0.24 * ((2 - 1) / 3))
    assert scored.score == round(expected, 4)
    assert 0 <= scored.confidence <= 1


def test_verified_claim_schema_contract() -> None:
    verifier = VerifierAgent()
    business = SimpleNamespace(id=9)

    claim = ClaimDraft(claim_id="food.taco", label="taco", confidence=0.92, score=1.01)
    claim.add_evidence(
        {
            "kind": "menu_item",
            "evidence": 0.91,
            "source_key": "menu:1",
            "source_id": "menu:1",
            "provenance": {"table": "menu_items", "row_id": 1},
        }
    )

    payloads = verifier.verify(session=None, business=business, claims={"food.taco": claim}, persist=False)

    assert len(payloads) == 1
    payload = payloads[0]
    assert set(payload.keys()) == {"claim_id", "label", "evidence", "confidence", "timestamp"}
    assert payload["claim_id"] == "food.taco"


def test_on_demand_subgraph_is_hop_bounded() -> None:
    graph = {
        "nodes": [
            {"id": "a", "label": "a"},
            {"id": "b", "label": "b"},
            {"id": "c", "label": "c"},
            {"id": "d", "label": "d"},
        ],
        "edges": [
            {"source": "a", "target": "b", "relation": "r", "hops": 1},
            {"source": "b", "target": "c", "relation": "r", "hops": 1},
            {"source": "c", "target": "d", "relation": "r", "hops": 1},
        ],
    }

    subgraph = build_on_demand_subgraph(graph=graph, seed_nodes={"a"}, max_hops=2)
    node_ids = {node["id"] for node in subgraph["nodes"]}

    assert subgraph["max_hops"] == 2
    assert "a" in node_ids
    assert "b" in node_ids
    assert "c" in node_ids
    assert "d" not in node_ids
