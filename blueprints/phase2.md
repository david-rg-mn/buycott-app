## Buycott — Phase 2 Feature Expansion (COLLECT-STRUCTURE)

This structure assumes **Phase 1 already implemented**:

* L4 semantic search
* Ontology expansion
* Embedding pipeline
* OpenClaw extraction agents
* pgvector database
* Flutter map UI
* Minutes-away metric
* Evidence score visualization

Phase 2 builds on that foundation to improve discovery, trust, civic alignment, and user experience.

---

# 1. Discovery Control and Local-First Reinforcement

## 1.1 Local-First Default + Reveal Chains (Already decided)

**Purpose**

* Prioritize independent businesses while preserving completeness option.

**Behavior**

* Default query filter:

  ```
  is_chain = false
  ```
* Optional user toggle:

  ```
  Show chain stores
  ```

**System Changes**

* Add fields:

  ```
  businesses.is_chain BOOLEAN
  businesses.chain_name TEXT
  ```

**Impact**

* Maximizes discovery of independent businesses.
* Preserves user autonomy and neutrality.

---

## 1.2 Discovery Highlighting Layer

**Purpose**

* Visually emphasize unfamiliar or independent businesses.

**Behavior**

* Applies subtle visual distinction:

  ```
  glow effect
  highlight border
  discovery badge
  ```

**Logic Inputs**

* is_chain = false
* low familiarity likelihood (future enhancement)
* specialty classification (optional)

**Impact**

* Encourages exploration.
* Reinforces Buycott’s civic mission.

---

# 2. Evidence Transparency and Trust Layer

## 2.1 Evidence Explanation View

**Purpose**

* Explain why a business appears for a search query.

**User Interaction**

* Tap evidence score square.

**Displays**

```
Evidence sources:
• Website mentions phone accessories
• Category: electronics repair
• Semantic similarity match: charging cable
• Ontology expansion: electronics accessory
```

**Backend Requirements**

* Store semantic match metadata:

  ```
  evidence_sources
  ontology_matches
  semantic_similarity_score
  ```

**Impact**

* Builds trust in semantic inference.
* Improves transparency.

---

## 2.2 Source Transparency View

**Purpose**

* Show origin of business information.

**Displays**

```
Sources:
• Business website
• Public directory listing
• Google Places description
```

**Database Changes**
Add source table:

```
business_sources

business_id
source_type
source_url
last_fetched
```

**Impact**

* Reinforces civic neutrality.
* Improves credibility.

---

## 2.3 Data Freshness Indicator

**Purpose**

* Show recency of information.

**Displays**

```
Last updated: 14 days ago
```

**Backend Requirements**

* Track:

  ```
  businesses.last_updated
  ```

**Impact**

* Improves reliability perception.
* Encourages continuous agent enrichment.

---

# 3. Semantic UX and Query Assistance Layer

## 3.1 Semantic Suggestions While Typing

**Purpose**

* Assist users in forming successful queries.

**Example**
User types:

```
charg
```

Suggestions:

```
phone charger
laptop charger
USB cable
charging cable
```

**Backend Components**

* Ontology term lookup
* Prefix matching
* Optional embedding similarity lookup

**Database Table**

```
ontology_terms

term
embedding
```

**Impact**

* Improves usability.
* Increases semantic search success rate.

---

## 3.2 Related Item Suggestions

**Purpose**

* Suggest semantically related items after search.

**Example**
Search:

```
camera film
```

Suggestions:

```
camera battery
photo printing
camera strap
```

**Logic**

* Ontology child and sibling relationships.

**Impact**

* Encourages deeper discovery.
* Expands user exploration.

---

# 4. Capability Visualization Layer

## 4.1 Capability Discovery View

**Purpose**

* Show inferred business capability profile.

**Displays**

```
Likely carries:
• charging cables
• phone accessories
• screen protectors
• electronics supplies
```

**Backend Requirements**

* Store ontology relationships per business:

  ```
  business_capabilities

  business_id
  ontology_term
  confidence_score
  ```

**Impact**

* Reveals latent business capability.
* Strengthens semantic trust.

---

## 4.2 Specialist Indicator

**Purpose**

* Highlight niche and specialty businesses.

**Displays**

```
Specialist badge
```

**Classification Criteria**

* Narrow ontology scope
* Specific semantic domain concentration

Examples:

```
camera stores
art supply stores
instrument stores
```

**Impact**

* Encourages discovery of unique businesses.

---

## 4.3 Independent Business Indicator

**Purpose**

* Reinforce local-first identity.

**Displays**

```
Independent badge
```

**Criteria**

```
is_chain = false
```

**Impact**

* Strengthens civic alignment.

---

# 5. Physical Accessibility Filters

## 5.1 Walking Distance Filter

**Purpose**

* Restrict results to immediate physical accessibility.

**User Toggle**

```
Within walking distance
```

**Backend Logic**
Filter:

```
walking_time <= threshold
```

Threshold example:

```
15 minutes
```

**Requires**

* Walking-time calculation via routing API.

**Impact**

* Reinforces immediacy advantage.

---

## 5.2 Open Now Filter

**Purpose**

* Show currently accessible businesses.

**User Toggle**

```
Open now
```

**Backend Requirements**
Store:

```
business_hours
```

Filter based on:

```
current_time
```

**Impact**

* Improves real-world usability.

---

# 6. Ontology Expansion Enhancements

## 6.1 Ontology Suggestion Integration

**Purpose**

* Use ontology relationships to enhance UX.

**Examples**
Search:

```
moving supplies
```

Suggest:

```
boxes
packing tape
bubble wrap
```

**Backend Requirements**

* Ontology graph traversal.

---

## 6.2 Ontology Capability Mapping

**Purpose**

* Map business embedding proximity to ontology terms.

**Generates**

```
business capability profile
```

Stored in:

```
business_capabilities table
```

**Impact**

* Improves explanation and discovery features.

---

# 7. Backend and Infrastructure Additions

## 7.1 New Database Tables

Add:

```
business_sources
business_capabilities
ontology_terms (expanded usage)
```

Add fields:

```
businesses.is_chain
businesses.last_updated
```

---

## 7.2 Backend API Endpoints

Add endpoints:

```
/search_suggestions
/evidence_explanation
/business_capabilities
/filter_local_only
/filter_open_now
/filter_walking_distance
```

---

# 8. Frontend (Flutter) Additions

New UI components:

```
Local-only toggle (default enabled)
Show chains toggle
Evidence explanation panel
Specialist badge
Independent badge
Open now filter toggle
Walking distance filter toggle
Semantic suggestion dropdown
Capability display panel
```

---

# 9. Phase 2 Strategic Impact

Phase 2 transforms Buycott from:

```
Semantic local search engine
```

Into:

```
Transparent civic semantic discovery infrastructure
```

Key improvements:

* Increased discovery power
* Increased trust and transparency
* Increased usability and accessibility
* Stronger civic mission alignment
* Improved semantic UX

---

# Critique

## Strengths

* Builds directly on Phase 1 foundation.
* Minimal architectural disruption.
* Significant UX and trust improvements.
* Reinforces civic neutrality and transparency.

## Weaknesses

* Requires ontology maintenance discipline.
* Additional backend metadata tracking required.

## Blind Spots

* Requires clear UX communication to avoid confusion about inference vs certainty.
* Requires reliable chain classification.

---

# Phase 2 Summary

Phase 2 enhances Buycott by adding:

* Discovery reinforcement
* Evidence transparency
* Semantic UX assistance
* Capability visualization
* Physical accessibility filters
* Ontology-powered UX enhancements

All built on Phase 1 semantic search and embedding infrastructure.
