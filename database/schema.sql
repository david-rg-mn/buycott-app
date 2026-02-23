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
  google_place_id TEXT UNIQUE,
  formatted_address TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  phone TEXT,
  website TEXT,
  hours JSONB,
  hours_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  primary_type TEXT,
  types JSONB,
  business_model JSONB NOT NULL DEFAULT '{}'::jsonb,
  google_last_fetched_at TIMESTAMP,
  google_source TEXT NOT NULL DEFAULT 'places_api',
  timezone TEXT NOT NULL DEFAULT 'America/Chicago',
  specialty_score REAL NOT NULL DEFAULT 0,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS google_place_id TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS formatted_address TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS hours JSONB;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS primary_type TEXT;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS types JSONB;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS business_model JSONB DEFAULT '{}'::jsonb;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS google_last_fetched_at TIMESTAMP;
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS google_source TEXT DEFAULT 'places_api';
ALTER TABLE businesses ADD COLUMN IF NOT EXISTS canonical_summary_text TEXT;
UPDATE businesses SET business_model = '{}'::jsonb WHERE business_model IS NULL;
ALTER TABLE businesses ALTER COLUMN business_model SET DEFAULT '{}'::jsonb;
ALTER TABLE businesses ALTER COLUMN business_model SET NOT NULL;
ALTER TABLE businesses ALTER COLUMN google_source SET DEFAULT 'places_api';
UPDATE businesses SET google_source = 'places_api' WHERE google_source IS NULL;
ALTER TABLE businesses ALTER COLUMN google_source SET NOT NULL;

CREATE TABLE IF NOT EXISTS business_sources (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_url TEXT,
  snippet TEXT,
  last_fetched TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, source_type, source_url)
);

CREATE TABLE IF NOT EXISTS ontology_nodes (
  id BIGSERIAL PRIMARY KEY,
  canonical_term TEXT NOT NULL UNIQUE,
  parent_id BIGINT REFERENCES ontology_nodes(id) ON DELETE SET NULL,
  synonyms JSONB NOT NULL DEFAULT '[]'::jsonb,
  source TEXT NOT NULL DEFAULT 'seed',
  embedding VECTOR(384),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_documents (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  source_url TEXT NOT NULL,
  modality TEXT NOT NULL,
  etag TEXT,
  content_hash TEXT NOT NULL,
  http_status INTEGER,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, source_url, content_hash)
);

CREATE TABLE IF NOT EXISTS evidence_packets (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  modality TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_snippet TEXT NOT NULL,
  claim_text TEXT NOT NULL,
  sanitized_claim_text TEXT NOT NULL,
  claim_hash TEXT NOT NULL,
  extraction_confidence REAL NOT NULL CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
  credibility_score REAL NOT NULL CHECK (credibility_score >= 0 AND credibility_score <= 100),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  content_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, claim_hash, source_url)
);

CREATE TABLE IF NOT EXISTS menu_items (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_snippet TEXT NOT NULL,
  section TEXT,
  item_name TEXT NOT NULL,
  description TEXT,
  price NUMERIC(10, 2),
  currency TEXT NOT NULL DEFAULT 'USD',
  dietary_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  raw_text TEXT NOT NULL,
  claim_hash TEXT NOT NULL,
  extraction_confidence REAL NOT NULL CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
  credibility_score REAL NOT NULL CHECK (credibility_score >= 0 AND credibility_score <= 100),
  embedding VECTOR(384),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, claim_hash)
);

CREATE TABLE IF NOT EXISTS capabilities (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  capability_type TEXT NOT NULL CHECK (
    capability_type IN ('sells', 'services', 'attributes', 'operations', 'suitability')
  ),
  canonical_items JSONB NOT NULL DEFAULT '[]'::jsonb,
  source_claim_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
  evidence_score REAL NOT NULL CHECK (evidence_score >= 0 AND evidence_score <= 100),
  canonical_text TEXT NOT NULL,
  embedding VECTOR(384),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, capability_type, canonical_text)
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

CREATE TABLE IF NOT EXISTS global_footprints (
  business_id BIGINT PRIMARY KEY REFERENCES businesses(id) ON DELETE CASCADE,
  feature_vector VECTOR(384) NOT NULL,
  feature_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
  coverage_score REAL NOT NULL DEFAULT 0 CHECK (coverage_score >= 0 AND coverage_score <= 1),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vertical_slices (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  slice_key TEXT NOT NULL,
  category_weights JSONB NOT NULL DEFAULT '{}'::jsonb,
  slice_terms JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, slice_key)
);

