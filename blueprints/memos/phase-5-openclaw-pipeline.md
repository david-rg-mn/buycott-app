# Phase 5: OpenClaw Multi‐Agent Pipeline for Menu & Business Signals

**Executive Summary:** We design an autonomous OpenClaw agent system that takes a business (identified via Google Places or similar) and **expands its “meaning space”** by gathering menus and related signals across formats (HTML, PDF, images, APIs, social, etc.). A **router master agent** detects the input modality and spawns specialized scraper sub‐agents (HTML, Playwright/SPA, PDF, OCR, social, API integrator). Each agent extracts structured “evidence packets” (e.g. menu items, hours, certifications) with source references. A layer of inference agents then **normalizes and compresses** these signals into a canonical profile (capabilities, model, operations, suitability). A final master arbiter reconciles conflicts and builds embeddings for each business. Throughout, we enforce sandboxed execution, rate‐limit handling, idempotency and audit trails. The result is a modular, scalable pipeline that enriches business vectors beyond the Google API baseline, preserving neutrality and traceability.  

---

## 1. Menu-URL Modalities & Detection

Business menus and listings can appear in many forms. We categorise them as follows, with heuristic cues and “confidence” signals for each:

| **Modality**        | **Detection Heuristics**                                                                          | **Example Confidence Metric**            |
|---------------------|---------------------------------------------------------------------------------------------------|-----------------------------------------|
| **Static HTML page**| HTML contains keywords (“Menu”, “Hours”, “Breakfast”, currency symbols), lists of `<li>` or `<tr>`.  | Count of menu-like keywords or price patterns vs total words. |
| **Single-Page App** | Initial HTML is sparse; heavy JS/XHR. Indicators: common frameworks (`<div id="root">`), endless scroll. | Compare raw fetch text length vs post-render text length (via headless browser). Large ratio ⇒ SPA. |
| **PDF file**        | URL ends in `.pdf` or HTTP `Content-Type: application/pdf`. Magic bytes in response (e.g. `%PDF`).   | Boolean flag + OCR/text extraction success (if many food terms found). |
| **Image file**      | URL ends in image extension (JPG/PNG) or `<img>` tag with menu photo. Page largely graphic.        | OCR yield (text length from image); if >X characters of menu-like text, high confidence. |
| **API/JSON feed**   | Known endpoints (e.g. Google Places `menu_url`, Yelp Fusion, Toast, Square). JSON/XML response.    | Success of API call & presence of menu array. |
| **Social Media**    | Business Instagram/Facebook posts (e.g. highlights, posts). Typically dynamic.                     | Presence of business handle + Graph API access + text content volume. |
| **Ordering Platform**| Links to third-party menus (e.g. ToastTab, ChowNow, Square Online).                                | Domain detection (e.g. “toasttab.com/menu”) + menu keywords on page. |

Each candidate source is scored by confidence. For example, a URL yielding thousands of words with many currency symbols and “Item – $X” patterns would get a high “menu” score, whereas an image with no detectable text scores low. Practically, the **Router Agent** can use these heuristics (domain patterns, response headers, and preliminary parsing) to decide which specialised scraper to invoke. We can assign numeric confidence levels (0–100) by combining signals, e.g. for an HTML page:  
```
confidence ≈ min( 100, 20*hasKeyword + 30*hasPrices + 50*li_density )
```  
so that only genuinely menu-like pages trigger the menu parser. 

These modalities cover essentially all menu sources. The detection stage runs lightweight checks (URL pattern, small content probes) to route the task. (Any uncertain case may spawn multiple scrapers in parallel with backoff or wait for the most credible result.) 

---

## 2. Router/Master Agent Architecture

We implement a **hierarchical agent structure**. At the top is a **Router Agent** (OpenClaw controller) that receives a business URL or ID (e.g. from Google Places data). The Router performs quick checks (header sniffing, URL keywords) to classify modality and then spawns **scraper sub-agents** accordingly (see Figure below). OpenClaw’s `sessions.spawn` or `/subagents spawn` command can launch each scraper as a *background agent*. Each runs in isolation (its own session and tools environment) and reports back when done【33†L175-L184】【20†L245-L254】.

