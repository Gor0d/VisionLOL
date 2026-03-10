import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

/**
 * GET /api/live/active
 * Retorna as match_keys ativas (atualizadas nos últimos 30s)
 */
export async function GET() {
  const cutoff = new Date(Date.now() - 30_000).toISOString();

  const { data } = await supabase
    .from("live_match_state")
    .select("match_key, player_id, game_time, updated_at")
    .eq("is_active", true)
    .gte("updated_at", cutoff)
    .order("updated_at", { ascending: false });

  // Agrupa por match_key
  const matches: Record<string, { players: string[]; game_time: number; updated_at: string }> = {};
  for (const row of data ?? []) {
    if (!matches[row.match_key]) {
      matches[row.match_key] = { players: [], game_time: row.game_time, updated_at: row.updated_at };
    }
    matches[row.match_key].players.push(row.player_id);
    if (row.game_time > matches[row.match_key].game_time) {
      matches[row.match_key].game_time = row.game_time;
    }
  }

  return NextResponse.json({
    active: Object.entries(matches).map(([key, v]) => ({
      match_key: key,
      ...v,
    })),
  });
}
