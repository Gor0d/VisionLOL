-- ═══════════════════════════════════════════════════════════════════
--  VisionLOL — Schema v3: Live Match Overlay
--  Execute no SQL Editor do Supabase após 002_riot_cache.sql
-- ═══════════════════════════════════════════════════════════════════

-- ── Estado ao vivo de cada jogador numa partida ───────────────────
CREATE TABLE IF NOT EXISTS live_match_state (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identificador da partida (gerado pelo agente no início do jogo)
    match_key    TEXT NOT NULL,

    -- Riot ID do jogador que enviou o dado ("GameName#TAG")
    player_id    TEXT NOT NULL,

    -- Dados extraídos do Live Client Data API
    game_time    FLOAT  NOT NULL DEFAULT 0,
    champion     TEXT   NOT NULL DEFAULT '',
    current_gold FLOAT  NOT NULL DEFAULT 0,
    kills        INT    NOT NULL DEFAULT 0,
    deaths       INT    NOT NULL DEFAULT 0,
    assists      INT    NOT NULL DEFAULT 0,
    cs           INT    NOT NULL DEFAULT 0,
    level        INT    NOT NULL DEFAULT 1,
    team         TEXT   NOT NULL DEFAULT 'ORDER',   -- ORDER | CHAOS

    -- Todos os jogadores (array de snapshots do allPlayers[])
    all_players  JSONB  NOT NULL DEFAULT '[]',

    -- Eventos acumulados da partida (dragon/baron/turret/kill etc.)
    events       JSONB  NOT NULL DEFAULT '[]',

    -- Sessão ativa?
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,

    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (match_key, player_id)
);

-- ── Índices ───────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_lms_match_key  ON live_match_state(match_key);
CREATE INDEX IF NOT EXISTS idx_lms_is_active  ON live_match_state(is_active);
CREATE INDEX IF NOT EXISTS idx_lms_updated    ON live_match_state(updated_at DESC);

-- ── RLS: leitura pública, escrita apenas service_role ─────────────
ALTER TABLE live_match_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read_live" ON live_match_state
    FOR SELECT TO anon USING (true);

-- ── Realtime ─────────────────────────────────────────────────────
-- Habilita Postgres Changes para broadcast em tempo real
ALTER PUBLICATION supabase_realtime ADD TABLE live_match_state;