```mermaid
flowchart LR
    Router[/Router Agent/]
    Router -->|HTML page| HTMLAgent[HTML Scraper Agent]
    Router -->|SPA (JS heavy)| SPAAgent[Playwright (JS) Scraper Agent]
    Router -->|PDF file| PDFAgent[PDF Parser Agent]
    Router -->|Image| OCRAgent[Image OCR Agent]
    Router -->|Social links| SocialAgent[Instagram/Facebook Agent]
    Router -->|API endpoint| APIAgent[Google/Yelp/Order API Agent]
    subgraph Data Store
      DB[(Vector DB / Postgres etc.)]
    end
    HTMLAgent --> DB
    SPAAgent --> DB
    PDFAgent --> DB
    OCRAgent --> DB
    SocialAgent --> DB
    APIAgent --> DB
    DB --> Master[Master (Arbiter) Agent]
```

**Workflow:** The Router uses OpenClaw’s subagent support to run scrapers in parallel【33†L175-L184】. For example, it might call `sessions.spawn` to launch an HTML scraper and a PDF parser concurrently if uncertainty exists. Each scraper writes its results to an agreed **data store** (e.g. a Postgres table with pgvector or a vector DB). When all relevant agents finish (or a timer/heartbeat elapses), the Router triggers the next phase. The final **Master Agent** then reads the combined evidence, resolves conflicts, and generates embeddings. 

This architecture mirrors known multi-agent scraping patterns【20†L245-L254】【33†L175-L184】: a *Discovery/Router agent* delegates to *Extraction agents*, which feed into a *Validation/Orchestrator layer*. OpenClaw’s concurrency primitives (lanes and sub-agents) ensure that each scrape job is isolated and recoverable【2†L133-L142】【33†L175-L184】. The Router can also handle retries (via exponential backoff on 429s), deduplication (skip URLs already fetched), and scheduling (cron-triggered scrapes). 

---

## 3. Scraper Agent Skills

Each scraper agent is implemented as an OpenClaw **Skill** (a self-contained plugin with a `SKILL.md` manifest【6†L188-L196】). Key agents include:

- **HTML Scraper (Static):** Input: business URL. Uses a simple HTTP request (e.g. `curl` or requests) and parses HTML (BeautifulSoup or JSoup) for menus, lists, `<h1>` tags, tables, etc. Extracts structured items: sections, item names, descriptions, prices, tags (e.g. “vegan”, “gluten-free”). *Outputs:* list of `menu_item` records, key-value claims from “About” pages, etc. *Errors:* Timeouts, CAPTCHA, malformed HTML. *Rate-limit/Auth:* Obey robots.txt and throttle to a few req/sec; use user-agent headers. No auth needed for public pages. *Sandboxing:* Runs in a Docker container or NodeJS safe mode to prevent arbitrary JS execution leakage.  

- **SPA Scraper (Playwright):** Input: business URL. Uses headless Playwright (Chromium/Firefox) to render JavaScript-heavy sites (React/Vue). After navigation (wait for network idle or a DOM signal), scrapes the rendered HTML as above. *Outputs:* same structure as HTML Scraper. *Errors:* Headless crashes, detection (some sites block automated browsers). *Mitigations:* Use stealth modes, rotate user agents. Handle async loading by waits. *Rate-limit:* slower (~1 task/minute) due to heavy resources.  

- **PDF Parser:** Input: PDF URL or downloaded file. Uses `PyMuPDF` or `pdfplumber` to extract text. Then parses text for menu structure (regex on prices, section headers). Optionally uses Tesseract OCR for PDFs that are scanned images. *Outputs:* structured `menu_item` objects (as above). *Errors:* Encrypted or malformed PDFs, low-quality scans. *Fallback:* If text extraction fails, try OCR on each page image.  

- **Image OCR Agent:** Input: image URL or page image. Uses Tesseract (or a Vision API) to extract text. Then applies NLP to parse menu entries. For example, an image of a storefront sign might be scanned for business name and certifications. *Outputs:* text captions, recognized terms (e.g. “certified organic”). *Errors:* Blurry images, irrelevant graphics. We flag low‐confidence OCR results.  

