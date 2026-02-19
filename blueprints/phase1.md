## Buycott — Complete Structured Project Outline (COLLECT-STRUCTURE)

---

# 1. Core Mission and Principles

## 1.1 Mission

* Enable users to find specific real-world items locally using semantic search.
* Strengthen local economies by revealing existing neighborhood commerce capability.
* Provide civic infrastructure that maps product availability geographically.

## 1.2 Core Design Principles

### Neutrality

* No ranking based on profit, popularity, or paid influence.
* Evidence visualization only, not recommendation ordering.
* Geographic placement is the primary organizing principle.

### Civic Alignment

* Donation-supported model.
* Open source codebase.
* No advertising or sponsored placement.

### Transparency

* Evidence score reflects observable signals only.
* All business data traceable to public sources.
* Ontology expansion explainable and inspectable.

### Immediate Utility

* Focus on time-to-possession (“minutes away vs days away”).
* Prioritize solving real-world user needs instantly.

---

# 2. Core User Experience Architecture

## 2.1 Interaction Model (Transit-Style Map-First UI)

### Permanent Base Layer

* Full-screen map always visible.
* User location centered or tracked.

### Dynamic Overlay Layers

* Search bar overlay
* Business pins
* Bottom sheet with business details

### Temporary Interaction Layers

* Search suggestions overlay
* Ontology-expanded query suggestions (future)

---

## 2.2 Map Pin Visual Model

Each pin contains:

```
Gradient square:
  Top number: minutes away
  Bottom number: evidence strength score (0–100)

Pin location: exact geographic position
```

Example:

```
[ 6m ]
[ 82 ]
```

Represents:

* Immediate accessibility
* Semantic evidence strength

---

## 2.3 Bottom Sheet Information Model

Displays:

```
Business name
Minutes away
Evidence strength indicator
Directions button
Call button
Website button
Hours
Source evidence indicators
```

Does NOT display:

* Rankings
* Sponsored placements
* Popularity scores

---

# 3. Semantic Search Architecture (L4 Target Level)

## 3.1 Target Search Capability Level: L4 — Specific Product Type

Supports queries like:

```
USB-C to Lightning cable
birthday candle number 5
packing tape
camera film
phone charger
```

Does NOT require explicit mention in business text.

Uses semantic inference.

---

## 3.2 Query Processing Pipeline

Step 1 — User enters query

Step 2 — Query embedding generation

Step 3 — Ontology expansion generates parent concepts

Example expansion:

```
USB-C to Lightning cable
→ USB cable
→ charging cable
→ phone accessory
→ electronics accessory
```

Step 4 — Generate embeddings for expanded concepts

Step 5 — Vector similarity search against business embeddings

Step 6 — Combine results

Step 7 — Compute evidence strength score

Step 8 — Return results to frontend

---

# 4. Ontology Expansion System

## 4.1 Ontology Purpose

* Expand query into semantically related parent concepts.
* Increase recall without reducing precision.
* Enable encapsulation of higher-level meaning.

---

## 4.2 Ontology Structure

Tree model:

```
Specific Item
  → Subtype
      → Product Category
          → Capability Domain
```

Example:

```
USB-C to Lightning cable
  → USB cable
      → charging cable
          → phone accessory
              → electronics accessory
```

---

## 4.3 Ontology Database Schema

```
ontology_terms

term TEXT
parent_term TEXT
embedding VECTOR(384)
depth INTEGER
```

Expansion depth limit:

```
3–5 levels maximum
```

---

# 5. Embedding and Semantic Matching System

## 5.1 Embedding Model

Recommended models:

```
BAAI/bge-small-en-v1.5
or
sentence-transformers/all-MiniLM-L6-v2
```

Purpose:

Convert text into semantic vectors.

---

## 5.2 Business Embedding Generation

OpenClaw agents extract:

* Website text
* Business descriptions
* Directory listings

Example extracted text:

```
"We repair phones and sell charging accessories."
```

Embedding generated once per business.

Stored in database.

---

## 5.3 Vector Database

Database:

```
PostgreSQL + pgvector
```

Business schema:

```
businesses

id
name
lat
lng
embedding VECTOR(384)
text_content
last_updated
```

---

## 5.4 Vector Similarity Search

Query embedding compared to business embeddings:

```
embedding similarity search
```

Results filtered and returned.

No ranking manipulation.

---

# 6. OpenClaw Agent Infrastructure

## 6.1 Purpose

Agents extract public business information to build semantic knowledge base.

Sources:

* Business websites
* Google Places descriptions
* Public directories