CREATE TABLE IF NOT EXISTS evidence_index_terms (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  evidence_ref JSONB NOT NULL DEFAULT '{}'::jsonb,
  provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
  weight REAL NOT NULL DEFAULT 0 CHECK (weight >= 0 AND weight <= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (business_id, term, claim_id, source_kind)
);

CREATE TABLE IF NOT EXISTS business_micrographs (
  business_id BIGINT PRIMARY KEY REFERENCES businesses(id) ON DELETE CASCADE,
  graph_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verified_claims (
  id BIGSERIAL PRIMARY KEY,
  business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
  claim_id TEXT NOT NULL,
  label TEXT NOT NULL,
  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  audit_chain JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (business_id, claim_id)
);

CREATE TABLE IF NOT EXISTS telemetry_logs (
  request_id UUID PRIMARY KEY,
  query_text TEXT,
  embedding_time_ms DOUBLE PRECISION,
  expansion_time_ms DOUBLE PRECISION,
  db_time_ms DOUBLE PRECISION,
  ranking_time_ms DOUBLE PRECISION,
  total_time_ms DOUBLE PRECISION,
  result_count INTEGER,
  top_similarity_score DOUBLE PRECISION,
  timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS google_api_usage_log (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  requests_made INTEGER NOT NULL CHECK (requests_made >= 0),
  estimated_cost DOUBLE PRECISION NOT NULL CHECK (estimated_cost >= 0)
);

CREATE INDEX IF NOT EXISTS idx_businesses_lat_lng ON businesses(lat, lng);
CREATE INDEX IF NOT EXISTS idx_businesses_is_chain ON businesses(is_chain);
CREATE INDEX IF NOT EXISTS idx_businesses_primary_type ON businesses(primary_type);
CREATE INDEX IF NOT EXISTS idx_businesses_business_model_gin ON businesses USING GIN (business_model jsonb_path_ops);
CREATE UNIQUE INDEX IF NOT EXISTS idx_businesses_google_place_id_unique
  ON businesses(google_place_id)
  WHERE google_place_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_businesses_google_last_fetched_at ON businesses(google_last_fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_business_sources_business_id ON business_sources(business_id);
CREATE INDEX IF NOT EXISTS idx_source_documents_business_id ON source_documents(business_id);
CREATE INDEX IF NOT EXISTS idx_source_documents_source_url ON source_documents(source_url);
CREATE INDEX IF NOT EXISTS idx_evidence_packets_business_id ON evidence_packets(business_id);
CREATE INDEX IF NOT EXISTS idx_evidence_packets_claim_hash ON evidence_packets(claim_hash);
CREATE INDEX IF NOT EXISTS idx_menu_items_business_id ON menu_items(business_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_item_name_trgm ON menu_items USING GIN (item_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_capabilities_business_id ON capabilities(business_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_type ON capabilities(capability_type);
CREATE INDEX IF NOT EXISTS idx_ontology_nodes_parent_id ON ontology_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_ontology_nodes_term_trgm ON ontology_nodes USING GIN (canonical_term gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ontology_nodes_synonyms_gin ON ontology_nodes USING GIN (synonyms jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_ontology_terms_parent_term ON ontology_terms(parent_term);
CREATE INDEX IF NOT EXISTS idx_ontology_terms_term_trgm ON ontology_terms USING GIN (term gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_business_capabilities_business_id ON business_capabilities(business_id);
CREATE INDEX IF NOT EXISTS idx_business_capabilities_term ON business_capabilities(ontology_term);
CREATE INDEX IF NOT EXISTS idx_vertical_slices_business_id ON vertical_slices(business_id);
CREATE INDEX IF NOT EXISTS idx_vertical_slices_slice_key ON vertical_slices(slice_key);
CREATE INDEX IF NOT EXISTS idx_evidence_index_terms_business_id ON evidence_index_terms(business_id);
CREATE INDEX IF NOT EXISTS idx_evidence_index_terms_term ON evidence_index_terms(term);
CREATE INDEX IF NOT EXISTS idx_evidence_index_terms_claim_id ON evidence_index_terms(claim_id);
CREATE INDEX IF NOT EXISTS idx_verified_claims_business_id ON verified_claims(business_id);
CREATE INDEX IF NOT EXISTS idx_verified_claims_claim_id ON verified_claims(claim_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_logs_timestamp ON telemetry_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_google_api_usage_log_timestamp ON google_api_usage_log(timestamp DESC);

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
      AND indexname = 'idx_global_footprints_vector_ivfflat'
  ) THEN
    CREATE INDEX idx_global_footprints_vector_ivfflat
      ON global_footprints
      USING ivfflat (feature_vector vector_cosine_ops)
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

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'public'
      AND indexname = 'idx_menu_items_embedding_ivfflat'
  ) THEN
    CREATE INDEX idx_menu_items_embedding_ivfflat
      ON menu_items
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
      AND indexname = 'idx_capabilities_embedding_ivfflat'
  ) THEN
    CREATE INDEX idx_capabilities_embedding_ivfflat
      ON capabilities
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
      AND indexname = 'idx_ontology_nodes_embedding_ivfflat'
  ) THEN
    CREATE INDEX idx_ontology_nodes_embedding_ivfflat
      ON ontology_nodes
      USING ivfflat (embedding vector_cosine_ops)
      WITH (lists = 50);
  END IF;
END
$$;
