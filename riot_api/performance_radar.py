# -*- coding: utf-8 -*-
"""
PlayerRadar — Radar de performance por jogador com 6 indicadores LoL.

Métricas calculadas a partir do histórico de partidas (Match-V5):
  KDA · CS/min · Visão/min · Gold/min · Damage Share · Kill Participation

Desenho em puro tkinter Canvas (sem matplotlib).
"""

import tkinter as tk
import threading
import math

# ═══════════════════════════════════════════════════════════════════════
#  PALETA  (alinhada com dashboard_viewer / team_viewer)
# ═══════════════════════════════════════════════════════════════════════
BG_DARKEST  = "#0d1117"
BG_DARK     = "#161b22"
BG_MEDIUM   = "#1c2129"
BG_LIGHT    = "#21262d"
BORDER      = "#30363d"

ACCENT      = "#58a6ff"
SUCCESS     = "#3fb950"
DANGER      = "#f85149"
WARNING     = "#d29922"
PURPLE      = "#bc8cff"

TEXT_BRIGHT = "#ffffff"
TEXT_COLOR  = "#e6edf3"
TEXT_DIM    = "#7d8590"

ROLE_COLORS = {
    "TOP":     "#e5534b",
    "JUNGLE":  "#3fb950",
    "MID":     "#58a6ff",
    "ADC":     "#d29922",
    "SUPPORT": "#bc8cff",
}

# ═══════════════════════════════════════════════════════════════════════
#  BENCHMARKS POR ROLE (valor = 100% no radar = padrão pro/soloq alto)
# ═══════════════════════════════════════════════════════════════════════
ROLE_BENCHMARKS = {
    "TOP": {
        "kda":          3.5,
        "cs_per_min":   8.0,
        "vision_pm":    1.2,
        "gold_per_min": 440.0,
        "dmg_share":    0.25,
        "kill_part":    0.60,
    },
    "JUNGLE": {
        "kda":          4.0,
        "cs_per_min":   6.0,
        "vision_pm":    1.5,
        "gold_per_min": 380.0,
        "dmg_share":    0.20,
        "kill_part":    0.75,
    },
    "MID": {
        "kda":          4.0,
        "cs_per_min":   8.5,
        "vision_pm":    1.2,
        "gold_per_min": 440.0,
        "dmg_share":    0.28,
        "kill_part":    0.65,
    },
    "ADC": {
        "kda":          5.0,
        "cs_per_min":   9.0,
        "vision_pm":    1.0,
        "gold_per_min": 460.0,
        "dmg_share":    0.30,
        "kill_part":    0.60,
    },
    "SUPPORT": {
        "kda":          4.5,
        "cs_per_min":   1.0,
        "vision_pm":    2.5,
        "gold_per_min": 250.0,
        "dmg_share":    0.10,
        "kill_part":    0.75,
    },
}

DEFAULT_BENCHMARK = ROLE_BENCHMARKS["MID"]

METRICS_ORDER = ["kda", "cs_per_min", "vision_pm", "gold_per_min", "dmg_share", "kill_part"]

METRICS_LABELS = {
    "kda":          "KDA",
    "cs_per_min":   "CS/min",
    "vision_pm":    "Visão/min",
    "gold_per_min": "Gold/min",
    "dmg_share":    "Dmg Share",
    "kill_part":    "Kill Part.",
}

METRICS_ICONS = {
    "kda":          "⚔",
    "cs_per_min":   "🌾",
    "vision_pm":    "👁",
    "gold_per_min": "💰",
    "dmg_share":    "💥",
    "kill_part":    "🎯",
}


# ═══════════════════════════════════════════════════════════════════════
#  CÁLCULO DE MÉTRICAS
# ═══════════════════════════════════════════════════════════════════════

