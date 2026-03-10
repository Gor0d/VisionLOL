-- ═══════════════════════════════════════════════════════════════════
--  VisionLOL — Schema v2: Riot API cache + player stats
--  Execute no SQL Editor do Supabase após 001_schema.sql
-- ═══════════════════════════════════════════════════════════════════

-- ── PUUID lookup ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS riot_accounts (
    player_key  TEXT PRIMARY KEY,          -- "GameName#TAG"
    puuid       TEXT NOT NULL UNIQUE,
    game_name   TEXT NOT NULL,
    tag_line    TEXT NOT NULL,
    team        TEXT NOT NULL DEFAULT '',  -- LOUD, Gen.G, etc.
    role        TEXT NOT NULL DEFAULT '',  -- TOP/JUNGLE/MIDDLE/BOTTOM/SUPPORT
    region      TEXT NOT NULL DEFAULT 'br1',
    routing     TEXT NOT NULL DEFAULT 'americas',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Participações em partidas (de-normalizado) ────────────────────────
CREATE TABLE IF NOT EXISTS match_participants (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id       TEXT NOT NULL,
    puuid          TEXT NOT NULL,
    player_key     TEXT NOT NULL DEFAULT '',
    team_tag       TEXT NOT NULL DEFAULT '',    -- LOUD, oponente, etc.
    champion       TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT '',
    kills          INT  DEFAULT 0,
    deaths         INT  DEFAULT 0,
    assists        INT  DEFAULT 0,
    cs             INT  DEFAULT 0,
    vision_score   INT  DEFAULT 0,
    gold_earned    INT  DEFAULT 0,
    damage_dealt   INT  DEFAULT 0,
    win            BOOLEAN DEFAULT FALSE,
    game_duration  INT  DEFAULT 0,             -- segundos
    game_date      DATE,
    patch          TEXT DEFAULT '',
    queue_id       INT  DEFAULT 0,
    UNIQUE (match_id, puuid)
);

-- ── Estatísticas agregadas por período ────────────────────────────────
CREATE TABLE IF NOT EXISTS player_stats_cache (
    player_key     TEXT NOT NULL,
    period         TEXT NOT NULL,    -- 'all', '14d', '30d'
    games          INT   DEFAULT 0,
    wins           INT   DEFAULT 0,
    kills          FLOAT DEFAULT 0,
    deaths         FLOAT DEFAULT 0,
    assists        FLOAT DEFAULT 0,
    kda            FLOAT DEFAULT 0,
    cs_per_min     FLOAT DEFAULT 0,
    vision_per_min FLOAT DEFAULT 0,
    top_champ      TEXT  DEFAULT '',
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_key, period)
);

-- ── Índices ───────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_mp_puuid   ON match_participants(puuid);
CREATE INDEX IF NOT EXISTS idx_mp_team    ON match_participants(team_tag);
CREATE INDEX IF NOT EXISTS idx_mp_date    ON match_participants(game_date DESC);
CREATE INDEX IF NOT EXISTS idx_mp_champ   ON match_participants(champion);
CREATE INDEX IF NOT EXISTS idx_mp_player  ON match_participants(player_key);

-- ── RLS ───────────────────────────────────────────────────────────────
ALTER TABLE riot_accounts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_participants    ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_stats_cache    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read_accounts" ON riot_accounts
    FOR SELECT TO anon USING (true);

CREATE POLICY "public_read_matches" ON match_participants
    FOR SELECT TO anon USING (true);

CREATE POLICY "public_read_stats" ON player_stats_cache
    FOR SELECT TO anon USING (true);

-- ── View: champion pool por jogador ───────────────────────────────────
CREATE OR REPLACE VIEW v_champion_pool AS
SELECT
    player_key,
    champion,
    COUNT(*)::int                                      AS games,
    SUM(CASE WHEN win THEN 1 ELSE 0 END)::int          AS wins,
    ROUND(AVG((kills + assists)::numeric / GREATEST(deaths,1)), 2) AS kda,
    ROUND(AVG(cs::numeric / GREATEST(game_duration/60.0,1)), 2)    AS cs_per_min,
    MAX(game_date)                                     AS last_played
FROM match_participants
WHERE player_key != ''
GROUP BY player_key, champion
ORDER BY player_key, games DESC;

GRANT SELECT ON v_champion_pool TO anon;
