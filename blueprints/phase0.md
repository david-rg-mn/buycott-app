## Buycott — Phase 0: Governance, Ontology, and System Invariants (COLLECT-STRUCTURE)

Phase 0 establishes the **permanent architectural constraints and semantic governance model** that all future phases must operate within. It does not introduce user-facing features. Instead, it defines the structural rules that ensure Buycott remains a civic, neutral, semantic geographic capability index.

Phase 0 exists to prevent semantic drift, ontology corruption, ranking manipulation, and architectural instability before any functional implementation begins.

---

# 1. System Identity Lock Layer

## 1.1 Core System Definition

Buycott is structurally defined as:

```
Semantic geographic capability index
```

Buycott is explicitly not:

```
Recommendation engine
Advertising platform
Popularity-ranked directory
Engagement-optimized system
```

This definition governs:

* database schema design
* search pipeline behavior
* ontology scope
* UI presentation model

This identity lock ensures semantic neutrality permanently.

---

## 1.2 Capability-Based Discovery Model

Buycott answers:

```
Where can this item likely be obtained nearby?
```

Buycott does not answer:

```
Which business is best?
Which business is most popular?
Which business is preferred?
```

Results represent semantic capability proximity, not recommendations.

---

# 2. Ontology Governance Layer

## 2.1 Ontology Structural Model

Ontology defines hierarchical semantic relationships between product types and capability domains.

Example structure:

```
USB-C to Lightning cable
→ USB cable
→ charging cable
→ phone accessory
→ electronics accessory
```

Ontology enables semantic encapsulation and inference.

---

## 2.2 Ontology Expansion Constraints

Expansion rules:

```
Maximum expansion depth: 3–5 levels
Parent-child relationships only
No cyclic relationships
No business-specific ontology entries
```

Ontology represents product capability domains only.

Ontology never represents business preference.

---

## 2.3 Ontology Schema Definition

```
ontology_terms

term TEXT
parent_term TEXT
embedding VECTOR
depth INTEGER
source TEXT
```

Ontology must remain explainable and traceable.

---

# 3. Data Model Governance Layer

## 3.1 Business Knowledge Schema

Core business schema:

```
businesses

id
name
lat
lng
embedding VECTOR
text_content
is_chain BOOLEAN
chain_name TEXT
last_updated TIMESTAMP
```

Embedding represents semantic capability space.

---

## 3.2 Source Attribution Schema

Source tracking schema:

```
business_sources

business_id
source_type
source_url
last_updated
```

Ensures semantic inference remains traceable to public data.

---

## 3.3 Capability Attribution Schema

Capability inference schema:

```
business_capabilities

business_id
ontology_term
confidence_score
source_reference
```

Supports explainability layer.

---

## 3.4 Forbidden Schema Fields (Architectural Enforcement)

The following fields must never exist in the schema:

```
popularity_score
click_count
engagement_metric
paid_priority
sponsored_flag
conversion_rate
revenue_metric
```

This prevents ranking manipulation structurally.

---

# 4. Semantic Matching and Search Pipeline Governance Layer

## 4.1 Query Processing Model

All search queries must follow the defined pipeline:

```
User query
→ query embedding generation
→ ontology expansion
→ expanded embeddings generated
→ vector similarity search
→ local-first filtering
→ response returned
```

Search must remain semantic and explainable.

---

## 4.2 Vector Similarity Search Model

Matching based on:

```
embedding similarity
ontology proximity relationships
```

Matching must not use:

```
popularity signals
engagement signals
monetization signals
behavioral tracking
```

Ensures semantic neutrality.

---

## 4.3 Evidence Score Governance

Evidence score represents semantic similarity strength.

Evidence score must:

```
Be displayed only
Never affect ranking priority
Never affect filtering
```

Purpose is transparency only.

---

# 5. API Governance Layer

## 5.1 Allowed API Parameters

Permitted parameters:

```
query
location
include_chains BOOLEAN
open_now BOOLEAN
walking_distance BOOLEAN
```

These parameters control filtering only.

---

## 5.2 Forbidden API Parameters

The following parameters must never exist:

```
rank_by
priority
sponsored
promoted
boost
demote
```

Prevents ranking manipulation.

---

## 5.3 API Response Model

API returns semantic candidate set.

Sorting allowed by:

```
geographic distance
```

Not allowed by:

```
popularity
revenue
engagement
```

---

# 6. OpenClaw Extraction Governance Layer

## 6.1 Extraction Scope Constraints

OpenClaw agents may extract:

```
business website text
public directory descriptions
public business metadata
```

OpenClaw agents must never extract:

```
transaction data
customer behavior data
private or proprietary inventory data
```

Ensures civic neutrality.

---

## 6.2 Embedding Generation Constraints

Embeddings generated from:

```
extracted public text only
```

Embeddings must never incorporate:

```
popularity weighting
engagement weighting
monetization weighting
```

Ensures semantic purity.

---

# 7. Local-First Discovery Governance Layer

## 7.1 Chain Classification Model

Chain classification stored structurally:

```
businesses.is_chain BOOLEAN
businesses.chain_name TEXT
```

Enables filtering without ranking manipulation.

---

## 7.2 Local-First Default Filtering Rule

Default search filter:

```
is_chain = false
```

Chain inclusion allowed only via explicit user toggle.

This preserves civic mission while maintaining completeness.

---

# 8. Vertical Slice Governance Layer

## 8.1 Vertical Slice Development Model

All functional implementation must occur as complete vertical slices.

Each slice must include:

```
extraction layer
embedding generation
ontology expansion
vector search
UI visualization
evidence display
```

Prevents fragmented development.

---

## 8.2 Semantic Validation Requirement

Each vertical slice must validate:

```
semantic matching correctness
ontology expansion correctness
evidence explainability
```

Ontology refinement occurs based on validation results.

---

# 9. System Integrity Enforcement Summary

Phase 0 establishes permanent architectural constraints governing:

```
System identity
Ontology structure
Database schema
Search pipeline behavior
API behavior
Extraction pipeline behavior
Local-first discovery model
Vertical slice validation discipline
```

These constraints ensure Buycott remains:

```
Semantic
Neutral
Explainable
Civic-aligned
Architecturally stable
```

---

# Critique

## Strengths

* Prevents ranking and monetization corruption structurally.
* Ensures ontology remains explainable and consistent.
* Enables safe semantic expansion over time.
* Supports scalable vertical slice development.

## Weaknesses

* Requires ontology governance discipline.
* Requires strict adherence to schema constraints.

## Blind Spots

* Ontology expansion must be carefully maintained to avoid semantic gaps.
* Extraction quality directly affects semantic matching accuracy.

---

# Phase 0 Summary

Phase 0 defines the invariant semantic, architectural, and governance framework that ensures Buycott remains a civic semantic geographic capability index.

All functional implementation in Phase 1 and beyond must operate strictly within these constraints.
