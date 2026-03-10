-- ═══════════════════════════════════════════════════════════════════
--  VisionLOL — Schema Supabase
--  Execute no SQL Editor do Supabase (Settings → SQL Editor)
-- ═══════════════════════════════════════════════════════════════════

-- ── Extensões ────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Tabela: scrim_sessions ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scrim_sessions (
    id          TEXT PRIMARY KEY,          -- ex: "scrim_20260309_143200"
    date        DATE NOT NULL,
    opponent    TEXT NOT NULL,
    notes       TEXT DEFAULT '',
    wins        INT  DEFAULT 0,
    losses      INT  DEFAULT 0,
    published_at TIMESTAMPTZ DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}'
);

-- ── Tabela: session_players ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS session_players (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  TEXT REFERENCES scrim_sessions(id) ON DELETE CASCADE,
    game_name   TEXT NOT NULL,
    tag_line    TEXT NOT NULL,
    role        TEXT NOT NULL,          -- TOP/JUNGLE/MID/ADC/SUPPORT
    display     TEXT DEFAULT '',

    -- Stats agregados da sessão
    games       INT  DEFAULT 0,
    wins        INT  DEFAULT 0,
    kills       INT  DEFAULT 0,
    deaths      INT  DEFAULT 0,
    assists     INT  DEFAULT 0,
    cs          INT  DEFAULT 0,
    vision      INT  DEFAULT 0,
    top_champ   TEXT DEFAULT '',        -- campeão mais jogado

    -- Métricas calculadas
    kda_ratio   FLOAT DEFAULT 0,
    cs_per_min  FLOAT DEFAULT 0,
    vision_pm   FLOAT DEFAULT 0,

    raw_metrics JSONB DEFAULT '{}',     -- {kda, cs_per_min, vision_pm, ...}
    norm_metrics JSONB DEFAULT '{}'     -- normalizado 0-1
);

-- ── Tabela: champion_pool_cache ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS champion_pool_cache (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_key  TEXT NOT NULL,          -- "GameName#TAG"
    role        TEXT NOT NULL,
    champ       TEXT NOT NULL,
    games       INT  DEFAULT 0,
    wins        INT  DEFAULT 0,
    kda         FLOAT DEFAULT 0,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (player_key, champ)
);

-- ── RLS: Habilitar ───────────────────────────────────────────────────
ALTER TABLE scrim_sessions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_players   ENABLE ROW LEVEL SECURITY;
ALTER TABLE champion_pool_cache ENABLE ROW LEVEL SECURITY;

-- ── RLS: Leitura pública (dashboard web sem login) ────────────────────
CREATE POLICY "public_read_sessions"
    ON scrim_sessions FOR SELECT TO anon USING (true);

CREATE POLICY "public_read_players"
    ON session_players FOR SELECT TO anon USING (true);

CREATE POLICY "public_read_pool"
    ON champion_pool_cache FOR SELECT TO anon USING (true);

-- ── RLS: Escrita via service_role (API routes do Next.js) ─────────────
-- A service_role key bypasssa RLS automaticamente — sem política necessária.
-- Writes vindos do VisionLOL passam pelo Next.js API route (server-side),
-- que usa a service_role key. NUNCA exposta no frontend.

-- ── Índices para performance ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sessions_date     ON scrim_sessions(date DESC);
CREATE INDEX IF NOT EXISTS idx_players_session   ON session_players(session_id);
CREATE INDEX IF NOT EXISTS idx_pool_player       ON champion_pool_cache(player_key);

-- ── View: resumo de sessão ────────────────────────────────────────────
CREATE OR REPLACE VIEW v_session_summary AS
SELECT
    s.id,
    s.date,
    s.opponent,
    s.notes,
    s.wins,
    s.losses,
    s.published_at,
    COUNT(p.id)::int       AS player_count,
    ROUND(AVG(p.kda_ratio)::numeric, 2) AS avg_kda
FROM scrim_sessions s
LEFT JOIN session_players p ON p.session_id = s.id
GROUP BY s.id, s.date, s.opponent, s.notes, s.wins, s.losses, s.published_at
ORDER BY s.date DESC;

-- Dar SELECT na view para anon
GRANT SELECT ON v_session_summary TO anon;
