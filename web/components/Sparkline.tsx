// Sparkline SVG puro — funciona em Server Components

interface Props {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
}

export default function Sparkline({ values, width = 80, height = 24, color = "#FF9830", fill = false }: Props) {
  if (!values || values.length < 2) {
    return <div style={{ width, height, background: "#111", borderRadius: 2 }} />;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });

  const points = pts.join(" ");
  const lastPt = pts[pts.length - 1].split(",");

  const fillPath = fill
    ? `M0,${height} L${pts.join(" L")} L${width},${height} Z`
    : undefined;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", overflow: "visible" }}>
      {fill && fillPath && (
        <path d={fillPath} fill={color} fillOpacity={0.12} />
      )}
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle
        cx={parseFloat(lastPt[0])}
        cy={parseFloat(lastPt[1])}
        r={2.5}
        fill={color}
      />
    </svg>
  );
}