- **Social Media Agent:** Input: business handle or scraped link. Prefers official APIs (Facebook Graph API for public pages, Instagram Graph API for business profiles). Retrieves bio, recent posts or highlights. *Outputs:* extracted text (e.g. Instagram bio listing “vegan bakery”), hashtags, links. *TOS note:* Automated scraping of social sites is legally sensitive – OpenClaw should prefer official APIs or skip if unauthorized【21†L156-L164】. Use proxies or caching to avoid IP blocks.  

- **API Integrator (Google/Yelp/Order):** Uses known APIs. E.g. call Google Places `/details` and scrape the `menu_url` field or call Yelp Fusion for categories/attributes. Also call third-party menu APIs (Toast, Square) where available. *Outputs:* data like “price_level”, “categories” (pizza, cafe), “attributes” (outdoor seating). *Auth:* requires API keys (store securely, inject via skill env config). Handle rate limits by caching Place IDs and retry schedules.  

Each skill logs its status and returns a structured JSON. For example, an HTML Scraper might output:  

```json
{
  "business_id": "biz123",
  "menu_items": [
    {
      "section": "Breakfast",
      "item_name": "Vegan Breakfast Burrito",
      "description": "Tofu scramble, black beans, pico de gallo...",
      "price": 11.50,
      "dietary_tags": ["vegan", "gluten-free"]
    },
    { ... }
  ],
  "hours": "8am–2pm",
  "claims": ["community-owned", "serves locally roasted coffee"]
}
```

And a Capability Extraction skill (below) might produce:  

```json
{
  "business_id": "biz123",
  "capabilities": [
    {"type": "sells",    "items": ["organic coffee", "housemade pastries"]},
    {"type": "services","items": ["custom cake design"]},
    {"type": "attributes","items": ["woman-owned", "locally-sourced"]},
    {"type": "price_level","items": ["mid"]}
  ]
}
```

Each skill must handle errors: for example, falling back from HTML to Image OCR if the page is mostly images. OpenClaw’s **sandboxing** is crucial: skills should run tools like `Browser` or `Exec` in restricted mode【6†L188-L196】, and secrets (API keys) injected carefully via environment. By design, sub-agents run in separate sessions with their own contexts, so a crash or abort in one agent won’t corrupt others【33†L175-L184】.

---

## 4. Ontology Extraction & Vectorization

Once raw items are scraped, we **normalize them into an ontology**. This involves: 

- **Structured prompts:** We feed each agent’s outputs into LLM prompts (using Codex/GPT) that emit structured JSON of capabilities. For example, the prompt might be: *“List what this business offers, sells, or is known for, in JSON format.”* The model outputs fields like `sells`, `services`, `attributes`, each an array of canonical terms. We should engineer a prompt template and possibly fine-tune or few-shot to ensure consistency. (There is no single “correct” output; human review might refine it.)  

- **Canonical mapping:** We maintain a lightweight ontology of terms (tables `ontology_nodes(canonical, parent, synonyms)`). When the LLM outputs items (e.g. “vegan options”), we map synonyms to canonical terms (e.g. map “vegan options” → “Vegan”). This can be done via a lookup or a small embedding similarity check. For example, a business might get `attributes: ["plant-based", "dairy-free"]`, both mapped to canonical node “Vegan”. This avoids drift.  

- **Per-item embeddings:** We store embeddings for each menu item (or capability string) rather than just the full business description. For instance, for each menu_item row we compute an embedding vector of `"name + description"`, and for each canonical capability we also store an embedding of the term. This enables fine-grained search (matching queries like “avocado toast” to specific items). (If using Postgres + pgvector, `menu_items` and `capabilities` tables can have a `vector` column.)  

