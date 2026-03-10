# -*- coding: utf-8 -*-
"""
GoldDiffViewer — gráfico de diferença de ouro/XP por lane ao longo do tempo.

Funcionalidades:
  • Animação de desenho ao abrir ou trocar métrica (ease-out cubic)
  • Hover com crosshair + tooltip mostrando valores de todas as lanes
  • Checkboxes por lane com transição suave (fade via stipple progressivo)
  • Toggle Ouro / XP com re-animação
"""

import tkinter as tk
from tkinter import ttk

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

BLUE_COLOR  = "#4488FF"
RED_COLOR   = "#FF4840"

LANE_COLORS = {
    "TOP":     "#e5534b",
    "JUNGLE":  "#50FF50",
    "MIDDLE":  "#FF9830",
    "BOTTOM":  "#FFCC50",
    "UTILITY": "#20F0FF",
}
LANE_LABELS = {
    "TOP":     "TOP",
    "JUNGLE":  "JGL",
    "MIDDLE":  "MID",
    "BOTTOM":  "ADC",
    "UTILITY": "SUP",
}

CHART_W    = 680
CHART_H    = 360
PAD_LEFT   = 60
PAD_RIGHT  = 70
PAD_TOP    = 24
PAD_BOTTOM = 44

ANIM_STEPS = 45          # frames de animação (~720 ms a 16ms/frame)
ANIM_MS    = 16          # intervalo entre frames

MODES = ["Ouro", "XP"]
FRAME_KEY = {"Ouro": "totalGold", "XP": "xp"}

# Stipple progressivo para fade-in/out de lanes
STIPPLES = ["gray75", "gray50", "gray25", "gray12", ""]   # "" = sólido


