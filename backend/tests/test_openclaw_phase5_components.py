from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "pipeline") not in sys.path:
    sys.path.insert(0, str(ROOT / "pipeline"))

from openclaw.inference import InferenceLayer
from openclaw.runtime import HttpProbe, RouterMasterAgent, SourceCandidate


class _ProbeClient:
    def __init__(self, probe: HttpProbe):
        self._probe = probe

    def probe(self, _url: str) -> HttpProbe:
        return self._probe


def test_router_detects_pdf_from_url_and_content_type() -> None:
    candidate = SourceCandidate(
        source_url="https://example.org/menu.pdf",
        source_type="website",
        source_snippet="PDF menu",
    )
    probe = HttpProbe(
        source_url=candidate.source_url,
        final_url=candidate.source_url,
        status_code=200,
        content_type="application/pdf",
        text_sample="",
        bytes_sample=b"%PDF-1.7",
        headers={},
        attempts=1,
    )
    router = RouterMasterAgent(http_client=_ProbeClient(probe))
    decision = router.detect(candidate)

    assert decision.primary_modality == "pdf"
    assert "pdf" in decision.spawn_modalities
    assert decision.scores["pdf"] >= 90


class _CountingNormalizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def normalize_term(self, term: str) -> tuple[str, int, str]:
        self.calls.append(term)
        return term.lower().strip(), len(self.calls), "test"


def test_inference_normalizes_terms_for_capability_output() -> None:
    normalizer = _CountingNormalizer()
    layer = InferenceLayer(normalizer=normalizer)  # type: ignore[arg-type]

    menu_items = [
        SimpleNamespace(
            id=1,
            item_name="Vegan Burrito",
            dietary_tags=["vegan", "gluten-free"],
            extraction_confidence=0.8,
            credibility_score=88.0,
        )
    ]
    evidence_packets = [
        SimpleNamespace(
            id=101,
            sanitized_claim_text="Mentions delivery operations and breakfast service window",
            extraction_confidence=0.65,
            credibility_score=70.0,
        )
    ]

    capabilities = layer.build_capabilities(evidence_packets=evidence_packets, menu_items=menu_items)
    output_types = {cap.capability_type for cap in capabilities}

    assert "sells" in output_types
    assert "attributes" in output_types
    assert "services" in output_types
    assert "operations" in output_types
    assert len(normalizer.calls) >= 4
