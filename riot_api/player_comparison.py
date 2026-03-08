# -*- coding: utf-8 -*-
"""
PlayerComparisonView — Comparação de dois jogadores do roster.

Radar duplo sobreposto + tabela de métricas comparativa lado a lado.
Suporta qualquer par de jogadores, independente de role.
"""

import tkinter as tk
from tkinter import ttk
import math

# ═══════════════════════════════════════════════════════════════════════
#  PALETA
# ═══════════════════════════════════════════════════════════════════════
BG_DARKEST  = "#000000"
BG_DARK     = "#0A0A08"
BG_MEDIUM   = "#111110"
BG_LIGHT    = "#181816"
BORDER      = "#2A2A28"

ACCENT      = "#FF9830"
SUCCESS     = "#50FF50"
DANGER      = "#FF4840"
WARNING     = "#FFCC50"

TEXT_BRIGHT = "#E0E0D8"
TEXT_COLOR  = "#C8C8C0"
TEXT_DIM    = "#8A8A82"

ROLE_COLORS = {
    "TOP":     "#e5534b",
    "JUNGLE":  "#50FF50",
    "MID":     "#FF9830",
    "ADC":     "#FFCC50",
    "SUPPORT": "#20F0FF",
}

from riot_api.performance_radar import (
    METRICS_ORDER, METRICS_LABELS, METRICS_ICONS,
    ROLE_BENCHMARKS, DEFAULT_BENCHMARK,
    _format_metric, _label_anchor, _blend_color,
)

RADAR_R    = 140
CANVAS_SZ  = 400


