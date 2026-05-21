-- Run this in the Supabase SQL Editor

-- Sessions table: one row per thesis/chat
CREATE TABLE IF NOT EXISTS thesis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query TEXT NOT NULL,
    theme TEXT,
    summary TEXT,
    conviction TEXT CHECK (conviction IN ('High', 'Medium', 'Low')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Stock recommendations: one-to-many with sessions
CREATE TABLE IF NOT EXISTS stock_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thesis_id UUID REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    name TEXT,
    entry_price NUMERIC(12,2),
    target_price NUMERIC(12,2),
    stop_loss NUMERIC(12,2),
    position_size TEXT,
    fundamentals_score NUMERIC(5,2),
    thematic_fit_score NUMERIC(5,2),
    risk_score NUMERIC(5,2),
    momentum_score NUMERIC(5,2),
    liquidity_score NUMERIC(5,2),
    total_score NUMERIC(5,2),
    rationale TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Documents fetched and parsed per session
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thesis_id UUID REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    source TEXT,
    parsed_content TEXT,
    chunk_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Messages for chat history / follow-ups
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES thesis_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_created ON thesis_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stocks_thesis ON stock_recommendations(thesis_id);
CREATE INDEX IF NOT EXISTS idx_docs_thesis ON documents(thesis_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at DESC);

-- Enable RLS (optional, but good practice)
ALTER TABLE thesis_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Allow anon access for demo (lock down in production)
CREATE POLICY "Allow all" ON thesis_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON stock_recommendations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON messages FOR ALL USING (true) WITH CHECK (true);
