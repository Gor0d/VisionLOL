import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { TEAMS, ROLE_SHORT, ROLE_ORDER } from "@/lib/teams";
import { championIconUrl } from "@/lib/ddragon";

export const revalidate = 300;

async function getPlayerStats() {
  const { data } = await supabase
    .from("player_stats_cache")
    .select("*")
    .eq("period", "30d");
  return Object.fromEntries((data ?? []).map((r: any) => [r.player_key, r]));
}

async function getTopChamps() {
  const { data } = await supabase
    .from("v_champion_pool")
    .select("*")
    .order("games", { ascending: false });

  const byPlayer: Record<string, any[]> = {};
  for (const row of data ?? []) {
    if (!byPlayer[row.player_key]) byPlayer[row.player_key] = [];
    if (byPlayer[row.player_key].length < 3) byPlayer[row.player_key].push(row);
  }
  return byPlayer;
}

function KdaColor({ v }: { v: number }) {
  const color = v >= 4 ? "#50FF50" : v >= 2.5 ? "#FF9830" : "#FF4040";
  return <span style={{ color, fontWeight: 700 }}>{v.toFixed(2)}</span>;
}

function MiniStat({ label, value, color = "#e0e0e0" }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 10, color: "#404040", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, color, fontWeight: 600 }}>{value}</div>
    </div>
  );
}

export default async function PlayersPage() {
  const [stats, topChamps] = await Promise.all([getPlayerStats(), getTopChamps()]);

  return (
    <div>
      {/* ── Header ── */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 6 }}>// MÓDULO 03</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#FF9830" }}>PLAYERS</h1>
        <p style={{ color: "#505050", fontSize: 12, marginTop: 4 }}>Roster e stats — últimos 30 dias</p>
      </div>

      {/* ── Teams ── */}
      {TEAMS.filter(t => !t.cnOnly).map(team => (
        <div key={team.name} style={{ marginBottom: 40 }}>
          {/* Team header */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, paddingBottom: 10, borderBottom: `1px solid ${team.color}22` }}>
            <div style={{ width: 4, height: 24, background: team.color, borderRadius: 2 }} />
            <span style={{ fontWeight: 700, fontSize: 15, color: team.color }}>{team.name}</span>
            <span style={{ fontSize: 10, color: "#404040", border: "1px solid #222", padding: "1px 6px", borderRadius: 2 }}>{team.region}</span>
          </div>

          {/* Player cards grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 8 }}>
            {[...team.players].sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role)).map(player => {
              const s = stats[player.key];
              const champs = topChamps[player.key] ?? [];
              const hasData = !!s;

              return (
                <Link key={player.key} href={`/players/${encodeURIComponent(player.key)}`} className="player-card">

                    {/* Role + Name */}
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                      <span className={`role-badge role-${player.role}`}>{ROLE_SHORT[player.role]}</span>
                      <span style={{ fontWeight: 700, color: "#e0e0e0", fontSize: 13 }}>{player.display}</span>
                    </div>

                    {/* Champion icons */}
                    <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
                      {champs.length > 0 ? champs.map(c => (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img key={c.champion} src={championIconUrl(c.champion)} alt={c.champion}
                          width={28} height={28} loading="lazy"
                          title={`${c.champion} — ${c.games}g ${Math.round(c.wins/c.games*100)}%WR`}
                          style={{ borderRadius: 3, border: "1px solid #252525" }} />
                      )) : (
                        <span style={{ fontSize: 10, color: "#303030" }}>sem dados</span>
                      )}
                    </div>

                    {/* Stats */}
                    {hasData ? (
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <MiniStat label="KDA" value="—" color="#e0e0e0" />
                        <MiniStat label="WR%" value={`${Math.round((s.wins / s.games) * 100)}%`}
                          color={s.wins/s.games >= 0.5 ? "#50FF50" : "#FF4040"} />
                        <MiniStat label="CS/M" value={s.cs_per_min.toFixed(1)} />
                        <MiniStat label="JOGOS" value={String(s.games)} color="#606060" />
                      </div>
                    ) : (
                      <div style={{ fontSize: 10, color: "#303030", textAlign: "center", paddingTop: 4 }}>
                        sincronizar dados →
                      </div>
                    )}
                </Link>
              );
            })}
          </div>

          {/* CN teams placeholder */}
          {team.cnOnly && (
            <div style={{ padding: "20px", color: "#404040", fontSize: 12, background: "#080808", border: "1px solid #181818", borderRadius: 4 }}>
              ⚠ API da Riot não cobre a China — dados indisponíveis
            </div>
          )}
        </div>
      ))}

      {/* CN teams */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {TEAMS.filter(t => t.cnOnly).map(team => (
            <div key={team.name} className="nerv-card" style={{ borderTop: `2px solid ${team.color}` }}>
              <span style={{ fontWeight: 700, color: team.color }}>{team.name}</span>
              <span style={{ marginLeft: 8, fontSize: 10, color: "#404040" }}>{team.region}</span>
              <p style={{ fontSize: 11, color: "#404040", marginTop: 8 }}>
                ⚠ API Riot não cobre China — dados via análise manual
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Sync hint */}
      <div style={{ marginTop: 24, padding: "12px 16px", background: "#080808", border: "1px solid #181818", borderRadius: 3, fontSize: 11, color: "#404040" }}>
        <span style={{ color: "#FF9830" }}>// SYNC </span>
        Para atualizar os dados: <code style={{ color: "#20F0FF" }}>POST /api/riot/sync</code> com <code style={{ color: "#20F0FF" }}>{"{ gameName, tagLine, routing, team }"}</code> — ou use o VisionLOL desktop
      </div>
    </div>
  );
}
