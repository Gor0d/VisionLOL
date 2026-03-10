import { NextRequest, NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase";

function authError() {
  return NextResponse.json({ error: "unauthorized" }, { status: 401 });
}

function validateAuth(req: NextRequest): boolean {
  const token = process.env.API_TOKEN;
  if (!token) return false; // Token não configurado — rejeita tudo
  const header = req.headers.get("Authorization") ?? "";
  return header === `Bearer ${token}`;
}

export async function POST(req: NextRequest) {
  if (!validateAuth(req)) return authError();

  let body: any;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const { session, players, champion_pool } = body;

  if (!session?.id) {
    return NextResponse.json({ error: "session.id required" }, { status: 400 });
  }

  try {
    const db = getServiceClient();

    // ── Upsert sessão ────────────────────────────────────────────────────────
    const { error: sessionErr } = await db
      .from("scrim_sessions")
      .upsert({
        id:          session.id,
        date:        session.date,
        opponent:    session.opponent,
        notes:       session.notes ?? "",
        wins:        session.wins ?? 0,
        losses:      session.losses ?? 0,
        metadata:    session.metadata ?? {},
        published_at: new Date().toISOString(),
      }, { onConflict: "id" });

    if (sessionErr) throw sessionErr;

    // ── Upsert jogadores ─────────────────────────────────────────────────────
    if (Array.isArray(players) && players.length > 0) {
      // Remove jogadores antigos e reinsere
      await db.from("session_players").delete().eq("session_id", session.id);

      const rows = players.map((p: any) => ({
        session_id:  session.id,
        game_name:   p.game_name,
        tag_line:    p.tag_line,
        role:        p.role,
        display:     p.display ?? p.game_name,
        games:       p.games ?? 0,
        wins:        p.wins ?? 0,
        kills:       p.kills ?? 0,
        deaths:      p.deaths ?? 0,
        assists:     p.assists ?? 0,
        cs:          p.cs ?? 0,
        vision:      p.vision ?? 0,
        top_champ:   p.top_champ ?? "",
        kda_ratio:   p.kda_ratio ?? 0,
        cs_per_min:  p.cs_per_min ?? 0,
        vision_pm:   p.vision_pm ?? 0,
        raw_metrics: p.raw_metrics ?? {},
        norm_metrics:p.norm_metrics ?? {},
      }));

      const { error: playersErr } = await db.from("session_players").insert(rows);
      if (playersErr) throw playersErr;
    }

    // ── Upsert champion pool ─────────────────────────────────────────────────
    if (Array.isArray(champion_pool) && champion_pool.length > 0) {
      const rows = champion_pool.map((e: any) => ({
        player_key: e.player_key,
        role:       e.role,
        champ:      e.champ,
        games:      e.games ?? 0,
        wins:       e.wins ?? 0,
        kda:        e.kda ?? 0,
        updated_at: new Date().toISOString(),
      }));

      const { error: poolErr } = await db
        .from("champion_pool_cache")
        .upsert(rows, { onConflict: "player_key,champ" });
      if (poolErr) throw poolErr;
    }

    return NextResponse.json({
      ok: true,
      session_id: session.id,
      players_upserted: players?.length ?? 0,
      pool_upserted: champion_pool?.length ?? 0,
    });

  } catch (err: any) {
    console.error("[publish]", err);
    return NextResponse.json(
      { error: err?.message ?? "internal error" },
      { status: 500 }
    );
  }
}
