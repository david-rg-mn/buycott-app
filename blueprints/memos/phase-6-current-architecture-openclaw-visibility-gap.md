# Current Architecture Memo: Post-`f26f40e` Attempt, Andale Validation, and OpenClaw Terms Visibility Gap

**Date:** 2026-02-23  
**Baseline commit (last pushed):** `f26f40e` (`phase-5-ticket complete`)  
**Scope:** System behavior and changes made since last push, with focus on Andale testing and OpenClaw terms display parity.

## 1) Executive Summary

This branch is a substantial extension of the Phase 5 baseline. It now includes:

1. Places-New-only business model classification and query-time gating.
2. Deterministic Phase 6 semantic pipeline scaffolding with auditable claims schema.
3. Ranking/precision controls to reduce false positives and far-distance contamination.
4. Phase 5 pipeline hardening for duplicate insert collisions.
5. OpenClaw capability rendering improvements, including menu-description ingredient extraction.

Primary unresolved QA concern (user-reported):

**The caret-expanded “OpenClaw terms” UI should represent the full scraped menu term set for a business, but the UI has not consistently reflected all collected terms as expected.**

## 2) Direct Answer: Is the full menu used in search ontology?

**Short answer: partially, not fully.**

1. Full parsed menu rows are stored in `menu_items` when extraction succeeds.
2. Menu rows are embedded (`_embed_menu_items`) in Phase 5.
3. Business-level summary embedding only includes top menu subset (`top_menu[:20]`) in `canonical_summary_text` construction.
4. Capability profile generation (`InferenceLayer.build_capabilities`) is selective, not a full menu passthrough ontology expansion.
5. Therefore: full menu is persisted and partially used for inference/embedding, but not fully projected into ontology-facing capability terms by default.

## 3) Current Architecture (as implemented in this attempt)

## 3.1 Ingestion + Places classification

1. Seed pipeline (`pipeline/google_places_seed.py`) uses Places API New field masks including:
   - `id`, `primaryType`, `types`, `businessStatus`, `pureServiceAreaBusiness`
   - `delivery`, `takeout`, `dineIn`, `curbsidePickup`, `reservable`
   - `currentOpeningHours`, `regularOpeningHours`
   - optional extras (`accessibilityOptions`, `paymentOptions`, `parkingOptions`)
2. Business model normalization and derivation is implemented in:
   - `backend/app/services/business_model_service.py`
3. Type-table driven deterministic classification is sourced from:
   - `data/raw/business_model/type_tables.v1.json`

## 3.2 Phase 5 OpenClaw pipeline

1. Pipeline entrypoint: `pipeline/phase5_openclaw_pipeline.py`
2. Flow:
   - source resolution -> router decisions -> scraper modalities -> source docs/evidence/menu persistence
   - menu embedding + inference -> capability profiles + business capabilities
   - business canonical summary embedding refresh
3. Stability hardening added:
   - in-memory dedupe guards for unique-key collisions in:
     - `source_documents`
     - `evidence_packets`
     - `menu_items`

## 3.3 Phase 6 deterministic semantic architecture (Phase A-style scaffolding)

1. Entrypoint: `pipeline/phase6_precision_pipeline.py`
2. Service namespace: `backend/app/services/phase6/`
3. Implemented layers/tables include:
   - global footprints
   - vertical slices
   - evidence index terms
   - micrograph
   - verified claims
   - on-demand subgraph utilities
4. Current Andale test runs produced zero verified claims in this attempt, indicating low precision-claim coverage from current evidence profile.

## 3.4 Search serving path

1. API endpoints in `backend/app/routes/search.py`:
   - `/api/search`
   - `/api/businesses`
   - `/api/business_capabilities/{business_id}`
   - `/api/search_precision`
2. Ranking and filtering in `backend/app/services/search_service.py` now include:
   - business-model query-time gating
   - distance cap (`max_search_distance_km`)
   - stricter similarity threshold
   - composite rank score (semantic + proximity + capability confidence)

## 3.5 Frontend terms rendering

1. Capability fetch path:
   - `frontend/buycott_flutter/lib/services/api_service.dart`
2. Capability model:
   - `frontend/buycott_flutter/lib/models/api_models.dart`
3. Business sheet caret rendering:
   - `frontend/buycott_flutter/lib/main.dart`

## 4) Observed Runtime History Since `f26f40e`

## 4.1 Andale pull + processing

