CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS businesses (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  lat DOUBLE PRECISION NOT NULL,
  lng DOUBLE PRECISION NOT NULL,
  embedding VECTOR(384) NOT NULL,
  text_content TEXT NOT NULL,
  is_chain BOOLEAN NOT NULL DEFAULT FALSE,
  chain_name TEXT,
  website TEXT,
  phone TEXT,
  hours_metadata JSONB,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ontology_terms (
  term TEXT PRIMARY KEY,
  parent_term TEXT REFERENCES ontology_terms(term),
  embedding VECTOR(384) NOT NULL,
  depth INTEGER NOT NULL,
  source TEXT NOT NULL DEFAULT 'seed',
  CHECK (depth >= 0)
);

CREATE TABLE IF NOT EXISTS business_sources (
  id BIGSERIAL PRIMARY KEY,
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_url TEXT NOT NULL,
  last_fetched TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business_capabilities (
  id BIGSERIAL PRIMARY KEY,
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  ontology_term TEXT NOT NULL REFERENCES ontology_terms(term) ON DELETE CASCADE,
  confidence_score DOUBLE PRECISION NOT NULL,
  source_reference TEXT,
  source_snippet TEXT,
  semantic_similarity_score DOUBLE PRECISION,
  ontology_matches JSONB,
  UNIQUE (business_id, ontology_term),
  CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

CREATE TABLE IF NOT EXISTS business_hours (
  id BIGSERIAL PRIMARY KEY,
  business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  day_of_week INTEGER NOT NULL,
  opens_at TIME NOT NULL,
  closes_at TIME NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  CHECK (day_of_week BETWEEN 0 AND 6)
);

CREATE INDEX IF NOT EXISTS idx_businesses_embedding_ivfflat
  ON businesses USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_ontology_terms_embedding_ivfflat
  ON ontology_terms USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 40);

CREATE INDEX IF NOT EXISTS idx_business_sources_business_id
  ON business_sources (business_id);

CREATE INDEX IF NOT EXISTS idx_business_capabilities_business_id
  ON business_capabilities (business_id);

CREATE INDEX IF NOT EXISTS idx_business_capabilities_ontology_term
  ON business_capabilities (ontology_term);
