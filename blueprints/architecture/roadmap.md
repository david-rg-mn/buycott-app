# Buycott Roadmap

This roadmap defines the next critical system upgrades required to stabilize, optimize, and productionize the Buycott semantic search architecture.

---

# Phase 1: Observability (Highest Priority)

## Problem

Currently, the system lacks visibility into performance characteristics. You do not know:

- How long search takes
- Where latency occurs
- What queries fail
- What similarity scores look like

## Objectives

Add full timing instrumentation across the search pipeline.

## Required Metrics

Log the following for every search request:

- Request start timestamp
- Embedding generation time
- Vector search time
- Database query time
- Ranking time
- Total request time

### Conceptual Example

Search request:

- embedding_time = 42ms
- db_time = 18ms
- ranking_time = 3ms
- total = 110ms

## Outcome

This enables:

- Identifying bottlenecks
- Performance tuning
- Regression detection
- Evidence-based optimization

Without observability, optimization is guesswork.

---

# Phase 2: Query Logging and Analytics

## Problem

The system does not retain query behavior data.

## Required Data to Store

For each search request:

- Query string
- Timestamp
- Result count
- Top similarity score

## Outcome

Enables:

- Long-tail query analysis
- Ontology gap detection
- Ranking logic improvement
- Failure detection
- Behavioral analytics

This converts the system into a learning engine.

---

# Phase 3: Location-Aware Ranking

## Current Ranking

rank = semantic_similarity

## Upgrade

Implement combined ranking:

rank = semantic_similarity * semantic_weight + distance_decay

## Outcome

- Nearby businesses rank higher
- Semantic relevance remains primary
- Improves real-world usability
- Improves perceived intelligence

---

# Phase 4: Hybrid Search (Semantic + Keyword)

## Problem

Pure semantic search can produce false positives.

## Upgrade

Combine:

- Semantic embedding similarity
- Exact keyword match boost

Example:

Query: "pencil sharpener"

If description contains exact phrase:
→ Apply ranking boost

## Outcome

- Improved precision
- Reduced false positives
- Better relevance accuracy

---

# Phase 5: Evidence Highlighting in UI

## Current State

Evidence is computed but not fully surfaced visually.

## Upgrade

Display:

- Matching semantic terms
- Ontology triggers
- Confidence explanations
- Evidence reasoning

## Outcome

- Increased user trust
- Improved transparency
- Stronger explainability

---

# Phase 6: Caching

## Problem

Repeated queries recompute embeddings and search unnecessarily.

## Upgrade Options

Implement one:

- In-memory cache
- Redis container
- Query-result caching layer

## Outcome

- Reduced latency
- Reduced compute load
- Improved responsiveness
- Better scalability

---

# Phase 7: Background Re-Embedding Jobs

## Problem

Embedding generation should not block search.

## Upgrade

1. Create background job system t
2. Regenerate embeddings when business data changes
3. Update vector store asynchronously

## Outcome

- Improved scalability
- Faster write operations
- Better system performance

---

# Phase 8: Personalization (Later Stage)

## Prerequisite

Only after core ranking system is stable.

## Upgrade

Add:

- User preference storage
- Personalized ranking adjustments
- Neutrality-preserving constraints

## Outcome

- Improved user experience
- Increased relevance
- Advanced system capability
- Lock in UI / UX

---

# Priority Order Summary

1. Observability
2. Query Logging
3. Location-Aware Ranking
4. Hybrid Search
5. Evidence Highlighting
6. Caching
7. Background Embedding Jobs
8. Personalization

# Strategic Principle

Optimize and stabilize the engine before expanding features or locking UI design.