1. Seed jobs repeatedly run for Andale (`businesses near Andale, Kansas`) with `--max-places 10`.
2. Andale-focused IDs observed in DB include: `266..278` range (not all are consumer storefronts).

## 4.2 Phase 5 operational issues encountered and fixed

1. Duplicate unique-key crashes occurred during multi-modality writes.
2. Fixes added in pipeline to dedupe within a run before DB flush.
3. After patching, per-business Phase 5 runs completed reliably.

## 4.3 Business-model + ranking tuning

1. Type table expanded for consumer-facing and B2B precision.
2. `consumer_facing_only` default filtering validated.
3. Distance contamination reduced via max-distance gate.
4. Similarity threshold increased to reduce low-confidence matches.

## 4.4 Andale Taqueria “carrot” test

1. `menu_items` contains carrot in descriptions for business `256`.
2. Deterministic menu-description ingredient extraction was added to surface terms like `carrot` in OpenClaw capability terms.
3. API check confirms:
   - `/api/business_capabilities/256?limit=8` includes `carrot` with `phase5:menu_description`.

## 5) OpenClaw Terms Box Mismatch (Collected vs Displayed)

## 5.1 Expected behavior

When user expands caret for a business, the OpenClaw terms panel should expose the complete collected term universe (menu-scale), not a narrow top-N subset.

## 5.2 Why mismatch happened in this attempt

1. Original backend response for `/api/business_capabilities` was capability-focused and limit-capped.
2. Many scraped tokens exist in menu descriptions, not item names, and were not always promoted into capability terms.
3. Frontend panel was originally based on returned capability terms only, filtered by `source_reference` prefix rules.
4. This combination made the expanded UI appear incomplete relative to raw collected corpus.

## 5.3 Current mitigation in branch

1. `CapabilitiesResponse` now includes `menu_items` (full deduped menu item-name list).
2. Frontend `CapabilityPayload` now parses `menu_items`.
3. Caret-expanded OpenClaw terms set now combines:
   - openclaw capability terms
   - full `menu_items` list
4. Validation sample for business `256`:
   - `menu_items_count = 204`
   - `carrot` present in capabilities via `phase5:menu_description`

## 5.4 Remaining UX/data parity caveat

Even with `menu_items` surfaced, full semantic parity with **all extracted phrases** is not guaranteed because:

1. `menu_items` returns item names only (not full description phrase inventory).
2. `evidence_packets.claim_text` can contain additional extracted language not currently projected into the terms box.
3. The UI terms list may still differ from the total extracted corpus unless a dedicated “all extracted spans” payload is shipped.

## 6) Evidence Snapshot (Current branch)

1. API health: `{"status":"ok"}`.
2. Backend tests: `24 passed`.
3. Business sample:
   - `256` shows `caps=8`, `menu_items=204`.
   - `257/258/259/260/263` show varying capability/menu coverage, with sparse extraction for several records.
4. Source docs for Andale batch show uneven source availability; some businesses have only 1 source doc and zero menu rows.

## 7) Architectural Interpretation

The platform is currently a hybrid of:

1. Deterministic Places classification + strict query filters.
2. Opportunistic OpenClaw enrichment quality (depends on source availability and scraper yield).
3. Capability-layer projection that is intentionally compressed relative to raw extraction corpus.

This means user-visible “OpenClaw terms” can diverge from “all collected text artifacts” unless explicitly bridged.

## 8) Recommended Next Step (to fully satisfy caret expectation)

Implement a dedicated backend endpoint (or extend `CapabilitiesResponse`) for **full extracted term inventory** per business, derived from:

1. `menu_items.item_name`
2. normalized tokens/phrases from `menu_items.description`
3. `evidence_packets.claim_text`

Then render that inventory in the caret “OpenClaw terms” panel as a separate section:

- `OpenClaw canonical terms` (current behavior)
- `OpenClaw full extracted inventory` (new behavior)

That removes ambiguity and guarantees UI parity with collected data.

## 9) Files Most Relevant to This Memo

1. `pipeline/google_places_seed.py`
2. `pipeline/phase5_openclaw_pipeline.py`
3. `pipeline/phase6_precision_pipeline.py`
4. `backend/app/services/business_model_service.py`
5. `backend/app/services/search_service.py`
6. `backend/app/schemas.py`
7. `frontend/buycott_flutter/lib/models/api_models.dart`
8. `frontend/buycott_flutter/lib/main.dart`