class GoldDiffViewer(tk.Toplevel):
    """
    Parâmetros
    ----------
    parent     : tk widget
    match_data : dict  — dados completos da partida (Riot API)
    timeline   : dict  — timeline completa da partida
    puuid      : str   — PUUID do jogador rastreado
    """

    def __init__(self, parent, match_data: dict, timeline: dict, puuid: str = ""):
        super().__init__(parent)
        self.match_data = match_data
        self.timeline   = timeline
        self.puuid      = puuid

        self._mode_var  = tk.StringVar(value="Ouro")
        self._lanes: list[str] = []
        self._series:  dict[str, list] = {}
        self._my_lane: str | None = None
        self._visible: dict[str, tk.BooleanVar] = {}

        # Estado de animação
        self._anim_id:       str | None = None
        self._anim_progress: int = 0
        self._anim_total:    int = 1

        # Estado de hover
        self._hover_items:   list = []   # IDs de canvas a limpar a cada frame

        self.title("VisionLOL — Diff por Lane")
        self.configure(bg=BG_DARKEST)
        self.resizable(False, False)

        self._build_series()
        self._build_ui()
        self._start_animation()

    # ─────────────────────────────────────────────────────────────────
    #  DADOS
    # ─────────────────────────────────────────────────────────────────

    def _build_series(self):
        """Extrai séries de gold/XP diff por lane a partir da timeline."""
        self._series.clear()
        info         = self.match_data.get("info", {})
        participants = info.get("participants", [])

        pid_lane:  dict[int, str] = {}
        pid_team:  dict[int, int] = {}
        pid_puuid: dict[int, str] = {}

        for p in participants:
            pid  = p.get("participantId", 0)
            pid_lane[pid]  = p.get("teamPosition", "")
            pid_team[pid]  = p.get("teamId", 0)
            pid_puuid[pid] = p.get("puuid", "")

        for pid, pu in pid_puuid.items():
            if pu == self.puuid:
                self._my_lane = pid_lane.get(pid)
                break

        lane_pids: dict[str, dict] = {}
        for pid, lane in pid_lane.items():
            if not lane:
                continue
            lane_pids.setdefault(lane, {})
            key = "blue" if pid_team[pid] == 100 else "red"
            lane_pids[lane][key] = pid

        frames = self.timeline.get("info", {}).get("frames", [])
        metric = FRAME_KEY[self._mode_var.get()]

        for lane, sides in lane_pids.items():
            b, r = sides.get("blue"), sides.get("red")
            if b is None or r is None:
                continue
            series = []
            for frame in frames:
                pf = frame.get("participantFrames", {})
                bv = pf.get(str(b), {}).get(metric, 0)
                rv = pf.get(str(r), {}).get(metric, 0)
                series.append(bv - rv)
            self._series[lane] = series

        order = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        self._lanes = [l for l in order if l in self._series]

        for lane in self._lanes:
            if lane not in self._visible:
                self._visible[lane] = tk.BooleanVar(value=True)

    # ─────────────────────────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ───────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, height=48)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="📈  Diferença por Lane",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=14, pady=10)

        mode_frame = tk.Frame(hdr, bg=BG_DARK)
        mode_frame.pack(side=tk.RIGHT, padx=14, pady=8)
        tk.Label(mode_frame, text="Métrica:",
                 font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.LEFT, padx=(0, 6))
        for m in MODES:
            rb = tk.Radiobutton(mode_frame, text=m, variable=self._mode_var, value=m,
                                font=("Segoe UI", 9, "bold"),
                                bg=BG_DARK, fg=ACCENT,
                                selectcolor=BG_MEDIUM,
                                activebackground=BG_DARK, activeforeground=ACCENT,
                                cursor="hand2",
                                command=self._on_mode_change)
            rb.pack(side=tk.LEFT, padx=5)

        # ── Subtítulo ─────────────────────────────────────────────────
        sub = tk.Frame(self, bg=BG_DARKEST)
        sub.pack(fill=tk.X, padx=14, pady=(4, 0))
        tk.Label(sub, text="▲ acima do zero = Time Azul ganhando",
                 font=("Segoe UI", 8), bg=BG_DARKEST, fg=BLUE_COLOR
                 ).pack(side=tk.LEFT)
        tk.Label(sub, text="   ▼ abaixo = Time Vermelho",
                 font=("Segoe UI", 8), bg=BG_DARKEST, fg=RED_COLOR
                 ).pack(side=tk.LEFT)

        # ── Canvas ────────────────────────────────────────────────────
        cf = tk.Frame(self, bg=BG_DARKEST)
        cf.pack(padx=12, pady=6)
        self._canvas = tk.Canvas(cf, width=CHART_W, height=CHART_H,
                                 bg=BG_DARKEST,
                                 highlightthickness=1, highlightbackground=BORDER)
        self._canvas.pack()
        self._canvas.bind("<Motion>",  self._on_hover)
        self._canvas.bind("<Leave>",   self._on_leave)

        # ── Legenda / checkboxes ───────────────────────────────────────
        legend = tk.Frame(self, bg=BG_DARKEST)
        legend.pack(pady=(0, 10))

        self._cb_widgets: dict[str, tk.Checkbutton] = {}
        for lane in self._lanes:
            color = LANE_COLORS.get(lane, ACCENT)
            lbl   = LANE_LABELS.get(lane, lane[:3])
            cb = tk.Checkbutton(legend,
                                text=f"  {lbl}  ",
                                variable=self._visible[lane],
                                font=("Segoe UI", 10, "bold"),
                                bg=BG_DARKEST, fg=color,
                                selectcolor=BG_MEDIUM,
                                activebackground=BG_DARKEST, activeforeground=color,
                                cursor="hand2",
                                command=lambda l=lane: self._on_toggle(l))
            cb.pack(side=tk.LEFT, padx=8)
            self._cb_widgets[lane] = cb

            # Sublinha colorida nos checkboxes
            tk.Frame(legend, bg=color, height=2, width=30
                     ).pack(side=tk.LEFT, padx=(0, 4))

        self.geometry(f"{CHART_W + 30}x{CHART_H + 152}")

    # ─────────────────────────────────────────────────────────────────
    #  ANIMAÇÃO
    # ─────────────────────────────────────────────────────────────────

    def _start_animation(self):
        """Inicia/reinicia a animação de desenho das linhas."""
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None
        self._anim_progress = 0
        self._anim_total = max((len(s) for s in self._series.values()), default=1)
        self._animate_step()

    def _animate_step(self):
        self._anim_progress += 1
        frac = min(self._anim_progress / ANIM_STEPS, 1.0)
        # Easing ease-out cubic
        frac = 1.0 - (1.0 - frac) ** 3
        n_limit = max(2, int(frac * self._anim_total))
        self._draw_chart(n_limit=n_limit)

        if self._anim_progress < ANIM_STEPS:
            self._anim_id = self.after(ANIM_MS, self._animate_step)
        else:
            self._anim_id = None
            self._draw_chart()   # frame final completo

    def _on_mode_change(self):
        self._build_series()
        self._start_animation()

    def _on_toggle(self, lane: str):
        """Trigger re-animação parcial ao alternar visibilidade de lane."""
        self._start_animation()

    # ─────────────────────────────────────────────────────────────────
    #  HOVER
    # ─────────────────────────────────────────────────────────────────

    def _on_hover(self, event):
        """Exibe crosshair e tooltip ao passar o mouse sobre o gráfico."""
        x0 = PAD_LEFT
        x1 = CHART_W - PAD_RIGHT
        y0 = PAD_TOP
        y1 = CHART_H - PAD_BOTTOM

        mx = event.x
        if not (x0 <= mx <= x1):
            self._clear_hover()
            return

        n_frames = max((len(s) for s in self._series.values()), default=0)
        if n_frames < 2:
            return

        # Índice do frame mais próximo
        frac  = (mx - x0) / (x1 - x0)
        idx   = min(int(frac * (n_frames - 1) + 0.5), n_frames - 1)
        t_min = idx

        plot_h = y1 - y0
        y_max  = self._current_y_max()

        def to_py(val: float) -> float:
            """Valor → pixel Y."""
            return y1 - ((val + y_max) / (2 * y_max)) * plot_h

        # Posição X real do frame
        px = x0 + (idx / (n_frames - 1)) * (x1 - x0)

        # Limpa overlay anterior
        self._clear_hover()

        # Linha vertical
        self._hover_items.append(
            self._canvas.create_line(px, y0, px, y1,
                                     fill=TEXT_DIM, width=1, dash=(3, 3))
        )

        # Bolinha + label por lane
        for lane in self._lanes:
            if not self._visible[lane].get():
                continue
            series = self._series.get(lane, [])
            if idx >= len(series):
                continue
            val   = series[idx]
            py    = to_py(val)
            color = LANE_COLORS.get(lane, ACCENT)
            lbl   = LANE_LABELS.get(lane, lane[:3])

            # Círculo na intersecção
            r = 5
            self._hover_items.append(
                self._canvas.create_oval(px - r, py - r, px + r, py + r,
                                         fill=color, outline=BG_DARKEST, width=2)
            )

            # Tooltip box
            mode  = self._mode_var.get()
            if mode == "Ouro":
                val_str = f"{val/1000:+.1f}k" if abs(val) >= 500 else f"{int(val):+d}"
            else:
                val_str = f"{int(val):+d} XP"

            tip_text = f"{lbl}: {val_str}"
            tip_x    = px + 8 if px < x1 - 80 else px - 8
            anchor   = "nw" if px < x1 - 80 else "ne"

            # Fundo da label
            txt_id = self._canvas.create_text(
                tip_x, py, text=tip_text,
                font=("Segoe UI", 8, "bold"),
                fill=color, anchor=anchor
            )
            bbox = self._canvas.bbox(txt_id)
            if bbox:
                pad = 2
                bg_id = self._canvas.create_rectangle(
                    bbox[0] - pad, bbox[1] - pad,
                    bbox[2] + pad, bbox[3] + pad,
                    fill=BG_DARKEST, outline="", width=0
                )
                self._canvas.tag_lower(bg_id, txt_id)
                self._hover_items.extend([bg_id, txt_id])
            else:
                self._hover_items.append(txt_id)

        # Rótulo do minuto
        self._hover_items.append(
            self._canvas.create_text(px, y1 + 6, text=f"{t_min}m",
                                     font=("Segoe UI", 8, "bold"),
                                     fill=TEXT_BRIGHT, anchor="n")
        )

    def _on_leave(self, event):
        self._clear_hover()

    def _clear_hover(self):
        for item in self._hover_items:
            try:
                self._canvas.delete(item)
            except Exception:
                pass
        self._hover_items.clear()

    def _current_y_max(self) -> float:
        """Valor máximo absoluto entre as lanes visíveis."""
        all_vals = []
        for lane in self._lanes:
            if self._visible[lane].get():
                all_vals.extend(self._series.get(lane, []))
        y_max = max((abs(v) for v in all_vals), default=1000)
        return max(y_max * 1.10, 500)

    # ─────────────────────────────────────────────────────────────────
    #  RENDERIZAÇÃO
    # ─────────────────────────────────────────────────────────────────

    def _draw_chart(self, n_limit: int | None = None):
        """Renderiza o gráfico completo ou até n_limit pontos (para animação)."""
        # Preserva hover items — apenas apaga o fundo do gráfico
        hover_set = set(self._hover_items)
        all_items = self._canvas.find_all()
        for item in all_items:
            if item not in hover_set:
                self._canvas.delete(item)

        if not self._series:
            self._canvas.create_text(CHART_W // 2, CHART_H // 2,
                                     text="Sem dados de timeline disponíveis.",
                                     fill=TEXT_DIM, font=("Segoe UI", 11))
            return

        n_frames = max((len(s) for s in self._series.values()), default=0)
        if n_frames < 2:
            self._canvas.create_text(CHART_W // 2, CHART_H // 2,
                                     text="Dados insuficientes.",
                                     fill=TEXT_DIM, font=("Segoe UI", 10))
            return

        n_draw  = n_limit if n_limit is not None else n_frames
        n_draw  = min(n_draw, n_frames)

        x0      = PAD_LEFT
        x1      = CHART_W - PAD_RIGHT
        y0      = PAD_TOP
        y1      = CHART_H - PAD_BOTTOM
        plot_w  = x1 - x0
        plot_h  = y1 - y0
        y_max   = self._current_y_max()

        def to_px(i: int, val: float) -> tuple[float, float]:
            total = n_frames - 1
            xp = x0 + (i / total) * plot_w
            yp = y1 - ((val + y_max) / (2 * y_max)) * plot_h
            return xp, yp

        # ── Grid horizontal ──────────────────────────────────────────
        grid_fracs = [-0.75, -0.50, -0.25, 0.0, 0.25, 0.50, 0.75]
        for frac in grid_fracs:
            val = y_max * frac
            _, yp = to_px(0, val)
            if not (y0 - 1 <= yp <= y1 + 1):
                continue
            is_zero = frac == 0.0
            color   = TEXT_DIM   if is_zero else BORDER
            width   = 1
            dash    = ()         if is_zero else (4, 6)
            self._canvas.create_line(x0, yp, x1, yp,
                                     fill=color, width=width, dash=dash)

            mode = self._mode_var.get()
            if mode == "Ouro":
                lbl = f"{val/1000:+.1f}k" if abs(val) >= 500 else f"{int(val):+d}"
            else:
                lbl = f"{int(val):+d}"
            self._canvas.create_text(x0 - 6, yp, text=lbl,
                                     font=("Segoe UI", 7),
                                     fill=TEXT_COLOR if is_zero else TEXT_DIM,
                                     anchor="e")

        # ── Grid vertical ─────────────────────────────────────────────
        tick_step = max(1, round(n_frames / 8))
        for i in range(0, n_frames, tick_step):
            xp, _ = to_px(i, 0)
            self._canvas.create_line(xp, y0, xp, y1,
                                     fill=BORDER, width=1, dash=(3, 7))
            self._canvas.create_text(xp, y1 + 6, text=f"{i}m",
                                     font=("Segoe UI", 7), fill=TEXT_DIM, anchor="n")

        # Borda
        self._canvas.create_rectangle(x0, y0, x1, y1, outline=BORDER, width=1)

        # Rótulos de eixo
        self._canvas.create_text((x0 + x1) // 2, CHART_H - 4,
                                 text="Tempo (minutos)", font=("Segoe UI", 8),
                                 fill=TEXT_DIM, anchor="s")
        mode_lbl = "Ouro Diff" if self._mode_var.get() == "Ouro" else "XP Diff"
        self._canvas.create_text(10, (y0 + y1) // 2,
                                 text=mode_lbl, font=("Segoe UI", 8),
                                 fill=TEXT_DIM, angle=90, anchor="center")

        # ── Linhas das lanes ─────────────────────────────────────────
        for lane in self._lanes:
            if not self._visible[lane].get():
                continue

            series = self._series[lane][:n_draw]
            color  = LANE_COLORS.get(lane, ACCENT)
            is_my  = (lane == self._my_lane)
            width  = 3 if is_my else 2

            pts     = []
            fill_p  = []
            for i, val in enumerate(series):
                xp, yp = to_px(i, val)
                pts.extend([xp, yp])
                fill_p.append((xp, yp))

            if len(fill_p) < 2:
                continue

            # Preenchimento (área entre linha e zero)
            _, zero_y = to_px(0, 0.0)
            poly = []
            for xp, yp in fill_p:
                poly.extend([xp, yp])
            poly.extend([fill_p[-1][0], zero_y, fill_p[0][0], zero_y])

            stipple = "gray25" if is_my else "gray12"
            self._canvas.create_polygon(poly, fill=color,
                                        outline="", stipple=stipple)

            # Linha principal
            self._canvas.create_line(pts, fill=color, width=width,
                                     smooth=True,
                                     joinstyle=tk.ROUND,
                                     capstyle=tk.ROUND)

            # Rótulo final (só no último frame da animação)
            if n_draw >= n_frames and fill_p:
                lx, ly = fill_p[-1]
                lbl    = LANE_LABELS.get(lane, lane[:3])
                val    = series[-1]
                sign   = "▲" if val >= 0 else "▼"
                font   = ("Segoe UI", 8, "bold") if is_my else ("Segoe UI", 8)
                self._canvas.create_text(lx + 7, ly,
                                         text=f"{lbl} {sign}",
                                         font=font, fill=color, anchor="w")

        # ── Pontos de destaque na lane do jogador ─────────────────────
        if n_draw >= n_frames and self._my_lane and self._my_lane in self._series:
            if self._visible.get(self._my_lane, tk.BooleanVar(value=True)).get():
                s = self._series[self._my_lane]
                c = LANE_COLORS.get(self._my_lane, ACCENT)
                for i in range(0, len(s), 5):
                    xp, yp = to_px(i, s[i])
                    r = 4
                    self._canvas.create_oval(xp - r, yp - r, xp + r, yp + r,
                                             fill=c, outline=BG_DARKEST, width=1)