- **Database schema:** An example relational schema is:  

  | Table           | Key Columns (examples)                                      |
  |-----------------|-------------------------------------------------------------|
  | **businesses**  | `business_id (PK), name, address, lat, lon, last_updated`   |
  | **menu_items**  | `item_id (PK), business_id (FK), section, item_name, description, price, dietary_tags, raw_text, embedding` |
  | **capabilities**| `cap_id (PK), business_id (FK), type (sells/services/attr), items(JSONB), confidence, embedding` |
  | **ontology_nodes**| `node_id (PK), canonical_term, parent_id, synonyms(JSONB)` |

  For example, a **menu_items** JSON row might be:  

  ```json
  {
    "item_id": "xyz789",
    "business_id": "biz123",
    "section": "Breakfast",
    "item_name": "Vegan Burrito",
    "description": "Tofu scramble, black beans, avocado...",
    "price": 11.50,
    "dietary_tags": ["vegan", "gluten-free"],
    "raw_text": "Vegan Burrito - Tofu scramble,...",
    "embedding": [ ...vector... ]
  }
  ```

  And a **capabilities** row:  

  ```json
  {
    "cap_id": "cap456",
    "business_id": "biz123",
    "type": "attributes",
    "items": ["Vegan", "Organic"],
    "confidence": 87,
    "embedding": [ ...vector... ]
  }
  ```

To actually get these fields, the *Inference Agents* (Layer 2) operate on the cleaned evidence bundle. For example, the **Capability Aggregation Agent** might answer “What can this business provide?” by picking out menu_items and keywords (e.g. “sells: X”). The **Operational Profile Agent** might infer “outdoor seating vs takeaway” from phrases (“patio”, “grab-n-go”). We can craft prompts or simple rule-based logic for these as needed. The key is that *all outputs remain traceable* (we keep pointers to which source snippet gave each claim). 

Finally, once structured fields are in place, we compute final embedding vectors using only the **canonical text** (e.g. join capabilities plus a short summary). These are stored in `businesses.embedding`. We deliberately exclude any value-laden content (e.g. political tags) from the core vector.  

---

## 5. Orchestration & Reliability

**Sync vs Async:** The Router skill can run sub-agents asynchronously (with `sessions.spawn`) or synchronously (`/subagents spawn mode:session`). In practice, we spawn scrapers in parallel and continue when all have completed or timed out. OpenClaw’s lane-queue (one task at a time per session) simplifies serial processing for each agent, while sub-agents allow parallelism【33†L175-L184】. 

**Retries & Backoff:** Each scraper skill should catch transient failures (e.g. HTTP 500 or 429). We implement exponential backoff (e.g. 1s → 2s → 4s) before retrying, and ultimately skip after N attempts. OpenClaw can itself retry tools using `apply_patch` or by re-spawning a sub-agent. Results of each scrape include a status code and number of attempts. 

**Idempotency & Deduplication:** We use URLs and content hashes to avoid reprocessing the same source. For each fetched page or file, store an `etag` or MD5 hash. If nothing changed since last crawl, skip re-parsing. Similarly, menu items can be deduplicated by name+price. OpenClaw’s tooling allows caching outputs of skills (using the `outputs` folder) to prevent duplicate work. 

**Evidence Scoring:** Each extracted claim or capability carries a confidence (e.g. source trustworthiness, extraction quality). For example, a Google Places “type” might score 10 points, a direct menu scrape 40 points, a single review mention 5 points, etc. We can tune weights so that the final “evidence score” reflects credibility【21†L156-L164】. Contradictions (e.g. one source says “vegan” and another doesn’t mention it) are flagged in Layer 1 and debated in arbitration. 

**Agent-to-Agent Communication:** Agents update a shared state (e.g. Redis or DB) with their findings. For example, once a scraper writes menu_items, it emits a completion event. The Router or a Coordinator Agent watches for these events (or polls) to know when to move to Layer 2. OpenClaw’s own `agent send` and `subagent` messages allow passing messages between agents if needed, but simpler is a central database or queue. 

---

## 6. Security, Privacy & TOS Compliance

Given the aggressive scraping, compliance is key.  

- **Legal/TOS:** We avoid violating terms. For instance, Instagram’s ToS explicitly forbids automated scraping without permission【21†L156-L164】. Therefore, the Social Agent should prefer official APIs and business accounts (Graph API for Business Profiles). We explicitly *do not* scrape private or user-generated content. Similarly, if a site’s robots.txt disallows crawling, the agent should skip or lower priority.  

- **Privacy:** Collected data is public (menus, signage, business descriptions). However, we must still treat any personal data (e.g. owner name from filings) with care. Encryption at rest and access control on logs should be used. Logging of scraped content should strip any PII irrelevant to search.  

