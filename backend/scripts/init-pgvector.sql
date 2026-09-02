CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- HNSW Vector Index for all-MiniLM-L6-v2 384-dimensional embeddings (cosine distance)
-- Note: Executed after tables are created or during bootstrap
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'material_embeddings') THEN
        CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw ON material_embeddings USING hnsw (embedding vector_cosine_ops);
    END IF;
END $$;