---

## 6.2 OpenClaw Agent Workflow

Step 1 — Discover business

Step 2 — Fetch public web content

Step 3 — Extract relevant text

Step 4 — Generate embedding vector

Step 5 — Store embedding in database

---

## 6.3 Infrastructure Platform

Runs on:

```
NVIDIA Spark / DGX Spark
```

Benefits:

* Parallel processing
* Fast embedding generation
* Continuous enrichment capability

---

# 7. Evidence Strength Scoring System

## 7.1 Purpose

Visualize semantic evidence strength.

Not ranking.

Not recommendation priority.

Only semantic proximity measure.

---

## 7.2 Evidence Score Components

Primary component:

```
embedding similarity(query_embedding, business_embedding)
```

Optional secondary components:

```
ontology expansion similarity
explicit extraction evidence
```

---

## 7.3 Evidence Score Output

Normalized:

```
0–100
```

Displayed visually via gradient square.

---

# 8. Minutes Away Metric System

## 8.1 Purpose

Show time-to-possession advantage vs online ordering.

Key user insight:

```
Immediate availability beats delayed delivery.
```

---

## 8.2 Computation Method

Uses routing APIs:

```
Google Distance Matrix API
or
Mapbox Directions API
```

Calculates:

```
driving time
walking time
```

Displays fastest mode.

---

# 9. Backend Architecture

## 9.1 Backend API Layer

Recommended:

```
FastAPI
```

Responsibilities:

* Handle search queries
* Generate embeddings
* Perform ontology expansion
* Query vector database
* Return results

---

## 9.2 Database Layer

Primary database:

```
PostgreSQL + pgvector
```

Stores:

* businesses
* embeddings
* ontology terms
* extracted text

---

## 9.3 OpenClaw Agent Layer

Runs separately.

Handles continuous data extraction and embedding generation.

---

# 10. Frontend Architecture

## 10.1 Framework

```
Flutter
```

Supports:

* iOS
* Android
* Web

---

## 10.2 Core Frontend Components

```
Map screen
Search bar
Pin rendering
Bottom sheet
Evidence visualization
Minutes-away visualization
```

---

# 11. Infrastructure Stack Summary

Extraction Layer:

```
OpenClaw agents
NVIDIA Spark
Python
```

Embedding Layer:

```
sentence-transformers or BGE models
```

Database Layer:

```
PostgreSQL + pgvector
```

Backend Layer:

```
FastAPI
```

Frontend Layer:

```
Flutter
```

---

# 12. Development Roadmap

## p1 — MVP

Implement:

```
Business extraction
Embedding generation
Vector database
Semantic search
Flutter map interface
Minutes-away metric
```

Supports L1–L4 search levels.

---

## Phase 2 — Ontology Expansion Integration

Add:

```
Ontology database
Query expansion engine
Expanded vector search
```

Improves L4 robustness.

---

## Phase 3 — Continuous Agent Enrichment

Deploy:

```
OpenClaw continuous crawling
Embedding refresh pipeline
```

Improves semantic coverage.

---

# 13. Strategic Advantages

## Unique Capabilities

Buycott answers:

```
Where can I get this specific item right now nearby?
```

Not:

```
What store should I visit?
```

---

## Competitive Differentiation

Compared to traditional systems:

| System      | Capability                  |
| ----------- | --------------------------- |
| Google Maps | location search             |
| Amazon      | product ordering            |
| Buycott     | semantic capability mapping |

---

# Critique

## Strengths

* Strong civic alignment and neutrality.
* Excellent architectural scalability.
* Embedding-based semantic matching supports powerful discovery.
* Ontology expansion improves robustness significantly.
* Transit-style UI maximizes usability and clarity.

---

## Weaknesses

* Ontology creation and maintenance requires ongoing effort.
* Semantic inference introduces probabilistic uncertainty.
* Initial OpenClaw extraction pipeline complexity moderate.

---

## Blind Spots

* Need clear UX communication of evidence strength meaning.
* Need safeguards against outdated business information.
* Need ontology governance structure for expansion accuracy.

---

# Final Summary

Buycott is a semantic geographic search system that:

* Maps real-world product availability using embeddings and ontology expansion.
* Uses OpenClaw agents to extract public business knowledge.
* Displays results geographically with evidence visualization.
* Optimizes for immediate local availability (“minutes away vs days away”).
* Operates as neutral civic infrastructure supporting local economies.

This architecture supports scalable, explainable, high-impact semantic discovery without requiring proprietary inventory integration.