- **Sandboxing & Vetting:** As noted, OpenClaw encourages sandboxed tool use【6†L188-L196】. Each skill should run in a controlled environment (e.g. a Docker container with limited network). Third-party skills must be reviewed before installation, as they run arbitrary code. Secrets (API keys) are injected only into the agent runtime and not logged.  

- **Rate-Limits and Etiquette:** We throttle all external calls (e.g. max 5 requests/sec to Google, pause on 429). For APIs like Google/Yelp, we obey their usage limits (e.g. 30 qps for Places)【21†L156-L164】. If authentication is required (e.g. Yelp API key), we use agent-level config with monthly quotas.  

Overall, we enforce a conservative default. Only signals in the **public domain** are ingested. No crowd-sourced user info or private data is used unless explicitly allowed (which is currently not planned).  

---

## 7. Monitoring, Logging & QA

To maintain data quality: 

- **Logging:** Every agent logs its steps and outputs (e.g. “Fetched menu.html, found 20 items”). OpenClaw’s built-in logs (via `/subagents log`) record LLM reasoning and tool calls. We aggregate logs into a centralized dashboard (e.g. ELK or Grafana). 

- **Similarity Thresholds:** After embedding, we can do sanity checks. For example, compare a new business vector to its last vector (if re-scraping). If cosine similarity < 0.7 (huge shift) or =1.0 (identical), flag for manual review. Also, if two distinct businesses produce nearly identical vectors, alert on possible data merge errors.  

- **Human-in-the-loop:** For critical fields (e.g. capability list), if confidence is low (<50%) we could queue it for a brief manual review. In practice, start without human check to iterate quickly, then add spot checks on edge cases (via an internal review UI).  

- **Duplicate Detection:** The Evidence Normalization step deduplicates cross-modality claims. We also cluster menu items by similarity (e.g. “Latte” vs “Caffè Latte”). If duplicates exist, we collapse them. QA metrics include recall of known capabilities for a test set of businesses, and false positive rates.  

- **Alerting:** We set up alerts for tool failures (e.g. X% of scrapers erroring), rate-limit hits, or budget overruns. For example, if OCR agents begin to extract gibberish from many images, that may indicate a library update broke compatibility.  

This monitoring ensures we catch drift or model issues early.  

---

## 8. Resources, Cost & Scaling

**Compute:** Each OpenClaw agent run is lightweight (mainly HTTP calls and Python/JS code). The heavy work is LLM prompting and embedding. Embeddings can be batched on GPUs or a CPU with accelerated BLAS. For scale (thousands of businesses), use batch embeddings via OpenAI’s Text Embedding API or run a local model on an NVIDIA DGX.  

**Token Costs:** As of 2026, GPT-5.2-codex costs ~$1.75 per 1,000 tokens (input)【30†L61-L69】. A typical prompt to extract capabilities might be ~200 tokens, so one agent run is a few cents. Embeddings (e.g. `text-embedding-3-large`) are extremely cheap at ~$0.13 per million tokens【31†L91-L94】. For a menu of 100 items, even 1000 tokens total is $0.00013. In summary, LLM costs are modest compared to data and compute.  

**Memory/Storage:** Storing embeddings for, say, 10,000 items (1536-d floats) is ~60 MB of vector data, negligible. Vector DBs (Faiss, Pinecone) scale linearly; we can shard per city.  

**Concurrency:** OpenClaw can run many agents in parallel (each in a Docker). We might run 5–10 scrapers per second across the fleet. For large crawls, we can horizontally scale the gateway container with a queue. 

**Caching:** We will cache API responses (e.g. place details) and page downloads. This saves both cost and avoids redundant work.  

**Scaling Plan:** 
- Start small (scrape 100 businesses end-to-end) to measure throughput. 
- Profile: if scraping 1000 businesses twice monthly, we might use a few CPU cores for HTML agents, one GPU for embeddings, and distribute OpenClaw processes.  
- If token spend grows (e.g. thousands of queries), consider fine-tuning a smaller local LLM for capability extraction to cut cost.  
- Use batching where possible: e.g. fetch all Place data in parallel, then feed URLs one by one to the router.  

---

## 9. OpenClaw Config & Example Skills

**Configuration:** Each agent has its own workspace. We can define in `agents.list` (in `openclaw.json`) entries like:  

