import LiveBoard from "./LiveBoard";

export const dynamic = "force-dynamic";

export default function LivePage() {
  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 11, color: "#404040", letterSpacing: "0.1em", marginBottom: 6 }}>// MÓDULO 06</div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#20F0FF" }}>LIVE</h1>
          <span style={{ fontSize: 11, padding: "2px 8px", background: "#20F0FF22", color: "#20F0FF", borderRadius: 2, fontWeight: 700 }}>
            AO VIVO
          </span>
        </div>
        <p style={{ color: "#505050", fontSize: 12, marginTop: 4 }}>
          Overlay analítico em tempo real — dados transmitidos pelos agentes durante a partida
        </p>
      </div>

      <LiveBoard />
    </div>
  );
}
