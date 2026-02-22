
# phase-3-memo-google-places-api-integration.md

---

## 1. Objective

Integrate Google Places API (New) into the Buycott Docker container to:

* Seed real businesses in the Powderhorn neighborhood of Minneapolis
* Store business data in existing Postgres schema
* Reuse the current embedding + capability rebuild pipeline
* Enforce 30-day data freshness requirement
* Respect cost limits per pipeline execution

This phase replaces synthetic seed data with live Google Places data while preserving the existing architecture.

---

## 2. Architectural Placement

New file:

<pre class="overflow-visible! px-0!" data-start="1087" data-end="1125"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>pipeline/google_places_seed.py</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

Modified file:

<pre class="overflow-visible! px-0!" data-start="1143" data-end="1180"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>pipeline/run_full_pipeline.py</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

No changes to:

* build_embeddings.py
* rebuild_capabilities.py
* openclaw_extract.py
* frontend logic
* Docker structure

---

## 3. Environment Configuration

`.env`

<pre class="overflow-visible! px-0!" data-start="1351" data-end="1459"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>GOOGLE_MAPS_API_KEY=YOUR_KEY</span><br/><span>MAX_RUN_COST_USD=1.00</span><br/><span>MAX_MONTHLY_COST_USD=5.00</span><br/><span>GOOGLE_DATA_TTL_DAYS=30</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

Docker compose remains unchanged except for environment injection.

---

## 4. Powderhorn Geographic Definition

Hard-coded in script as bounding circle:

* Center: Powderhorn Park
* Lat/Lng: 44.9485, -93.2547
* Radius: 1.5 miles

This defines the static seeding boundary.

Future neighborhoods will be parameterized but Phase 3 seeds Powderhorn only.

---

## 5. Data Model Extensions (Minimal)

Add fields if not already present:

<pre class="overflow-visible! px-0!" data-start="1894" data-end="2115"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>google_place_id TEXT UNIQUE</span><br/><span>formatted_address TEXT</span><br/><span>latitude DOUBLE PRECISION</span><br/><span>longitude DOUBLE PRECISION</span><br/><span>phone TEXT</span><br/><span>website TEXT</span><br/><span>hours JSONB</span><br/><span>types JSONB</span><br/><span>google_last_fetched_at TIMESTAMP</span><br/><span>google_source = 'places_api'</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

No schema redesign. Only additive fields.

---

## 6. Seeding Logic

### 6.1 Staleness Rule

A record is stale if:

<pre class="overflow-visible! px-0!" data-start="2233" data-end="2281"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>NOW() - google_last_fetched_at > 30 days</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

OR

<pre class="overflow-visible! px-0!" data-start="2287" data-end="2325"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>google_last_fetched_at IS NULL</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

### 6.2 Seeding Algorithm

For each Place returned:

1. Check if google_place_id exists.
2. If not exists → INSERT.
3. If exists AND stale → UPDATE.
4. If exists AND fresh → skip.

This prevents unnecessary API calls.

---

## 7. Google API Usage

Use:

**Places API (New)**

Endpoints:

* Nearby Search (Text Search with location bias)
* Place Details (field-masked)

### Fields Requested

Only fetch required fields:

<pre class="overflow-visible! px-0!" data-start="2747" data-end="2852"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>id</span><br/><span>displayName</span><br/><span>formattedAddress</span><br/><span>location</span><br/><span>types</span><br/><span>websiteUri</span><br/><span>nationalPhoneNumber</span><br/><span>regularOpeningHours</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

No photos.

No reviews.

No unnecessary fields.

This reduces cost and ensures compliance.

---

## 8. Cost Guardrail Implementation

### 8.1 Runtime Cost Counter

Track:

<pre class="overflow-visible! px-0!" data-start="3024" data-end="3081"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>request_count</span><br/><span>cost_per_request = estimated $0.017</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

Stop pipeline if:

<pre class="overflow-visible! px-0!" data-start="3102" data-end="3162"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>request_count * cost_per_request >= MAX_RUN_COST_USD</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

### 8.2 Monthly Guard (Soft)

Maintain table:

<pre class="overflow-visible! px-0!" data-start="3211" data-end="3290"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>google_api_usage_log</span><br/><span>  - timestamp</span><br/><span>  - requests_made</span><br/><span>  - estimated_cost</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

If rolling 30-day total >= $5:

abort pipeline.

---

## 9. Storage Compliance (30-Day Rule)

This implementation enforces:

* Data must be refreshed every 30 days.
* Stale entries are re-fetched.
* Data is not stored permanently without refresh.
* google_place_id is stored indefinitely (allowed identifier).
* Other fields are refreshed if older than TTL.

This satisfies static storage with refresh enforcement.

---

## 10. Pipeline Integration

### run_full_pipeline.py modification

Add before embeddings:

<pre class="overflow-visible! px-0!" data-start="3808" data-end="3865"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>if args.seed_google:</span><br/><span>    google_places_seed.run()</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

Full order:

1. init_db
2. google_places_seed
3. build_embeddings
4. rebuild_capabilities

No change to embedding logic.

---

## 11. Runtime Search Behavior (Unchanged)

At runtime:

* User location obtained via frontend
* Radius selection: {1,5,10,25,50,100}
* Query vectorized
* Compared against DB embeddings
* No Google calls during search

Google is ingestion-only.

---

## 12. Frontend Business Card Rules

If field is NULL:

* Disable button
* Gray link

Fields:

* Website
* Phone
* Hours

No media rendering yet.

---

## 13. Execution

Inside container:

<pre class="overflow-visible! px-0!" data-start="4434" data-end="4520"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>docker compose exec backend python pipeline/run_full_pipeline.py --seed-google</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

Only requirement:

<pre class="overflow-visible! px-0!" data-start="4541" data-end="4580"><div class="w-full my-4"><div class=""><div class="relative"><div class="h-full min-h-0 min-w-0"><div class="h-full min-h-0 min-w-0"><div class="border corner-superellipse/1.1 border-token-border-light bg-token-bg-elevated-secondary rounded-3xl"><div class="pointer-events-none absolute inset-x-4 top-12 bottom-4"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-border-light"></div></div></div><div class="pointer-events-none absolute inset-x-px top-0 bottom-96"><div class="pointer-events-none sticky z-40 shrink-0 z-1!"><div class="sticky bg-token-bg-elevated-secondary"></div></div></div><div class="corner-superellipse/1.1 rounded-3xl bg-token-bg-elevated-secondary"><div class="relative z-0 flex max-w-full"><div id="code-block-viewer" dir="ltr" class="q9tKkq_viewer cm-editor z-10 light:cm-light dark:cm-light flex h-full w-full flex-col items-stretch ͼs ͼ16"><div class="cm-scroller"><div class="cm-content q9tKkq_readonly"><span>GOOGLE_MAPS_API_KEY set in .env</span></div></div></div></div></div></div></div></div><div class=""><div class=""></div></div></div></div></div></pre>

---

## 14. Deterministic Behavior Guarantees

* No duplicate businesses
* No unnecessary refresh calls
* No uncontrolled API cost growth
* No architectural restructuring
* No OpenClaw integration
* Embeddings unchanged
* Static DB strengthened with real data

---

## 15. Resulting System Behavior

After Phase 3:

* Powderhorn businesses exist in DB
* Keywords derived from types
* Real addresses + phone + website + hours
* Semantic search operates against real businesses
* Google data auto-refreshes every 30 days
* API costs capped
