import { NextRequest, NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase";

function authOk(req: NextRequest) {
  const token = process.env.API_TOKEN ?? process.env.RIOT_SYNC_TOKEN;
  if (!token) return false;
  return req.headers.get("Authorization") === `Bearer ${token}`;
}

/**
 * POST /api/live/update
 *
 * Recebido do Flask relay (scrim_server /live_update) em tempo real
 * durante uma partida ativa.
 *
 * Body esperado:
 * {
 *   match_key:    "LIVE_1710000000",
 *   player_id:    "xyno#kiwi",
 *   game_time:    845.5,
 *   champion:     "Renekton",
 *   current_gold: 1234.0,
 *   kills:        3,
 *   deaths:       0,
 *   assists:      5,
 *   cs:           187,
 *   level:        13,
 *   team:         "ORDER",
 *   all_players:  [...],
 *   events:       [...],
 *   is_active:    true
 * }
 */
export async function POST(req: NextRequest) {
  if (!authOk(req)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  let body: any;
  try { body = await req.json(); } catch { return NextResponse.json({ error: "invalid json" }, { status: 400 }); }

  const {
    match_key, player_id, game_time,
    champion = "", current_gold = 0,
    kills = 0, deaths = 0, assists = 0,
    cs = 0, level = 1, team = "ORDER",
    all_players = [], events = [],
    is_active = true,
  } = body;

  if (!match_key || !player_id) {
    return NextResponse.json({ error: "match_key e player_id obrigatórios" }, { status: 400 });
  }

  const db = getServiceClient();

  const { error } = await db.from("live_match_state").upsert({
    match_key,
    player_id,
    game_time,
    champion,
    current_gold,
    kills,
    deaths,
    assists,
    cs,
    level,
    team,
    all_players,
    events,
    is_active,
    updated_at: new Date().toISOString(),
  }, { onConflict: "match_key,player_id" });

  if (error) {
    console.error("[live/update]", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true, match_key, player_id });
}

/**
 * DELETE /api/live/update?match_key=LIVE_xxx
 * Marca todos os jogadores de um match como inativos (jogo encerrado)
 */
export async function DELETE(req: NextRequest) {
  if (!authOk(req)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const matchKey = req.nextUrl.searchParams.get("match_key");
  if (!matchKey) return NextResponse.json({ error: "match_key obrigatório" }, { status: 400 });

  const db = getServiceClient();
  await db.from("live_match_state")
    .update({ is_active: false, updated_at: new Date().toISOString() })
    .eq("match_key", matchKey);

  return NextResponse.json({ ok: true });
}
