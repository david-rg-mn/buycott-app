CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS businesses (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  lat DOUBLE PRECISION NOT NULL,
  lng DOUBLE PRECISION NOT NULL,
  embedding VECTOR(384),
  text_content TEXT NOT NULL,
  is_chain BOOLEAN NOT NULL DEFAULT FALSE,
  chain_name TEXT,
  phone TEXT,
  website TEXT,
  hours_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  timezone TEXT NOT NULL DEFAULT 'America/Chicago',
  specialty_score REAL NOT NULL DEFAULT 0,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business_sources (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_url TEXT,
  snippet TEXT,
  last_fetched TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, source_type, source_url)
);

CREATE TABLE IF NOT EXISTS ontology_terms (
  id BIGSERIAL PRIMARY KEY,
  term TEXT NOT NULL UNIQUE,
  parent_term TEXT,
  depth INTEGER NOT NULL CHECK (depth >= 0),
  source TEXT NOT NULL DEFAULT 'seed',
  embedding VECTOR(384),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_ontology_parent
    FOREIGN KEY(parent_term)
    REFERENCES ontology_terms(term)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS business_capabilities (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  ontology_term TEXT NOT NULL REFERENCES ontology_terms(term) ON DELETE CASCADE,
  confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
  source_reference TEXT,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, ontology_term)
);

CREATE INDEX IF NOT EXISTS idx_businesses_lat_lng ON businesses(lat, lng);
CREATE INDEX IF NOT EXISTS idx_businesses_is_chain ON businesses(is_chain);
CREATE INDEX IF NOT EXISTS idx_business_sources_business_id ON business_sources(business_id);
CREATE INDEX IF NOT EXISTS idx_ontology_terms_parent_term ON ontology_terms(parent_term);
CREATE INDEX IF NOT EXISTS idx_ontology_terms_term_trgm ON ontology_terms USING GIN (term gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_business_capabilities_business_id ON business_capabilities(business_id);
CREATE INDEX IF NOT EXISTS idx_business_capabilities_term ON business_capabilities(ontology_term);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname = 'idx_businesses_embedding_ivfflat'
  ) THEN
    CREATE INDEX idx_businesses_embedding_ivfflat
      ON businesses
      USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 100);
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname = 'idx_ontology_terms_embedding_ivfflat'
  ) THEN
    CREATE INDEX idx_ontology_terms_embedding_ivfflat
      ON ontology_terms
      USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 50);
  END IF;
END
$$;
