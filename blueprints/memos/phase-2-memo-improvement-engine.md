Buycott Improvement Engine Blueprint Memo

Logging, Analytics, and Continuous Search Optimization Architecture
Version: Phase 2 Infrastructure
Scope: pgvector + Docker + Semantic Search Pipeline

1. Purpose

This memo defines the architecture, operation, and verification procedures for the Buycott Query Logging and Improvement Engine.

This system enables:

Observability of semantic search performance

Detection of ontology and coverage gaps

Measurement of embedding and ranking quality

Continuous improvement through usage-driven feedback

This transforms Buycott from a static semantic search system into a continuously improvable search engine.

2. Current System Context (from Project Architecture)

Based on your project:

Core infrastructure already deployed:

PostgreSQL with pgvector (buycott-db container)

Semantic embedding search pipeline

Ontology expansion pipeline

Flutter frontend

Backend API container (buycott-api)

Docker Compose orchestration

Vector embedding database

Defined in:

services:
  db:
    image: pgvector/pgvector:pg16
  api:
    build: ./backend

This provides the correct foundation for query logging.

3. Improvement Engine Architecture Overview

The improvement engine consists of three layers:

Layer 1 — Query Logging (automatic)
Layer 2 — Query Analysis (periodic)
Layer 3 — System Improvement (manual or automated)
4. Layer 1 — Query Logging Architecture
Purpose

Capture behavioral and quality signals from real searches.

Required Database Table

Add to database/schema.sql:

CREATE TABLE IF NOT EXISTS query_logs (
  id BIGSERIAL PRIMARY KEY,
  query TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  result_count INTEGER NOT NULL,
  top_similarity_score FLOAT NOT NULL,
  embedding_time_ms FLOAT,
  search_time_ms FLOAT,
  total_time_ms FLOAT
);

This integrates directly with your existing pgvector database.

Logged Data Definition

Each search request produces one record:

Example:

{
  "query": "vegan bakery",
  "timestamp": "2026-02-19T22:14:05Z",
  "result_count": 6,
  "top_similarity_score": 0.89,
  "embedding_time_ms": 42,
  "search_time_ms": 18,
  "total_time_ms": 60
}
5. Runtime Logging Flow

Current runtime flow:

User query
  ↓
Backend API receives query
  ↓
Embedding generated
  ↓
pgvector search executed
  ↓
Results returned

Improvement engine extends flow:

User query
  ↓
Embedding generated
  ↓
Vector search executed
  ↓
Results returned
  ↓
Query log written to PostgreSQL

Logging adds negligible overhead.

6. Docker Integration Architecture

Your system already uses Docker Compose with Postgres.

Containers:

buycott-db      → PostgreSQL + pgvector
buycott-api     → backend API

Logging writes directly to:

buycott-db → query_logs table

No additional containers required.

7. Verification Procedures (Docker Environment)
Step 1 — Confirm database container is running
docker ps

Expected:

buycott-db
buycott-api
Step 2 — Connect to database container
docker exec -it buycott-db psql -U buycott -d buycott
Step 3 — Verify logging table exists
SELECT table_name FROM information_schema.tables
WHERE table_name = 'query_logs';

Expected:

query_logs
Step 4 — Verify log entries exist
SELECT * FROM query_logs LIMIT 10;

Expected example:

id | query        | result_count | top_similarity_score
1  | vegan pizza  | 4            | 0.82
2  | bike repair  | 0            | 0.42

This confirms logging is functional.

8. Layer 2 — Query Analysis Engine

Logging alone does not improve the system.

Analysis extracts actionable intelligence.

Analysis script reads query_logs and computes:

failure rate

low-similarity queries

ontology gaps

frequent searches

coverage weaknesses

Example analysis query:

SELECT query, COUNT(*)
FROM query_logs
WHERE top_similarity_score < 0.5
GROUP BY query
ORDER BY COUNT(*) DESC;

This identifies system weaknesses.

9. Layer 3 — Improvement Workflow

Analysis drives improvements in three areas:

9.1 Ontology Expansion

Detected weakness:

"refill station detergent"
score: 0.41

Action:

Add ontology entries and businesses.

Result:

Future similarity improves.

9.2 Ranking Optimization

Logs enable tuning:

rank = semantic_score + distance_factor

Improves real-world usability.

9.3 Embedding Model Evaluation

Compare average similarity scores across models.

Switch to better model if needed.

10. Deployment Lifecycle Behavior
Development Phase

Logging runs automatically.

Developer verifies logging periodically.

No continuous analysis required.

Early Deployment Phase

Run analysis manually:

docker exec buycott-api python analyze_logs.py

Frequency:

weekly

or after significant traffic

Mature Deployment Phase

Analysis runs automatically via scheduled job:

cron → analysis → report generation
11. Improvement Engine Feedback Loop

Full continuous improvement loop:

User queries
  ↓
Logs recorded
  ↓
Analysis identifies weaknesses
  ↓
Ontology expanded / ranking tuned / data improved
  ↓
System redeployed
  ↓
Search quality improves

This loop repeats indefinitely.

12. Operational Commands Reference
Enter database
docker exec -it buycott-db psql -U buycott -d buycott
View logs
SELECT * FROM query_logs ORDER BY timestamp DESC LIMIT 20;
Count logs
SELECT COUNT(*) FROM query_logs;
Detect failures
SELECT query, COUNT(*)
FROM query_logs
WHERE result_count = 0
GROUP BY query
ORDER BY COUNT(*) DESC;
13. System Impact and Capabilities Enabled

This infrastructure enables:

Ontology-driven improvement

Search quality measurement

Semantic model evaluation

Ranking optimization

Data coverage expansion

Performance optimization

Failure detection

This is foundational infrastructure for any production semantic search system.

14. Integration With Existing Buycott Pipeline

Your current components already support this architecture:

pgvector database → supports logging table

Docker Compose → supports persistence

Backend API → supports log insertion

Pipeline architecture → supports ontology improvements

No architectural restructuring required.

Only additions:

query_logs table

logging insertion in search handler

optional analysis script

15. Final Operational Summary

Logging runs continuously and automatically.

Improvement occurs only when analysis is performed and system updates are deployed.

Docker integration provides full persistence and observability.

This system enables Buycott to evolve continuously as usage increases.

If desired, a production-grade query_logs.sql schema and analyze_logs.py script can be generated specifically for your existing backend structure.