import { notFound } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { TEAMS, ROLE_SHORT } from "@/lib/teams";
import { championIconUrl, championSplashUrl } from "@/lib/ddragon";
import ChampionIcon from "@/components/ChampionIcon";
import Sparkline from "@/components/Sparkline";

export const revalidate = 300;

const PERIOD_LABELS: Record<string, string> = { all: "Total", "30d": "30 dias", "14d": "14 dias" };

async function getData(key: string) {
  const [{ data: account }, { data: stats }, { data: champs }, { data: recent }] = await Promise.all([
    supabase.from("riot_accounts").select("*").eq("player_key", key).single(),
    supabase.from("player_stats_cache").select("*").eq("player_key", key).order("period"),
    supabase.from("v_champion_pool").select("*").eq("player_key", key).order("games", { ascending: false }).limit(12),
    supabase.from("match_participants").select("*").eq("player_key", key).order("game_date", { ascending: false }).limit(15),
  ]);

  return { account, stats: stats ?? [], champs: champs ?? [], recent: recent ?? [] };
}

function getPlayer(key: string) {
  for (const team of TEAMS) {
    const p = team.players.find(p => p.key === key);
    if (p) return { player: p, team };
  }
  return null;
}

export default async function PlayerPage({ params }: { params: Promise<{ key: string }> }) {
  const { key: rawKey } = await params;
  const key = decodeURIComponent(rawKey);

  const meta = getPlayer(key);
  const { account, stats, champs, recent } = await getData(key);

  if (!meta && !account) notFound();

  const player  = meta?.player;
  const team    = meta?.team;
  const stat30  = stats.find((s: any) => s.period === "30d");
  const statAll = stats.find((s: any) => s.period === "all");

  // Sparkline: KDA das últimas 15 partidas (ordem cronológica)
  const kdaHistory = [...recent].reverse().map((r: any) =>
    (r.kills + r.assists) / Math.max(r.deaths, 1)
  );

  // Splash do campeão mais jogado
  const topChamp = champs[0]?.champion ?? "";

  return (
    <div>
      {/* ── Hero ── */}
      <div style={{
        position: "relative",
        background: "#050505",
        border: "1px solid #1a1a1a",
        borderRadius: 6,
        overflow: "hidden",
        marginBottom: 32,
        padding: "24px 28px",
      }}>
        {/* Splash background */}
        {topChamp && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={championSplashUrl(topChamp)}
            alt=""
            style={{
              position: "absolute", right: -40, top: 0,
              height: "100%", width: 260, objectFit: "cover",
              opacity: 0.08, pointerEvents: "none",
            }}
          />
        )}

        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap", marginBottom: 6 }}>
            {player && (
              <span className={`role-badge role-${player.role}`}>
                {ROLE_SHORT[player.role] ?? player.role}
              </span>
            )}
            <h1 style={{ fontSize: 26, fontWeight: 700, color: team?.color ?? "#FF9830" }}>
              {player?.display ?? key.split("#")[0]}
            </h1>
            <span style={{ fontSize: 13, color: "#404040" }}>{key}</span>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            {team && (
              <span style={{ fontSize: 11, color: team.color, border: `1px solid ${team.color}44`, padding: "1px 8px", borderRadius: 2 }}>
                {team.name} · {team.region}
              </span>
            )}
            {account?.region && (
              <span style={{ fontSize: 10, color: "#404040", border: "1px solid #222", padding: "1px 6px", borderRadius: 2 }}>
                {account.region.toUpperCase()}
              </span>
            )}
            {account?.updated_at && (
              <span style={{ fontSize: 10, color: "#303030" }}>
                sync {new Date(account.updated_at).toLocaleDateString("pt-BR")}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Stats por período ── */}
      {stats.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>// PERFORMANCE</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 8 }}>
            {stats.map((s: any) => {
              const wr = s.games ? Math.round((s.wins / s.games) * 100) : 0;
              return (
                <div key={s.period} className="nerv-card" style={{ padding: "14px 16px" }}>
                  <div style={{ fontSize: 10, color: "#404040", marginBottom: 10, letterSpacing: "0.1em" }}>
                    {PERIOD_LABELS[s.period] ?? s.period}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                    {[
                      { l: "KDA",    v: s.kda?.toFixed(2),    c: s.kda >= 4 ? "#50FF50" : s.kda >= 2.5 ? "#FF9830" : "#FF4040" },
                      { l: "WR%",    v: `${wr}%`,              c: wr >= 50 ? "#50FF50" : "#FF4040" },
                      { l: "JOGOS",  v: s.games,               c: "#606060" },
                      { l: "CS/M",   v: s.cs_per_min?.toFixed(1), c: "#e0e0e0" },
                      { l: "VIS/M",  v: s.vision_per_min?.toFixed(1), c: "#e0e0e0" },
                      { l: "TOP",    v: s.top_champ || "—",    c: "#FF9830" },
                    ].map(({ l, v, c }) => (
                      <div key={l} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 9, color: "#404040", marginBottom: 2 }}>{l}</div>
                        <div style={{ fontSize: 12, color: c, fontWeight: 600 }}>{v}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── KDA Sparkline ── */}
      {kdaHistory.length >= 2 && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>// KDA — ÚLTIMAS {kdaHistory.length} PARTIDAS</div>
          <div className="nerv-card" style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 20 }}>
            <Sparkline values={kdaHistory} width={200} height={36} fill color="#FF9830" />
            <div style={{ display: "flex", gap: 16 }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 9, color: "#404040" }}>MÁX</div>
                <div style={{ fontSize: 13, color: "#50FF50" }}>{Math.max(...kdaHistory).toFixed(1)}</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 9, color: "#404040" }}>MÍN</div>
                <div style={{ fontSize: 13, color: "#FF4040" }}>{Math.min(...kdaHistory).toFixed(1)}</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 9, color: "#404040" }}>MÉD</div>
                <div style={{ fontSize: 13, color: "#FF9830" }}>
                  {(kdaHistory.reduce((a, b) => a + b, 0) / kdaHistory.length).toFixed(1)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Champion Pool ── */}
      {champs.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>// CHAMPION POOL</div>
          <table className="nerv-table">
            <thead>
              <tr>
                <th></th>
                <th>CAMPEÃO</th>
                <th>JOGOS</th>
                <th>WIN RATE</th>
                <th>KDA</th>
                <th>CS/MIN</th>
                <th>ÚLT. JOGO</th>
              </tr>
            </thead>
            <tbody>
              {champs.map((c: any) => {
                const wr = c.games ? Math.round((c.wins / c.games) * 100) : 0;
                return (
                  <tr key={c.champion}>
                    <td style={{ width: 36 }}>
                      <ChampionIcon name={c.champion} size={28} />
                    </td>
                    <td style={{ fontWeight: 600, color: "#e0e0e0" }}>{c.champion}</td>
                    <td style={{ color: "#606060" }}>{c.games}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <div style={{ width: 60, height: 4, background: "#1a1a1a", borderRadius: 2, overflow: "hidden" }}>
                          <div style={{ width: `${wr}%`, height: "100%", background: wr >= 60 ? "#50FF50" : wr >= 50 ? "#FF9830" : "#FF4040" }} />
                        </div>
                        <span style={{ fontSize: 11, color: wr >= 60 ? "#50FF50" : wr >= 50 ? "#FF9830" : "#FF4040", minWidth: 30 }}>{wr}%</span>
                      </div>
                    </td>
                    <td className={c.kda >= 3 ? "kda-good" : c.kda >= 2 ? "kda-ok" : "kda-bad"}>{c.kda.toFixed(2)}</td>
                    <td style={{ color: "#808080" }}>{c.cs_per_min.toFixed(1)}</td>
                    <td style={{ fontSize: 11, color: "#404040" }}>{c.last_played ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Partidas recentes ── */}
      {recent.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 12 }}>// PARTIDAS RECENTES</div>
          <table className="nerv-table">
            <thead>
              <tr>
                <th>DATA</th>
                <th></th>
                <th>CAMPEÃO</th>
                <th>RESULTADO</th>
                <th>KDA</th>
                <th>CS</th>
                <th>VISION</th>
                <th>DURAÇÃO</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((r: any) => {
                const kda = (r.kills + r.assists) / Math.max(r.deaths, 1);
                const mins = Math.floor(r.game_duration / 60);
                const secs = r.game_duration % 60;
                return (
                  <tr key={`${r.match_id}-${r.puuid}`}>
                    <td style={{ color: "#505050", fontSize: 11 }}>{r.game_date}</td>
                    <td><ChampionIcon name={r.champion} size={24} /></td>
                    <td style={{ color: "#e0e0e0" }}>{r.champion}</td>
                    <td>
                      <span className={`badge ${r.win ? "badge-win" : "badge-loss"}`}>
                        {r.win ? "WIN" : "LOSS"}
                      </span>
                    </td>
                    <td>
                      <span className={kda >= 4 ? "kda-good" : kda >= 2.5 ? "kda-ok" : "kda-bad"}>
                        {kda.toFixed(1)}
                      </span>
                      <span style={{ color: "#404040", fontSize: 10, marginLeft: 5 }}>
                        {r.kills}/{r.deaths}/{r.assists}
                      </span>
                    </td>
                    <td style={{ color: "#808080" }}>
                      {r.cs}
                      <span style={{ color: "#505050", fontSize: 10, marginLeft: 4 }}>
                        ({(r.cs / Math.max(r.game_duration / 60, 1)).toFixed(1)}/m)
                      </span>
                    </td>
                    <td style={{ color: "#808080" }}>{r.vision_score}</td>
                    <td style={{ color: "#505050", fontSize: 11 }}>{mins}:{String(secs).padStart(2, "0")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!account && (
        <div className="nerv-card" style={{ textAlign: "center", padding: 40, color: "#404040" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>◈</div>
          <p style={{ color: "#606060", marginBottom: 8 }}>{player?.display ?? key} — sem dados sincronizados</p>
          <p style={{ fontSize: 11 }}>
            Use <code style={{ color: "#20F0FF" }}>POST /api/riot/sync</code> com <code style={{ color: "#20F0FF" }}>{"{ gameName: \"" + (player?.gameName ?? "...") + "\", tagLine: \"" + (player?.tagLine ?? "...") + "\", routing: \"" + (player?.routing ?? "americas") + "\", team: \"" + (team?.name ?? "LOUD") + "\" }"}</code>
          </p>
        </div>
      )}
    </div>
  );
}
