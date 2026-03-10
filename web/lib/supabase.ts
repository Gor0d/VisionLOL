import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

/** Cliente público (anon) — leitura pública via RLS */
export const supabase = createClient(url, anonKey);

/** Cliente service_role — apenas server-side (API routes) */
export function getServiceClient() {
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!serviceKey) throw new Error("SUPABASE_SERVICE_ROLE_KEY não configurado");
  return createClient(url, serviceKey);
}

// ── Tipos ──────────────────────────────────────────────────────────────────

export interface ScrimSession {
  id: string;
  date: string;
  opponent: string;
  notes: string;
  wins: number;
  losses: number;
  published_at: string;
  metadata: Record<string, unknown>;
  player_count?: number;
  avg_kda?: number;
}

export interface SessionPlayer {
  id: string;
  session_id: string;
  game_name: string;
  tag_line: string;
  role: string;
  display: string;
  games: number;
  wins: number;
  kills: number;
  deaths: number;
  assists: number;
  cs: number;
  vision: number;
  top_champ: string;
  kda_ratio: number;
  cs_per_min: number;
  vision_pm: number;
  raw_metrics: Record<string, unknown>;
  norm_metrics: Record<string, unknown>;
}

export interface ChampionPoolEntry {
  id: string;
  player_key: string;
  role: string;
  champ: string;
  games: number;
  wins: number;
  kda: number;
  updated_at: string;
}
