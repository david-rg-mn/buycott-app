# inference-normalizer

## Purpose
Layer 2 inference agent that normalizes evidence into canonical ontology nodes and capability profiles.

## Inputs
- `evidence_packets`
- `menu_items`
- `ontology_nodes`

## Mandatory Behavior
- Every term must pass through ontology normalization (no direct raw-term persistence).
- Canonical capability output must include `source_claim_ids` for full traceability.
- Output types: `sells`, `services`, `attributes`, `operations`, `suitability`.

## Output
- `capabilities[]` rows suitable for `capabilities` table insertion.
- per-capability confidence and evidence scores.