class PlayerComparisonView(tk.Toplevel):
    """
    Janela de comparação entre dois jogadores do roster.

    players_data: list of dict {
        'player':  {display, game_name, role},
        'raw':     {metric: float},
        'norm':    {metric: float},
        'n_games': int,
    }
    """

    def __init__(self, root, players_data: list):
        super().__init__(root)
        self.title("⚔  Comparação de Jogadores — VisionLOL")
        self.configure(bg=BG_DARKEST)
        self.geometry("1020x600")
        self.resizable(False, False)
        self.lift()

        self._data  = players_data
        self._names = [
            p["player"].get("display", p["player"].get("game_name", "?"))
            for p in players_data
        ]

        self._idx_a = 0
        self._idx_b = min(1, len(players_data) - 1)

        self._build()

    # ─────────────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()

        body = tk.Frame(self, bg=BG_DARKEST)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 10))

        # Painel esquerdo (Jogador A)
        self._panel_a = tk.Frame(body, bg=BG_DARK, width=230)
        self._panel_a.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self._panel_a.pack_propagate(False)

        # Centro: radar + legenda
        center = tk.Frame(body, bg=BG_DARKEST)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(center, width=CANVAS_SZ, height=CANVAS_SZ,
                                 bg=BG_DARKEST, highlightthickness=0)
        self._canvas.pack(expand=True)

        self._legend_frame = tk.Frame(center, bg=BG_DARKEST)
        self._legend_frame.pack(pady=(0, 4))

        # Painel direito (Jogador B)
        self._panel_b = tk.Frame(body, bg=BG_DARK, width=230)
        self._panel_b.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        self._panel_b.pack_propagate(False)

        self._refresh()

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_DARK, height=56)
        hdr.pack(fill=tk.X, padx=10, pady=(10, 0))
        hdr.pack_propagate(False)

        tk.Label(hdr, text="⚔",
                 font=("Segoe UI", 16), bg=BG_DARK, fg=ACCENT
                 ).pack(side=tk.LEFT, padx=(12, 6), pady=10)
        tk.Label(hdr, text="Comparação de Jogadores",
                 font=("Segoe UI", 13, "bold"), bg=BG_DARK, fg=TEXT_BRIGHT
                 ).pack(side=tk.LEFT, pady=10)

        # Seletores (direita → esquerda para pack correto)
        self._cb_b = self._make_selector(hdr, side=tk.RIGHT, init=self._idx_b,
                                         callback=self._on_select_b)
        tk.Label(hdr, text="vs", font=("Segoe UI", 10, "bold"),
                 bg=BG_DARK, fg=TEXT_DIM).pack(side=tk.RIGHT, padx=6)
        self._cb_a = self._make_selector(hdr, side=tk.RIGHT, init=self._idx_a,
                                         callback=self._on_select_a)

    def _make_selector(self, parent, side, init, callback):
        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(side=side, padx=10, pady=8)

        style = ttk.Style()
        style.configure("Dark.TCombobox",
                        fieldbackground=BG_LIGHT,
                        background=BG_LIGHT,
                        foreground=TEXT_BRIGHT,
                        selectbackground=BG_MEDIUM,
                        selectforeground=TEXT_BRIGHT)

        cb = ttk.Combobox(frame, values=self._names, state="readonly",
                          width=18, font=("Segoe UI", 9))
        cb.current(init)
        cb.pack()
        cb.bind("<<ComboboxSelected>>", lambda e: callback(cb.current()))
        return cb

    # ─────────────────────────────────────────────────────────────────
    #  EVENTOS
    # ─────────────────────────────────────────────────────────────────

    def _on_select_a(self, idx: int):
        self._idx_a = idx
        self._refresh()

    def _on_select_b(self, idx: int):
        self._idx_b = idx
        self._refresh()

    # ─────────────────────────────────────────────────────────────────
    #  RENDERIZAÇÃO
    # ─────────────────────────────────────────────────────────────────

    def _refresh(self):
        da = self._data[self._idx_a]
        db = self._data[self._idx_b]

        # Radar
        self._canvas.delete("all")
        self._draw_radar(da, db)

        # Legenda
        for w in self._legend_frame.winfo_children():
            w.destroy()
        self._build_legend(da, db)

        # Painéis de stats
        for w in self._panel_a.winfo_children():
            w.destroy()
        for w in self._panel_b.winfo_children():
            w.destroy()

        color_a = ROLE_COLORS.get(da["player"].get("role", "MID").upper(), ACCENT)
        color_b = ROLE_COLORS.get(db["player"].get("role", "MID").upper(), ACCENT)
        self._build_stats_panel(self._panel_a, da, color_a, db)
        self._build_stats_panel(self._panel_b, db, color_b, da)

    def _draw_radar(self, da: dict, db: dict):
        cx = CANVAS_SZ // 2
        cy = CANVAS_SZ // 2
        R  = RADAR_R
        n  = len(METRICS_ORDER)
        angles = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        color_a = ROLE_COLORS.get(da["player"].get("role", "MID").upper(), ACCENT)
        color_b = ROLE_COLORS.get(db["player"].get("role", "MID").upper(), ACCENT)

        # ── Anéis de grid ────────────────────────────────────────────
        for level in [0.25, 0.50, 0.75, 1.00]:
            pts = []
            for ang in angles:
                pts.extend([cx + R * level * math.cos(ang),
                             cy + R * level * math.sin(ang)])
            outline = BORDER if level == 1.0 else "#1e2630"
            width   = 2 if level == 1.0 else 1
            self._canvas.create_polygon(pts, outline=outline, fill="", width=width)

        # Marcadores de %
        for level in [0.25, 0.50, 0.75, 1.00]:
            lx = cx + R * level * math.cos(angles[0]) - 16
            ly = cy + R * level * math.sin(angles[0]) - 8
            self._canvas.create_text(lx, ly, text=f"{int(level * 100)}%",
                                     font=("Segoe UI", 7), fill=TEXT_DIM)

        # ── Eixos radiais ─────────────────────────────────────────────
        for ang in angles:
            self._canvas.create_line(cx, cy,
                                     cx + R * math.cos(ang), cy + R * math.sin(ang),
                                     fill="#263040", width=1)

        # ── Polígono B (tracejado, atrás) ─────────────────────────────
        norm_b = db.get("norm", {})
        pts_b = []
        for i, metric in enumerate(METRICS_ORDER):
            v = min(norm_b.get(metric, 0.0), 1.2)
            pts_b.extend([cx + R * v * math.cos(angles[i]),
                          cy + R * v * math.sin(angles[i])])
        fill_b = _blend_color(color_b, BG_DARKEST, 0.20)
        self._canvas.create_polygon(pts_b, fill=fill_b, outline=color_b,
                                    width=2, dash=(6, 3))

        # ── Polígono A (sólido, frente) ───────────────────────────────
        norm_a = da.get("norm", {})
        pts_a = []
        for i, metric in enumerate(METRICS_ORDER):
            v = min(norm_a.get(metric, 0.0), 1.2)
            pts_a.extend([cx + R * v * math.cos(angles[i]),
                          cy + R * v * math.sin(angles[i])])
        fill_a = _blend_color(color_a, BG_DARKEST, 0.25)
        self._canvas.create_polygon(pts_a, fill=fill_a, outline=color_a, width=2)

        # ── Pontos A ──────────────────────────────────────────────────
        for i, metric in enumerate(METRICS_ORDER):
            v  = norm_a.get(metric, 0.0)
            px = cx + R * v * math.cos(angles[i])
            py = cy + R * v * math.sin(angles[i])
            self._canvas.create_oval(px - 5, py - 5, px + 5, py + 5,
                                     fill=color_a, outline=BG_DARKEST, width=2)

        # ── Pontos B ──────────────────────────────────────────────────
        for i, metric in enumerate(METRICS_ORDER):
            v  = norm_b.get(metric, 0.0)
            px = cx + R * v * math.cos(angles[i])
            py = cy + R * v * math.sin(angles[i])
            self._canvas.create_oval(px - 4, py - 4, px + 4, py + 4,
                                     fill=color_b, outline=BG_DARKEST, width=1)

        # ── Rótulos dos eixos (valores de A) ──────────────────────────
        raw_a = da.get("raw", {})
        label_pad = 38
        for i, metric in enumerate(METRICS_ORDER):
            ang   = angles[i]
            lx    = cx + (R + label_pad) * math.cos(ang)
            ly    = cy + (R + label_pad) * math.sin(ang)
            label = METRICS_LABELS[metric]
            raw   = raw_a.get(metric, 0.0)
            _, val_str = _format_metric(metric, raw, 0)
            self._canvas.create_text(lx, ly,
                                     text=f"{label}\n{val_str}",
                                     font=("Segoe UI", 8, "bold"),
                                     fill=TEXT_COLOR,
                                     justify="center",
                                     anchor=_label_anchor(ang))

    def _build_legend(self, da: dict, db: dict):
        color_a = ROLE_COLORS.get(da["player"].get("role", "MID").upper(), ACCENT)
        color_b = ROLE_COLORS.get(db["player"].get("role", "MID").upper(), ACCENT)
        name_a  = da["player"].get("display", "A")
        name_b  = db["player"].get("display", "B")

        for color, label, style in [
            (color_a, f"{name_a}  ({da['n_games']}p)", "bold"),
            (color_b, f"{name_b}  ({db['n_games']}p)", "normal"),
        ]:
            tk.Label(self._legend_frame, text="━━",
                     font=("Segoe UI", 9, "bold"),
                     bg=BG_DARKEST, fg=color).pack(side=tk.LEFT, padx=(6, 2))
            tk.Label(self._legend_frame, text=label,
                     font=("Segoe UI", 8, style),
                     bg=BG_DARKEST, fg=TEXT_DIM).pack(side=tk.LEFT, padx=(0, 14))

    def _build_stats_panel(self, panel: tk.Frame, data: dict, color: str,
                           opponent: dict):
        """Painel de métricas de um jogador com indicadores vs adversário."""
        player  = data["player"]
        name    = player.get("display", player.get("game_name", "?"))
        role    = player.get("role", "MID").upper()
        n_games = data.get("n_games", 0)
        raw     = data.get("raw", {})
        norm    = data.get("norm", {})
        opp_raw = opponent.get("raw", {})
        bench   = ROLE_BENCHMARKS.get(role, DEFAULT_BENCHMARK)

        # Cabeçalho do painel
        hdr = tk.Frame(panel, bg=BG_MEDIUM)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f" {role[:3]} ",
                 font=("Segoe UI", 8, "bold"),
                 bg=color, fg=BG_DARKEST).pack(side=tk.LEFT, padx=4, pady=5)
        tk.Label(hdr, text=name,
                 font=("Segoe UI", 10, "bold"),
                 bg=BG_MEDIUM, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=4)
        tk.Label(hdr, text=f"{n_games}p",
                 font=("Segoe UI", 8),
                 bg=BG_MEDIUM, fg=TEXT_DIM).pack(side=tk.RIGHT, padx=6)

        # Linha por métrica
        for metric in METRICS_ORDER:
            r       = raw.get(metric, 0.0)
            n       = norm.get(metric, 0.0)
            opp_r   = opp_raw.get(metric, 0.0)
            ref     = bench.get(metric, 1.0)
            label   = METRICS_LABELS[metric]
            icon    = METRICS_ICONS[metric]

            val_str, _ = _format_metric(metric, r, ref)
            opp_str, _ = _format_metric(metric, opp_r, ref)

            pct   = min(max(n, 0.0), 1.0)
            bar_c = SUCCESS if n >= 0.85 else (WARNING if n >= 0.60 else DANGER)
            better = r >= opp_r
            delta_c = SUCCESS if better else DANGER
            delta_sym = "▲" if better else "▼"

            row = tk.Frame(panel, bg=BG_MEDIUM)
            row.pack(fill=tk.X, padx=4, pady=2)

            top = tk.Frame(row, bg=BG_MEDIUM)
            top.pack(fill=tk.X, padx=5, pady=(5, 0))
            tk.Label(top, text=f"{icon} {label}",
                     font=("Segoe UI", 8, "bold"),
                     bg=BG_MEDIUM, fg=TEXT_COLOR).pack(side=tk.LEFT)
            tk.Label(top, text=val_str,
                     font=("Segoe UI", 9, "bold"),
                     bg=BG_MEDIUM, fg=bar_c).pack(side=tk.RIGHT)

            # Barra de progresso
            bar_bg = tk.Frame(row, bg=BG_LIGHT, height=5)
            bar_bg.pack(fill=tk.X, padx=5, pady=(2, 0))
            bar_bg.update_idletasks()
            if pct > 0:
                tk.Frame(bar_bg, bg=bar_c, height=5).place(
                    relwidth=pct, relheight=1.0, x=0, y=0)

            # Delta vs oponente
            tk.Label(row, text=f"{delta_sym} vs {opp_str}",
                     font=("Segoe UI", 7),
                     bg=BG_MEDIUM, fg=delta_c).pack(anchor="e", padx=5, pady=(0, 3))