def compute_player_metrics(summaries, match_data_cache: dict, puuid: str) -> dict:
    """
    Calcula métricas de performance médias a partir das partidas fornecidas.

    summaries: list of (match_id, summary_dict)
               ou    list of (match_id, summary_dict, match_data)
    match_data_cache: dict {match_id: match_data} — usado como fallback
    puuid: PUUID do jogador alvo

    Retorna dict {metric_key: float_value} com as médias.
    """
    totals = {m: 0.0 for m in METRICS_ORDER}
    count  = 0

    for entry in summaries:
        if len(entry) == 3:
            match_id, _s, md = entry
        else:
            match_id, _s = entry
            md = match_data_cache.get(match_id)

        if not md:
            continue

        duration_s = md.get("info", {}).get("gameDuration", 0)
        if duration_s < 120:   # ignora partidas muito curtas (remake)
            continue

        minutes = duration_s / 60.0

        # Localiza o participante pelo PUUID
        participant = None
        for p in md.get("info", {}).get("participants", []):
            if p.get("puuid") == puuid:
                participant = p
                break
        if not participant:
            continue

        k    = participant.get("kills",    0)
        d    = participant.get("deaths",   0)
        a    = participant.get("assists",  0)
        cs   = (participant.get("totalMinionsKilled", 0)
                + participant.get("neutralMinionsKilled", 0))
        vs   = participant.get("visionScore",                   0)
        gold = participant.get("goldEarned",                    0)
        dmg  = participant.get("totalDamageDealtToChampions",   0)
        tid  = participant.get("teamId", 100)

        # Agrega stats do mesmo time
        team_kills = 0
        team_dmg   = 0
        for p in md.get("info", {}).get("participants", []):
            if p.get("teamId") == tid:
                team_kills += p.get("kills", 0)
                team_dmg   += p.get("totalDamageDealtToChampions", 0)

        totals["kda"]          += (k + a) / max(d, 1)
        totals["cs_per_min"]   += cs   / minutes
        totals["vision_pm"]    += vs   / minutes
        totals["gold_per_min"] += gold / minutes
        totals["dmg_share"]    += dmg  / max(team_dmg,   1)
        totals["kill_part"]    += (k + a) / max(team_kills, 1)
        count += 1

    if count == 0:
        return {m: 0.0 for m in METRICS_ORDER}

    return {m: totals[m] / count for m in METRICS_ORDER}


def normalize_metrics(raw: dict, role: str) -> dict:
    """Normaliza métricas raw contra benchmarks do role. Retorna dict 0.0–1.2+."""
    bench = ROLE_BENCHMARKS.get(role.upper(), DEFAULT_BENCHMARK)
    return {
        m: min(raw.get(m, 0.0) / max(bench.get(m, 1.0), 1e-9), 1.3)
        for m in METRICS_ORDER
    }


# ═══════════════════════════════════════════════════════════════════════
#  JANELA PRINCIPAL DE RADAR
# ═══════════════════════════════════════════════════════════════════════

