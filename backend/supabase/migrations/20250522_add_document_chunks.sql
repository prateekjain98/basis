-- Migration: Add document_chunks table for stateless vector store fallback
-- Run this in Supabase SQL Editor before deploying to Cloud Run

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, chunk_index)
);

-- Index for fast session lookups
CREATE INDEX IF NOT EXISTS idx_document_chunks_session ON document_chunks(session_id);
