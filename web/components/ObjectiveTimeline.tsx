"use client";

export interface GameEvent {
  EventName: string;
  EventTime: number;
  EventID?: number;
  KillerName?: string;
  DragonType?: string;
  Assisters?: string[];
  VictimName?: string;
  TurretKilled?: string;
  InhibKilled?: string;
  BaronKilled?: string;
  // raw passthrough
  [key: string]: unknown;
}

interface Props {
  events: GameEvent[];
  gameTime: number;
}

const OBJECTIVE_NAMES = new Set([
  "DragonKill", "BaronKill", "HeraldKill",
  "TurretKilled", "InhibKilled", "InhibRespawned",
  "GameStart", "GameEnd",
  "FirstBlood", "Ace",
]);

const EVENT_EMOJI: Record<string, string> = {
  DragonKill:      "🐉",
  BaronKill:       "🟣",
  HeraldKill:      "👁",
  TurretKilled:    "🏰",
  InhibKilled:     "💥",
  InhibRespawned:  "🔄",
  FirstBlood:      "🩸",
  Ace:             "⚡",
  GameStart:       "▶",
  GameEnd:         "🏁",
};

const EVENT_COLOR: Record<string, string> = {
  DragonKill:   "#FF9830",
  BaronKill:    "#a855f7",
  HeraldKill:   "#06b6d4",
  TurretKilled: "#6b7280",
  InhibKilled:  "#ef4444",
  FirstBlood:   "#ef4444",
  Ace:          "#20F0FF",
  GameEnd:      "#50FF50",
};

function fmt(secs: number) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function label(ev: GameEvent): string {
  switch (ev.EventName) {
    case "DragonKill":   return `${ev.DragonType ?? ""} Dragon`;
    case "BaronKill":    return "Baron Nashor";
    case "HeraldKill":   return "Rift Herald";
    case "TurretKilled": return `Turret`;
    case "InhibKilled":  return `Inibidor`;
    case "FirstBlood":   return `First Blood`;
    case "Ace":          return `Ace`;
    default:             return ev.EventName;
  }
}

export default function ObjectiveTimeline({ events, gameTime }: Props) {
  const objectives = events.filter(e => OBJECTIVE_NAMES.has(e.EventName));

  if (!objectives.length) {
    return (
      <div style={{ fontSize: 11, color: "#303030", padding: "12px 0" }}>
        Sem eventos registrados
      </div>
    );
  }

  return (
    <div style={{ position: "relative" }}>
      {/* Progress bar background */}
      <div style={{ height: 2, background: "#1a1a1a", borderRadius: 1, marginBottom: 16, position: "relative" }}>
        {gameTime > 0 && objectives.map((ev, i) => (
          <div key={i} style={{
            position: "absolute",
            left: `${Math.min((ev.EventTime / gameTime) * 100, 100)}%`,
            top: -3,
            width: 2,
            height: 8,
            background: EVENT_COLOR[ev.EventName] ?? "#505050",
            borderRadius: 1,
          }} />
        ))}
        {/* Current time cursor */}
        <div style={{
          position: "absolute",
          left: "100%",
          top: -4,
          width: 1,
          height: 10,
          background: "#20F0FF",
          borderRadius: 1,
        }} />
      </div>

      {/* Event list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 200, overflowY: "auto" }}>
        {[...objectives].reverse().map((ev, i) => (
          <div key={i} style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "4px 8px",
            background: "#080808",
            border: `1px solid ${(EVENT_COLOR[ev.EventName] ?? "#1a1a1a")}22`,
            borderRadius: 3,
            fontSize: 11,
          }}>
            <span style={{ fontSize: 13 }}>{EVENT_EMOJI[ev.EventName] ?? "◆"}</span>
            <span style={{ color: "#404040", fontVariantNumeric: "tabular-nums", minWidth: 36 }}>
              {fmt(ev.EventTime)}
            </span>
            <span style={{ color: EVENT_COLOR[ev.EventName] ?? "#e0e0e0", flex: 1, fontWeight: 600 }}>
              {label(ev)}
            </span>
            {ev.KillerName && (
              <span style={{ fontSize: 10, color: "#505050" }}>
                {String(ev.KillerName).split(" ")[0]}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