class PlayerRadar(tk.Toplevel):
    """
    Janela de radar de performance individual.

    Mostra gráfico radar com 6 eixos + painel de métricas detalhadas.
    Suporta overlay de comparação (ex: média do time ou adversário).
    """

    RADAR_R = 130   # raio do radar em pixels

    def __init__(self, root, player: dict, summaries,
                 match_data_cache: dict, puuid: str,
                 role: str = "MID",
                 compare_metrics: dict = None,
                 compare_label: str = "Média do Time"):
        """
        player          : dict com 'display', 'game_name', 'role'
        summaries       : list[(match_id, summary)] ou [(match_id, summary, match_data)]
        match_data_cache: {match_id: match_data}
        puuid           : PUUID do jogador
        role            : role string (TOP/JUNGLE/MID/ADC/SUPPORT)
        compare_metrics : dict {metric: normalized_value} para overlay opcional
        compare_label   : nome do overlay de comparação
        """
        super().__init__(root)

        self.title(f"Radar — {player.get('display', player.get('game_name', '?'))}")
        self.configure(bg=BG_DARKEST)
        self.geometry("760x580")
        self.resizable(False, False)
        self.lift()

        self.player          = player
        self.role            = role.upper()
        self.puuid           = puuid
        self.compare_metrics = compare_metrics   # já normalizado (0-1)
        self.compare_label   = compare_label

        n_games = sum(1 for e in summaries
                      if (match_data_cache.get(e[0]) if len(e) == 2
                          else e[2]) is not None)
        self._n_games = len(summaries)

        self._raw        = compute_player_metrics(summaries, match_data_cache, puuid)
        self._normalized = normalize_metrics(self._raw, self.role)

        self._build()

    # ─────────────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()

        body = tk.Frame(self, bg=BG_DARKEST)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        left  = tk.Frame(body, bg=BG_DARKEST)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right = tk.Frame(body, bg=BG_DARKEST, width=252)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        self._build_radar_canvas(left)
        self._build_stats_panel(right)

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_DARK, height=54)
        hdr.pack(fill=tk.X, padx=10, pady=(10, 0))
        hdr.pack_propagate(False)

        role_color = ROLE_COLORS.get(self.role, ACCENT)
        name       = self.player.get("display", self.player.get("game_name", "?"))

        tk.Label(hdr, text="🕸",
                 font=("Segoe UI", 16),
                 bg=BG_DARK, fg=role_color).pack(side=tk.LEFT, padx=(12, 6), pady=10)
        tk.Label(hdr, text=f"Radar de Performance — {name}",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, pady=10)

        # Badge de role
        tk.Label(hdr, text=f" {self.role} ",
                 font=("Segoe UI", 9, "bold"),
                 bg=role_color, fg=BG_DARKEST).pack(side=tk.LEFT, padx=8)

        # Contagem de partidas
        tk.Label(hdr, text=f"{self._n_games} partidas",
                 font=("Segoe UI", 9),
                 bg=BG_DARK, fg=TEXT_DIM).pack(side=tk.RIGHT, padx=14)

    def _build_radar_canvas(self, parent):
        size = 420
        self._canvas = tk.Canvas(
            parent,
            width=size, height=size,
            bg=BG_DARKEST, highlightthickness=0
        )
        self._canvas.pack(expand=True)
        self._draw_radar(self._canvas, size)

        # Legenda (se houver comparação)
        if self.compare_metrics:
            leg = tk.Frame(parent, bg=BG_DARKEST)
            leg.pack()
            role_color = ROLE_COLORS.get(self.role, ACCENT)
            name = self.player.get("display", "Jogador")

            for color, label in [(role_color, name), ("#888888", self.compare_label)]:
                tk.Label(leg, text="━━", font=("Segoe UI", 9, "bold"),
                         bg=BG_DARKEST, fg=color).pack(side=tk.LEFT, padx=(6, 2))
                tk.Label(leg, text=label, font=("Segoe UI", 8),
                         bg=BG_DARKEST, fg=TEXT_DIM).pack(side=tk.LEFT, padx=(0, 10))

    def _build_stats_panel(self, parent):
        tk.Label(parent, text="MÉTRICAS DETALHADAS",
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_DARKEST, fg=TEXT_DIM).pack(anchor="w", padx=8, pady=(8, 4))

        bench = ROLE_BENCHMARKS.get(self.role, DEFAULT_BENCHMARK)

        for metric in METRICS_ORDER:
            raw   = self._raw.get(metric, 0.0)
            norm  = self._normalized.get(metric, 0.0)
            ref   = bench.get(metric, 1.0)
            label = METRICS_LABELS[metric]
            icon  = METRICS_ICONS[metric]

            val_str, ref_str = _format_metric(metric, raw, ref)

            pct   = min(max(norm, 0.0), 1.0)
            bar_c = SUCCESS if norm >= 0.85 else (WARNING if norm >= 0.60 else DANGER)

            row = tk.Frame(parent, bg=BG_MEDIUM)
            row.pack(fill=tk.X, padx=6, pady=2)

            # Título + valor
            top = tk.Frame(row, bg=BG_MEDIUM)
            top.pack(fill=tk.X, padx=6, pady=(5, 0))
            tk.Label(top, text=f"{icon} {label}",
                     font=("Segoe UI", 9, "bold"),
                     bg=BG_MEDIUM, fg=TEXT_COLOR).pack(side=tk.LEFT)
            tk.Label(top, text=val_str,
                     font=("Segoe UI", 9, "bold"),
                     bg=BG_MEDIUM, fg=bar_c).pack(side=tk.RIGHT)

            # Barra de progresso
            bar_bg = tk.Frame(row, bg=BG_LIGHT, height=6)
            bar_bg.pack(fill=tk.X, padx=6, pady=(2, 0))
            bar_bg.update_idletasks()
            if pct > 0:
                bar = tk.Frame(bar_bg, bg=bar_c, height=6)
                bar.place(relwidth=pct, relheight=1.0, x=0, y=0)

            # Referência
            pct_text = f"{int(norm * 100)}% do benchmark"
            tk.Label(row, text=f"{pct_text}   ref: {ref_str}",
                     font=("Segoe UI", 7), bg=BG_MEDIUM, fg=TEXT_DIM
                     ).pack(anchor="e", padx=6, pady=(0, 4))

    # ─────────────────────────────────────────────────────────────────
    #  RADAR CHART
    # ─────────────────────────────────────────────────────────────────

    def _draw_radar(self, canvas, size: int):
        cx = size // 2
        cy = size // 2
        R  = self.RADAR_R
        n  = len(METRICS_ORDER)

        # Ângulos: começa no topo (−π/2), sentido horário
        angles = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        role_color = ROLE_COLORS.get(self.role, ACCENT)

        # ── Grid: anéis percentuais ───────────────────────────────────
        ring_levels = [0.25, 0.50, 0.75, 1.00]
        for level in ring_levels:
            pts = []
            for ang in angles:
                pts.extend([
                    cx + R * level * math.cos(ang),
                    cy + R * level * math.sin(ang),
                ])
            color = BORDER if level == 1.0 else "#1e2630"
            width = 2 if level == 1.0 else 1
            canvas.create_polygon(pts, outline=color, fill="", width=width)

        # Marcadores de % sobre o eixo vertical (entre anel e anel)
        for level in ring_levels:
            lx = cx + R * level * math.cos(angles[0]) - 16
            ly = cy + R * level * math.sin(angles[0]) - 8
            canvas.create_text(lx, ly,
                               text=f"{int(level * 100)}%",
                               font=("Segoe UI", 7), fill=TEXT_DIM)

        # ── Eixos radiais ─────────────────────────────────────────────
        for ang in angles:
            canvas.create_line(
                cx, cy,
                cx + R * math.cos(ang), cy + R * math.sin(ang),
                fill="#263040", width=1
            )

        # ── Overlay de comparação (cinza) ─────────────────────────────
        if self.compare_metrics:
            cmp_pts = []
            for i, metric in enumerate(METRICS_ORDER):
                v   = min(self.compare_metrics.get(metric, 0.0), 1.2)
                ang = angles[i]
                cmp_pts.extend([
                    cx + R * v * math.cos(ang),
                    cy + R * v * math.sin(ang),
                ])
            fill_cmp = _blend_color("#888888", BG_DARKEST, 0.15)
            canvas.create_polygon(cmp_pts,
                                  fill=fill_cmp, outline="#888888", width=1,
                                  dash=(4, 3))

        # ── Polígono principal ─────────────────────────────────────────
        pts = []
        for i, metric in enumerate(METRICS_ORDER):
            v   = self._normalized.get(metric, 0.0)
            ang = angles[i]
            pts.extend([
                cx + R * v * math.cos(ang),
                cy + R * v * math.sin(ang),
            ])

        fill_poly = _blend_color(role_color, BG_DARKEST, 0.28)
        canvas.create_polygon(pts, fill=fill_poly, outline=role_color, width=2)

        # Pontos nos vértices
        for i, metric in enumerate(METRICS_ORDER):
            v   = self._normalized.get(metric, 0.0)
            ang = angles[i]
            px  = cx + R * v * math.cos(ang)
            py  = cy + R * v * math.sin(ang)
            r2  = 5
            canvas.create_oval(
                px - r2, py - r2, px + r2, py + r2,
                fill=role_color, outline=BG_DARKEST, width=2
            )

        # ── Rótulos dos eixos ─────────────────────────────────────────
        label_pad = 36
        for i, metric in enumerate(METRICS_ORDER):
            ang   = angles[i]
            lx    = cx + (R + label_pad) * math.cos(ang)
            ly    = cy + (R + label_pad) * math.sin(ang)
            label = METRICS_LABELS[metric]
            raw   = self._raw.get(metric, 0.0)
            _, val_str = _format_metric(metric, raw, 0)

            # Ajuste de âncora conforme posição no círculo
            anchor = _label_anchor(ang)

            canvas.create_text(
                lx, ly,
                text=f"{label}\n{val_str}",
                font=("Segoe UI", 8, "bold"),
                fill=TEXT_COLOR,
                justify="center",
                anchor=anchor,
            )


