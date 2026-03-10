import { supabase } from "@/lib/supabase";
import { TEAMS } from "@/lib/teams";
import ChampionIcon from "@/components/ChampionIcon";
import Sparkline from "@/components/Sparkline";

export const revalidate = 300;

const LOUD_KEYS = TEAMS.find(t => t.name === "LOUD")!.players.map(p => p.key);

async function getInsightsData() {
  const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);

  const [{ data: recent30 }, { data: allStats }, { data: champPool }] = await Promise.all([
    // Partidas dos últimos 30 dias
    supabase.from("match_participants")
      .select("*")
      .in("player_key", LOUD_KEYS)
      .gte("game_date", thirtyDaysAgo)
      .order("game_date", { ascending: false })
      .limit(200),

    // Stats de cada jogador
    supabase.from("player_stats_cache")
      .select("*")
      .in("player_key", LOUD_KEYS)
      .eq("period", "30d"),

    // Champion pool geral
    supabase.from("v_champion_pool")
      .select("*")
      .in("player_key", LOUD_KEYS)
      .order("games", { ascending: false }),
  ]);

  return {
    recent: recent30 ?? [],
    stats: allStats ?? [],
    pool: champPool ?? [],
  };
}

function ContentCard({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="nerv-card" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: "#FF9830" }}>{title}</span>
        {sub && <span style={{ fontSize: 10, color: "#404040" }}>{sub}</span>}
      </div>
      {children}
    </div>
  );
}

