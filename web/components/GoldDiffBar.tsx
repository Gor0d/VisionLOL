"use client";

interface Props {
  /** gold time-series: [{t: seconds, gold: number}] */
  series: { t: number; gold: number }[];
  /** label for this player */
  label?: string;
  color?: string;
  width?: number;
  height?: number;
}

/**
 * Micro sparkline showing gold accumulation over time.
 * Gold is only available for the activePlayer in each agent snapshot,
 * so we display a per-player line when data exists.
 */
export default function GoldDiffBar({ series, label, color = "#FF9830", width = 200, height = 40 }: Props) {
  if (!series || series.length < 2) {
    return (
      <div style={{ width, height, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 9, color: "#303030" }}>sem dados</span>
      </div>
    );
  }

  const maxT    = series[series.length - 1].t;
  const minGold = Math.min(...series.map(s => s.gold));
  const maxGold = Math.max(...series.map(s => s.gold));
  const range   = maxGold - minGold || 1;

  const pts = series.map(s => {
    const x = (s.t / maxT) * width;
    const y = height - ((s.gold - minGold) / range) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const current = series[series.length - 1].gold;

  return (
    <div style={{ position: "relative" }}>
      {label && (
        <div style={{ fontSize: 9, color: "#404040", marginBottom: 2 }}>{label}</div>
      )}
      <svg width={width} height={height} style={{ display: "block", overflow: "visible" }}>
        <defs>
          <linearGradient id={`gold-fill-${label}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        {/* Fill area */}
        <polyline
          points={`0,${height} ${pts} ${width},${height}`}
          fill={`url(#gold-fill-${label})`}
          stroke="none"
        />
        {/* Line */}
        <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
        {/* Last point dot */}
        {series.length > 0 && (() => {
          const last = series[series.length - 1];
          const x = (last.t / maxT) * width;
          const y = height - ((last.gold - minGold) / range) * (height - 4) - 2;
          return <circle cx={x} cy={y} r={2.5} fill={color} />;
        })()}
      </svg>
      <div style={{ fontSize: 10, color, fontWeight: 700, marginTop: 2 }}>
        {current.toLocaleString("pt-BR")} g
      </div>
    </div>
  );
}