# ═══════════════════════════════════════════════════════════════════════
#  JANELA COMPARAÇÃO DE MÚLTIPLOS JOGADORES (time inteiro)
# ═══════════════════════════════════════════════════════════════════════

class TeamRadarView(tk.Toplevel):
    """
    Exibe 5 mini-radares (um por jogador do time) em uma única janela.
    Útil para visão geral de performance do roster.
    """

    MINI_R  = 75
    CELL_W  = 260
    CELL_H  = 280

    def __init__(self, root, players_data: list):
        """
        players_data: list of dict com chaves:
            'player'   : dict {display, game_name, role}
            'raw'      : dict {metric: float}
            'norm'     : dict {metric: float}
            'n_games'  : int
        """
        super().__init__(root)
        self.title("Radar do Time — VisionLOL")
        self.configure(bg=BG_DARKEST)
        self.resizable(True, True)
        self.lift()

        self._data = players_data
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG_DARK, height=50)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🕸  Radar do Time — Performance por Jogador",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=14, pady=10)
        tk.Label(hdr, text=f"{len(self._data)} jogadores",
                 font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.RIGHT, padx=14)

        # Grade de radares
        grid = tk.Frame(self, bg=BG_DARKEST)
        grid.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        for idx, entry in enumerate(self._data):
            col  = idx % 5
            row_ = idx // 5
            cell = tk.Frame(grid, bg=BG_DARK,
                            width=self.CELL_W, height=self.CELL_H)
            cell.grid(row=row_, column=col, padx=4, pady=4, sticky="nsew")
            cell.grid_propagate(False)
            self._build_mini_radar(cell, entry)

        # Expande colunas igualmente
        for c in range(min(5, len(self._data))):
            grid.columnconfigure(c, weight=1)

    def _build_mini_radar(self, parent, entry: dict):
        player = entry["player"]
        role   = player.get("role", "MID").upper()
        norm   = entry.get("norm", {})
        raw    = entry.get("raw",  {})
        n_g    = entry.get("n_games", 0)
        name   = player.get("display", player.get("game_name", "?"))
        color  = ROLE_COLORS.get(role, ACCENT)

        # Sub-cabeçalho
        sub = tk.Frame(parent, bg=BG_MEDIUM)
        sub.pack(fill=tk.X)
        tk.Label(sub, text=f" {role[:3]} ",
                 font=("Segoe UI", 8, "bold"),
                 bg=color, fg=BG_DARKEST).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Label(sub, text=name,
                 font=("Segoe UI", 9, "bold"),
                 bg=BG_MEDIUM, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=4)
        tk.Label(sub, text=f"{n_g}p",
                 font=("Segoe UI", 8), bg=BG_MEDIUM, fg=TEXT_DIM
                 ).pack(side=tk.RIGHT, padx=6)

        # Canvas do mini-radar
        size  = self.CELL_H - 48   # subheader + margem
        canvas = tk.Canvas(parent, width=self.CELL_W, height=size,
                           bg=BG_DARK, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        self._draw_mini(canvas, self.CELL_W, size, norm, raw, color)

    def _draw_mini(self, canvas, w, h, norm: dict, raw: dict, color: str):
        cx = w // 2
        cy = h // 2
        R  = self.MINI_R
        n  = len(METRICS_ORDER)
        angles = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        # Anéis
        for level in [0.5, 1.0]:
            pts = []
            for ang in angles:
                pts.extend([
                    cx + R * level * math.cos(ang),
                    cy + R * level * math.sin(ang),
                ])
            canvas.create_polygon(pts, outline=BORDER if level == 1.0 else "#1e2630",
                                  fill="", width=1 if level < 1 else 2)

        # Eixos
        for ang in angles:
            canvas.create_line(cx, cy,
                               cx + R * math.cos(ang), cy + R * math.sin(ang),
                               fill="#1e2630", width=1)

        # Polígono
        pts = []
        for i, metric in enumerate(METRICS_ORDER):
            v   = norm.get(metric, 0.0)
            ang = angles[i]
            pts.extend([cx + R * v * math.cos(ang), cy + R * v * math.sin(ang)])

        fill_c = _blend_color(color, BG_DARK, 0.28)
        canvas.create_polygon(pts, fill=fill_c, outline=color, width=2)

        # Pontos
        for i, metric in enumerate(METRICS_ORDER):
            v  = norm.get(metric, 0.0)
            ang = angles[i]
            px  = cx + R * v * math.cos(ang)
            py  = cy + R * v * math.sin(ang)
            canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                               fill=color, outline=BG_DARKEST, width=2)

        # Rótulos compactos nos eixos
        label_pad = 18
        for i, metric in enumerate(METRICS_ORDER):
            ang   = angles[i]
            lx    = cx + (R + label_pad) * math.cos(ang)
            ly    = cy + (R + label_pad) * math.sin(ang)
            label = METRICS_LABELS[metric][:4]  # abreviado
            canvas.create_text(lx, ly, text=label,
                               font=("Segoe UI", 6), fill=TEXT_DIM,
                               anchor=_label_anchor(ang))


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _format_metric(metric: str, raw: float, ref: float) -> tuple:
    """Retorna (valor_formatado, ref_formatada)."""
    if metric == "kda":
        return f"{raw:.2f}", f"{ref:.1f}"
    elif metric in ("dmg_share", "kill_part"):
        return f"{raw * 100:.1f}%", f"{ref * 100:.0f}%"
    elif metric == "gold_per_min":
        return f"{raw:.0f}", f"{ref:.0f}"
    elif metric == "cs_per_min":
        return f"{raw:.1f}", f"{ref:.1f}"
    elif metric == "vision_pm":
        return f"{raw:.2f}", f"{ref:.1f}"
    return f"{raw:.2f}", f"{ref:.2f}"


def _label_anchor(ang: float) -> str:
    """Retorna âncora tkinter conforme ângulo do eixo."""
    a = ang % (2 * math.pi)
    if a < 0:
        a += 2 * math.pi
    # Divide o círculo em 6 setores de 60°
    if a < math.pi / 6 or a >= 11 * math.pi / 6:
        return "s"    # topo → ancora em baixo do texto
    elif a < math.pi / 2:
        return "sw"
    elif a < 5 * math.pi / 6:
        return "w"
    elif a < 7 * math.pi / 6:
        return "n"    # baixo → ancora em cima do texto
    elif a < 3 * math.pi / 2:
        return "ne"
    else:
        return "e"


def _blend_color(hex_color: str, bg_color: str, alpha: float) -> str:
    """
    Mistura hex_color com bg_color pelo fator alpha (0=bg, 1=cor).
    Simula transparência em Canvas tkinter (que não suporta alpha nativo).
    """
    def parse(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    r1, g1, b1 = parse(hex_color)
    r2, g2, b2 = parse(bg_color)
    r = int(r1 * alpha + r2 * (1 - alpha))
    g = int(g1 * alpha + g2 * (1 - alpha))
    b = int(b1 * alpha + b2 * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"
