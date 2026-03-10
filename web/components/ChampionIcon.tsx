"use client";
import { championIconUrl } from "@/lib/ddragon";
import { useState } from "react";

interface Props {
  name: string;
  size?: number;
  style?: React.CSSProperties;
}

export default function ChampionIcon({ name, size = 32, style }: Props) {
  const [err, setErr] = useState(false);

  if (!name || err) {
    return (
      <div style={{
        width: size, height: size,
        background: "#181818",
        border: "1px solid #222",
        borderRadius: 3,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: size * 0.35,
        color: "#404040",
        flexShrink: 0,
        ...style,
      }}>
        {name?.[0] ?? "?"}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={championIconUrl(name)}
      alt={name}
      width={size}
      height={size}
      loading="lazy"
      onError={() => setErr(true)}
      style={{
        borderRadius: 3,
        flexShrink: 0,
        objectFit: "cover",
        border: "1px solid #2a2a2a",
        ...style,
      }}
    />
  );
}
