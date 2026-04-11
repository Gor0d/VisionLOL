import { NextRequest, NextResponse } from "next/server";
import { getServiceClient } from "@/lib/supabase";
import {
  getPuuid, getMatchIds, getMatch,
  normalizeRole, patchFromVersion, gameDateFromTimestamp,
  type RiotParticipant,
} from "@/lib/riot";

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

function authOk(req: NextRequest) {
  const token = process.env.API_TOKEN ?? process.env.RIOT_SYNC_TOKEN;
  if (!token) return false;
  return req.headers.get("Authorization") === `Bearer ${token}`;
}

// ── Agrega stats de um conjunto de participações ──────────────────────
function aggregateStats(rows: any[]) {
  if (!rows.length) return null;
  const games = rows.length;
  const wins  = rows.filter(r => r.win).length;
  const kills   = rows.reduce((s, r) => s + r.kills,   0) / games;
  const deaths  = rows.reduce((s, r) => s + r.deaths,  0) / games;
  const assists = rows.reduce((s, r) => s + r.assists,  0) / games;
  const kda     = (kills + assists) / Math.max(deaths, 1);
  const cs_per_min   = rows.reduce((s, r) => s + r.cs / Math.max(r.game_duration / 60, 1), 0) / games;
  const vision_per_min = rows.reduce((s, r) => s + r.vision_score / Math.max(r.game_duration / 60, 1), 0) / games;

  // Campeão mais jogado
  const champCounts: Record<string, number> = {};
  for (const r of rows) champCounts[r.champion] = (champCounts[r.champion] ?? 0) + 1;
  const top_champ = Object.entries(champCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";

  return { games, wins, kills: +kills.toFixed(2), deaths: +deaths.toFixed(2), assists: +assists.toFixed(2),
           kda: +kda.toFixed(2), cs_per_min: +cs_per_min.toFixed(2), vision_per_min: +vision_per_min.toFixed(2), top_champ };
}

export async function POST(req: NextRequest) {
  if (!authOk(req)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  let body: any;
  try { body = await req.json(); } catch { return NextResponse.json({ error: "invalid json" }, { status: 400 }); }

  const {
    playerKey, gameName, tagLine,
    region = "br1", routing = "americas", team = "", count = 20,
    alts = [],   // [{ gameName, tagLine }] — contas alternativas em caso de 404
  } = body;

  if (!gameName || !tagLine) {
    return NextResponse.json({ error: "gameName e tagLine são obrigatórios" }, { status: 400 });
  }

  const db  = getServiceClient();
  const key = playerKey ?? `${gameName}#${tagLine}`;

  try {
    // ── 1. Resolver PUUID (com fallback para contas alternativas) ─────
    let puuid: string = "";
    let resolvedName = gameName;
    let resolvedTag  = tagLine;

    const { data: cached } = await db.from("riot_accounts").select("puuid").eq("player_key", key).single();

    if (cached?.puuid) {
      puuid = cached.puuid;
    } else {
      // Tenta conta principal, depois as alternativas
      const candidates = [{ gameName, tagLine }, ...alts];
      let lastError: Error | null = null;
      let resolved = false;

      for (const c of candidates) {
        try {
          puuid = await getPuuid(c.gameName, c.tagLine, routing);
          resolvedName = c.gameName;
          resolvedTag  = c.tagLine;
          resolved = true;
          break;
        } catch (e: any) {
          lastError = e;
          console.warn(`[sync] 404 para ${c.gameName}#${c.tagLine}, tentando próxima conta...`);
          await sleep(200);
        }
      }

      if (!resolved) throw lastError ?? new Error("Nenhuma conta encontrada");

      await db.from("riot_accounts").upsert({
        player_key: key, puuid: puuid!, game_name: resolvedName, tag_line: resolvedTag,
        team, region, routing, updated_at: new Date().toISOString(),
      }, { onConflict: "player_key" });
    }

    // ── 2. Buscar match IDs recentes ──────────────────────────────────
    const matchIds = await getMatchIds(puuid, routing, count);
    await sleep(55); // rate limit guard

    // ── 3. Filtrar já existentes ──────────────────────────────────────
    const { data: existing } = await db
      .from("match_participants")
      .select("match_id")
      .eq("puuid", puuid)
      .in("match_id", matchIds);

    const existingSet = new Set((existing ?? []).map((r: any) => r.match_id));
    const toFetch = matchIds.filter(id => !existingSet.has(id));

    // ── 4. Ingerir novas partidas ─────────────────────────────────────
    let ingested = 0;
    for (const matchId of toFetch) {
      try {
        await sleep(55);
        const match = await getMatch(matchId, routing);
        const info  = match.info;
        const patch = patchFromVersion(info.gameVersion);
        const gameDate = gameDateFromTimestamp(info.gameStartTimestamp);

        const rows = info.participants.map((p: RiotParticipant) => ({
          match_id:       matchId,
          puuid:          p.puuid,
          player_key:     p.puuid === puuid ? key : "",
          team_tag:       p.puuid === puuid ? team : "",
          champion:       p.championName,
          role:           normalizeRole(p.teamPosition),
          kills:          p.kills,
          deaths:         p.deaths,
          assists:        p.assists,
          cs:             p.totalMinionsKilled + p.neutralMinionsKilled,
          vision_score:   p.visionScore,
          gold_earned:    p.goldEarned,
          damage_dealt:   p.totalDamageDealtToChampions,
          win:            p.win,
          game_duration:  info.gameDuration,
          game_date:      gameDate,
          patch,
          queue_id:       info.queueId,
        }));

        await db.from("match_participants").upsert(rows, { onConflict: "match_id,puuid", ignoreDuplicates: true });
        ingested++;
      } catch (e: any) {
        console.warn(`[sync] Erro em ${matchId}:`, e?.message);
      }
    }

    // ── 5. Recomputar stats cache ─────────────────────────────────────
    const { data: allRows } = await db
      .from("match_participants")
      .select("*")
      .eq("puuid", puuid)
      .order("game_date", { ascending: false });

    const rows = allRows ?? [];
    const now  = new Date();

    const periods: [string, number | null][] = [
      ["all", null],
      ["30d", 30],
      ["14d", 14],
    ];

    for (const [period, days] of periods) {
      const filtered = days
        ? rows.filter(r => {
            const diff = (now.getTime() - new Date(r.game_date).getTime()) / 86400000;
            return diff <= days;
          })
        : rows;

      const stats = aggregateStats(filtered);
      if (!stats) continue;

      await db.from("player_stats_cache").upsert({
        player_key: key, period, ...stats,
        updated_at: new Date().toISOString(),
      }, { onConflict: "player_key,period" });
    }

    return NextResponse.json({
      ok: true, player_key: key, puuid,
      total_matches: matchIds.length,
      already_cached: existingSet.size,
      ingested,
    });

  } catch (err: any) {
    console.error("[sync]", err);
    return NextResponse.json({ error: err?.message ?? "internal error" }, { status: 500 });
  }
}

// Sync de todo o roster de uma vez
export async function PUT(req: NextRequest) {
  if (!authOk(req)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  let body: any;
  try { body = await req.json(); } catch { return NextResponse.json({ error: "invalid json" }, { status: 400 }); }

  const { players } = body; // [{ gameName, tagLine, region, routing, team }]
  if (!Array.isArray(players)) return NextResponse.json({ error: "players[] required" }, { status: 400 });

  const results = [];
  for (const p of players) {
    await sleep(500); // entre jogadores
    const mockReq = new Request(req.url, {
      method: "POST",
      headers: req.headers,
      body: JSON.stringify(p),
    });
    const res = await POST(new NextRequest(mockReq));
    results.push(await res.json());
  }

  return NextResponse.json({ ok: true, results });
}