export default async function InsightsPage() {
  const { recent, stats, pool } = await getInsightsData();
  const hasData = recent.length > 0;

  // ── Processar dados ─────────────────────────────────────────────────

  // Top performances individuais (KDA > 5)
  const topPerfs = recent
    .map((r: any) => ({ ...r, kda: (r.kills + r.assists) / Math.max(r.deaths, 1) }))
    .sort((a: any, b: any) => b.kda - a.kda)
    .slice(0, 8);

  // Jogadores em sequência de vitórias (últimas 5 partidas)
  const streaks: { key: string; display: string; streak: number; type: "WIN" | "LOSS" }[] = [];
  for (const key of LOUD_KEYS) {
    const playerGames = recent.filter((r: any) => r.player_key === key).slice(0, 5);
    if (playerGames.length < 3) continue;
    const last = playerGames[0];
    let streak = 0;
    for (const g of playerGames) {
      if (g.win === last.win) streak++;
      else break;
    }
    if (streak >= 3) {
      const p = TEAMS.find(t => t.name === "LOUD")!.players.find(p => p.key === key);
      streaks.push({ key, display: p?.display ?? key.split("#")[0], streak, type: last.win ? "WIN" : "LOSS" });
    }
  }
  streaks.sort((a, b) => b.streak - a.streak);

  // KDA médio por patch (últimas semanas)
  const patchGroups: Record<string, number[]> = {};
  for (const r of recent) {
    if (!r.patch) continue;
    if (!patchGroups[r.patch]) patchGroups[r.patch] = [];
    patchGroups[r.patch].push((r.kills + r.assists) / Math.max(r.deaths, 1));
  }
  const patchTrend = Object.entries(patchGroups)
    .map(([patch, kdas]) => ({ patch, avg: kdas.reduce((a, b) => a + b, 0) / kdas.length }))
    .sort((a, b) => a.patch.localeCompare(b.patch));

  // Campeões mais usados no time
  const teamChampCounts: Record<string, { games: number; wins: number }> = {};
  for (const r of recent) {
    if (!teamChampCounts[r.champion]) teamChampCounts[r.champion] = { games: 0, wins: 0 };
    teamChampCounts[r.champion].games++;
    if (r.win) teamChampCounts[r.champion].wins++;
  }
  const teamChamps = Object.entries(teamChampCounts)
    .map(([champ, { games, wins }]) => ({ champ, games, wins, wr: Math.round((wins / games) * 100) }))
    .sort((a, b) => b.games - a.games)
    .slice(0, 10);

  // Campeão "problema" (≥3 jogos, WR < 45%)
  const problemChamps = Object.entries(teamChampCounts)
    .map(([champ, { games, wins }]) => ({ champ, games, wins, wr: Math.round((wins / games) * 100) }))
    .filter(c => c.games >= 3 && c.wr < 45)
    .sort((a, b) => a.wr - b.wr);

  return (
    <div>
      {/* ── Header ── */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 6 }}>// MÓDULO 04</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#50FF50" }}>INSIGHTS</h1>
        <p style={{ color: "#505050", fontSize: 12, marginTop: 4 }}>
          Análise de conteúdo — últimos 30 dias · {recent.length} partidas
        </p>
      </div>

      {!hasData ? (
        <div className="nerv-card" style={{ textAlign: "center", padding: 48, color: "#404040" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
          <p style={{ color: "#606060" }}>Sem dados suficientes para gerar insights</p>
          <p style={{ fontSize: 12, marginTop: 8 }}>Sincronize os jogadores via <code style={{ color: "#20F0FF" }}>/api/riot/sync</code></p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          {/* ── Sequências ── */}
          <div>
            <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 10 }}>// SEQUÊNCIAS ATIVAS</div>
            {streaks.length > 0 ? streaks.map(s => (
              <ContentCard key={s.key} title={s.display} sub={`${s.streak}x seguidas`}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 20 }}>{s.type === "WIN" ? "🔥" : "❄️"}</span>
                  <span style={{ fontSize: 13, color: s.type === "WIN" ? "#50FF50" : "#FF4040", fontWeight: 700 }}>
                    {s.streak} {s.type === "WIN" ? "VITÓRIAS" : "DERROTAS"} CONSECUTIVAS
                  </span>
                </div>
              </ContentCard>
            )) : (
              <div className="nerv-card" style={{ color: "#404040", fontSize: 12, padding: "20px" }}>
                Sem sequências de 3+ nos últimos jogos
              </div>
            )}

            {/* ── Campeões problema ── */}
            {problemChamps.length > 0 && (
              <>
                <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", margin: "20px 0 10px" }}>// PONTOS FRACOS</div>
                {problemChamps.map(c => (
                  <ContentCard key={c.champ} title={c.champ} sub={`${c.games} jogos`}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <ChampionIcon name={c.champ} size={32} />
                      <div>
                        <div style={{ fontSize: 12, color: "#FF4040", fontWeight: 700 }}>{c.wr}% WR</div>
                        <div style={{ fontSize: 10, color: "#404040" }}>{c.wins}V / {c.games - c.wins}D</div>
                      </div>
                      <div style={{ marginLeft: "auto", fontSize: 10, color: "#404040", maxWidth: 100, textAlign: "right" }}>
                        candidato a banir/estudar
                      </div>
                    </div>
                  </ContentCard>
                ))}
              </>
            )}
          </div>

          {/* ── Coluna direita ── */}
          <div>
            {/* Top Performances */}
            <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 10 }}>// TOP PERFORMANCES</div>
            {topPerfs.slice(0, 5).map((r: any) => {
              const p = TEAMS.find(t => t.name === "LOUD")!.players.find(p => p.key === r.player_key);
              return (
                <ContentCard key={`${r.match_id}-${r.puuid}`} title={p?.display ?? r.player_key.split("#")[0]} sub={r.game_date}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ChampionIcon name={r.champion} size={32} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, color: "#50FF50", fontWeight: 700 }}>{r.kda.toFixed(1)} KDA</div>
                      <div style={{ fontSize: 11, color: "#505050" }}>
                        {r.kills}/{r.deaths}/{r.assists} · {r.champion}
                      </div>
                    </div>
                    <span className={`badge ${r.win ? "badge-win" : "badge-loss"}`}>
                      {r.win ? "W" : "L"}
                    </span>
                  </div>
                </ContentCard>
              );
            })}

            {/* ── Champion meta ── */}
            <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", margin: "20px 0 10px" }}>// CAMPEÕES DO TIME</div>
            <div className="nerv-card">
              {teamChamps.map((c, i) => (
                <div key={c.champ} style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "6px 0",
                  borderBottom: i < teamChamps.length - 1 ? "1px solid #111" : "none",
                }}>
                  <span style={{ fontSize: 10, color: "#303030", width: 16, textAlign: "right" }}>{i + 1}</span>
                  <ChampionIcon name={c.champ} size={24} />
                  <span style={{ flex: 1, fontSize: 12, color: "#e0e0e0" }}>{c.champ}</span>
                  <span style={{ fontSize: 11, color: "#606060" }}>{c.games}g</span>
                  <span style={{ fontSize: 11, color: c.wr >= 50 ? "#50FF50" : "#FF4040", minWidth: 36, textAlign: "right" }}>
                    {c.wr}%
                  </span>
                </div>
              ))}
            </div>

            {/* ── Trend de KDA por patch ── */}
            {patchTrend.length >= 2 && (
              <>
                <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", margin: "20px 0 10px" }}>// KDA MÉDIO POR PATCH</div>
                <div className="nerv-card" style={{ display: "flex", alignItems: "flex-end", gap: 16 }}>
                  <Sparkline values={patchTrend.map(p => p.avg)} width={140} height={40} fill color="#20F0FF" />
                  <div style={{ fontSize: 11 }}>
                    {patchTrend.map(p => (
                      <div key={p.patch} style={{ display: "flex", gap: 8 }}>
                        <span style={{ color: "#404040", width: 36 }}>{p.patch}</span>
                        <span style={{ color: "#20F0FF" }}>{p.avg.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