```json
{
  "agents": {
    "router": {"subagents": {"model": "gpt-5.2-codex"}},
    "html-scraper": {"subagents": {"model": "gpt-5.1-codex"}},
    "spa-scraper": {"subagents": {"model": "gpt-5.1-codex"}},
    // ...
  }
}
```

This ensures the router uses the best model while sub-agents may use smaller ones for efficiency. We also set `skills.load.extraDirs` to our workspace (for custom skills).  

**Router Skill (pseudocode):**  

```yaml
# router-skill/SKILL.md
---
name: router-skill
description: Inspect a business URL and dispatch to appropriate scrapers
inputs:
  - name: business_url
    type: text
    required: true
run:
  - name: inspect-url
    tool: Browser.open  # or Exec curl
    args:
      url: "{{business_url}}"
    id: fetch
  - name: analyze-content
    instructions: |
      The assistant determines the content type (HTML, PDF, etc.) and decides which agents to spawn.
    llm:
      model: codex
    id: decide
  - name: spawn-agents
    tool: CLI
    command: |
      {% if decide.output contains "HTML" %}
      /subagents spawn html-scraper "scrape {{business_url}}"
      {% endif %}
      {% if decide.output contains "PDF" %}
      /subagents spawn pdf-parser "scrape {{business_url}}"
      {% endif %}
      // etc.
```

On completion, the Router does a final `send` to the master agent or updates DB.  

**HTML Scraper Skill (SKILL.md excerpt):**  

```yaml
name: html-scraper
description: Fetch static HTML and extract menu items.
inputs:
  - name: target_url
run:
  - name: fetch_page
    tool: Browser.open  # headless HTTP fetch
    args:
      url: "{{target_url}}"
    id: page
  - name: parse_menu
    llm:
      model: gpt-5.1-codex
      instructions: |
        Extract all menu sections, item names, descriptions, and prices from the HTML stored in file page.content.
        Return JSON of items as described in schema.
    id: extract
  - name: write_output
    tool: File.write
    args:
      path: output/menu_items.json
      content: "{{extract.result}}"
```

This illustrates the pattern: fetch content, parse (possibly with LLM or code), and output structured JSON. Other skills (PDF, OCR, API) follow similarly. 

Example **skill manifest** for JSON output: each SKILL.md would declare its outputs so OpenClaw can route results downstream. 

---

## 10. Timeline & Phases

| **Phase**       | **Objectives & Activities**                                                                                    | **Deliverables**                           |
|-----------------|--------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| **1. Prototype (Week 1–2)**  | Set up OpenClaw environment. Create router skill and one basic scraper (HTML). Integrate Google Places API. | Initial working pipeline: Google data → HTML scrape for menus of a few businesses. |
| **2. Expanded Scrapers (Week 3–5)** | Add SPA scraping (Playwright), PDF parsing, image OCR agents. Implement API and social connectors. | Multi-modal scraping suite with test coverage (each modality works on sample sites). |
| **3. Ontology & Embeddings (Week 6–7)** | Develop capability extraction prompts. Build ontology term list and mapping logic. Implement item-level embedding. | Database schema and initial data for scraped businesses; vector embeddings generated. |
| **4. Inference & Arbitration (Week 8–9)** | Implement Layer 2 agents to merge evidence (capabilities, business model). Build master arbiter logic to finalize record. | End‐to‐end business profile records with confidence scores and embedded vectors. |
| **5. Orchestration & QA (Week 10–11)** | Implement retry/backoff and dedup logic. Add monitoring/logging dashboards. Perform QA on sample data. | Robust pipeline with error handling, alerting, and documentation of process. |
| **6. Scale & Optimization (Week 12+)** | Scale to city-wide data. Optimize cost (batch queries, adjust models). Re-evaluate freshness policy. | Scaled deployment prototype; performance benchmarks and cost estimates. |

Each phase ends with a demoable deliverable (e.g. a set of enriched business vectors). We iterate based on feedback, tuning confidence weights and adding refinements (like embedding QA or user feedback loops). 

---

**Figures:** The above architecture (router, agents, DB) is shown in the Mermaid flowchart. This blueprint outlines how OpenClaw orchestrates multi-modal data ingestion into a unified semantic index for businesses.

