# -*- coding: utf-8 -*-
"""
EvolutionViewer — gráfico de linha mostrando a evolução temporal de KDA,
CS/min e Vision/min de um jogador ao longo das últimas partidas.

Desenhado em puro tkinter Canvas (sem matplotlib).
"""

import tkinter as tk
import threading
import math

from .performance_radar import ROLE_BENCHMARKS, ROLE_COLORS

# ═══════════════════════════════════════════════════════════════════════
#  PALETA  (alinhada com o restante do projeto)
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

TEXT_BRIGHT = "#ffffff"
TEXT_COLOR  = "#e6edf3"
TEXT_DIM    = "#7d8590"

# Cores e rótulos das séries
SERIES = {
    "kda":          {"color": ACCENT,   "label": "KDA",        "fmt": "{:.2f}"},
    "cs_per_min":   {"color": SUCCESS,  "label": "CS/min",     "fmt": "{:.1f}"},
    "vision_per_min": {"color": WARNING, "label": "Vision/min", "fmt": "{:.2f}"},
}

MATCH_COUNT = 20   # partidas a buscar

# Dimensões do canvas
CANVAS_W = 600
CANVAS_H = 300
PAD_LEFT   = 60
PAD_RIGHT  = 24
PAD_TOP    = 32
PAD_BOTTOM = 48


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _blend(hex_color: str, bg: str = BG_MEDIUM, alpha: float = 0.25) -> str:
    """Mistura hex_color com bg na proporção alpha."""
    r1, g1, b1 = _hex_to_rgb(hex_color)
    r2, g2, b2 = _hex_to_rgb(bg)
    r = int(r1 * alpha + r2 * (1 - alpha))
    g = int(g1 * alpha + g2 * (1 - alpha))
    b = int(b1 * alpha + b2 * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


class EvolutionViewer(tk.Toplevel):
    """
    Janela de evolução temporal de um jogador.

    Parâmetros
    ----------
    parent : tk widget
    match_api : MatchAPI — instância para buscar dados
    puuid : str — PUUID do jogador
    player_name : str — nome exibido no título
    role : str — role (TOP/JUNGLE/MID/ADC/SUPPORT)
    """

    def __init__(self, parent, match_api, puuid: str,
                 player_name: str, role: str = "MID"):
        super().__init__(parent)
        self.match_api   = match_api
        self.puuid       = puuid
        self.player_name = player_name
        self.role        = role.upper()

        self.title(f"Evolução Temporal — {player_name}")
        self.configure(bg=BG_DARKEST)
        self.resizable(False, False)

        # Série selecionada (começa com todas visíveis)
        self._active_series = set(SERIES.keys())

        # Dados carregados
        self._points: list[dict] = []   # lista de dicts com kda, cs_per_min, vision_per_min, champion, win
        self._tooltip_win: tk.Toplevel | None = None

        self._build_ui()

        threading.Thread(target=self._fetch, daemon=True).start()

    # ── UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG_DARK, height=44)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        role_color = ROLE_COLORS.get(self.role, ACCENT)
        tk.Label(hdr, text=f"📈  {self.player_name}  — Evolução Temporal",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=14, pady=10)
        tk.Label(hdr, text=self.role,
                 font=("Segoe UI", 9, "bold"),
                 bg=role_color, fg=TEXT_BRIGHT,
                 padx=6, pady=2).pack(side=tk.LEFT, pady=12)

        # Seletor de séries
        ctrl = tk.Frame(self, bg=BG_DARKEST, pady=6)
        ctrl.pack(fill=tk.X, padx=14)
        tk.Label(ctrl, text="Exibir:", font=("Segoe UI", 9),
                 bg=BG_DARKEST, fg=TEXT_DIM).pack(side=tk.LEFT, padx=(0, 8))
        self._toggle_btns = {}
        for key, info in SERIES.items():
            btn = tk.Button(
                ctrl, text=info["label"],
                font=("Segoe UI", 9, "bold"),
                bg=info["color"], fg=TEXT_BRIGHT,
                relief=tk.FLAT, cursor="hand2", padx=10, pady=3,
                command=lambda k=key: self._toggle_series(k),
            )
            btn.pack(side=tk.LEFT, padx=3)
            self._toggle_btns[key] = btn

        # Canvas do gráfico
        self._canvas = tk.Canvas(
            self, width=CANVAS_W, height=CANVAS_H,
            bg=BG_MEDIUM, highlightthickness=1,
            highlightbackground=BORDER
        )
        self._canvas.pack(padx=14, pady=(4, 6))
        self._canvas.bind("<Motion>",   self._on_mouse_move)
        self._canvas.bind("<Leave>",    self._on_mouse_leave)

        # Loading label
        self._loading_lbl = tk.Label(
            self, text="⏳  Carregando partidas…",
            font=("Segoe UI", 10), bg=BG_DARKEST, fg=ACCENT
        )
        self._loading_lbl.pack(pady=4)

        # Rodapé com legenda
        foot = tk.Frame(self, bg=BG_DARK, height=28)
        foot.pack(fill=tk.X, side=tk.BOTTOM)
        foot.pack_propagate(False)
        tk.Label(foot,
                 text=f"Últimas {MATCH_COUNT} partidas · linha tracejada = benchmark de role",
                 font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.LEFT, padx=12, pady=6)

    # ── Fetch ─────────────────────────────────────────────────────────

    def _fetch(self):
        try:
            match_ids = self.match_api.get_match_ids(self.puuid, count=MATCH_COUNT)
            if not match_ids:
                self.after(0, self._on_no_data)
                return

            points = []
            for mid in match_ids:
                data = self.match_api.get_match_data(mid)
                if not data:
                    continue
                p = self.match_api.get_participant_by_puuid(data, self.puuid)
                if not p:
                    continue
                duration = data.get("info", {}).get("gameDuration", 0)
                if duration < 60:
                    continue
                dur_min = duration / 60.0

                kills    = p.get("kills",    0)
                deaths   = p.get("deaths",   1)
                assists  = p.get("assists",  0)
                cs       = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
                vision   = p.get("visionScore", 0)

                points.append({
                    "kda":             (kills + assists) / max(deaths, 1),
                    "cs_per_min":      cs / dur_min,
                    "vision_per_min":  vision / dur_min,
                    "champion":        p.get("championName", ""),
                    "win":             p.get("win", False),
                    "kda_str":         f"{kills}/{deaths}/{assists}",
                    "match_id":        mid,
                })

            # Ordena do mais antigo ao mais recente
            points.reverse()
            self.after(0, self._on_data, points)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_data(self, points: list):
        self._loading_lbl.destroy()
        self._points = points
        if not points:
            self._on_no_data()
            return
        self._draw()

    def _on_no_data(self):
        if self._loading_lbl.winfo_exists():
            self._loading_lbl.config(text="⚠  Nenhuma partida encontrada.", fg=WARNING)
        else:
            tk.Label(self, text="⚠  Nenhuma partida encontrada.",
                     font=("Segoe UI", 10), bg=BG_DARKEST, fg=WARNING).pack(pady=8)

    def _on_error(self, msg: str):
        if self._loading_lbl.winfo_exists():
            self._loading_lbl.config(text=f"Erro: {msg}", fg=DANGER)

    # ── Desenho ───────────────────────────────────────────────────────

    def _toggle_series(self, key: str):
        if key in self._active_series:
            if len(self._active_series) == 1:
                return  # pelo menos 1 série visível
            self._active_series.discard(key)
            self._toggle_btns[key].config(bg=BG_LIGHT, fg=TEXT_DIM)
        else:
            self._active_series.add(key)
            self._toggle_btns[key].config(bg=SERIES[key]["color"], fg=TEXT_BRIGHT)
        self._draw()

    def _draw(self):
        cv = self._canvas
        cv.delete("all")
        pts = self._points
        if not pts:
            return

        n = len(pts)
        plot_w = CANVAS_W - PAD_LEFT - PAD_RIGHT
        plot_h = CANVAS_H - PAD_TOP  - PAD_BOTTOM

        # Grades de fundo
        cv.create_rectangle(PAD_LEFT, PAD_TOP,
                             PAD_LEFT + plot_w, PAD_TOP + plot_h,
                             fill=BG_DARK, outline=BORDER)

        grid_lines = 4
        for i in range(1, grid_lines):
            y = PAD_TOP + plot_h * i // grid_lines
            cv.create_line(PAD_LEFT, y, PAD_LEFT + plot_w, y,
                           fill=BORDER, dash=(4, 4))

        for i in range(n):
            x = PAD_LEFT + plot_w * i / max(n - 1, 1)
            cv.create_line(x, PAD_TOP, x, PAD_TOP + plot_h,
                           fill=BORDER, dash=(2, 6))

        # Rótulos do eixo X (a cada 5 partidas)
        for i, pt in enumerate(pts):
            if i % 5 == 0 or i == n - 1:
                x = PAD_LEFT + plot_w * i / max(n - 1, 1)
                cv.create_text(x, PAD_TOP + plot_h + 14,
                               text=str(i + 1),
                               font=("Segoe UI", 7), fill=TEXT_DIM, anchor="n")

        # Desenha cada série activa
        benchmarks = ROLE_BENCHMARKS.get(self.role, {})

        for key, info in SERIES.items():
            if key not in self._active_series:
                continue

            values = [pt[key] for pt in pts]
            vmin = min(values)
            vmax = max(values)
            span = max(vmax - vmin, 0.001)
            pad_v = span * 0.15
            lo = vmin - pad_v
            hi = vmax + pad_v

            # Benchmark como linha tracejada
            bench = benchmarks.get(
                "cs_per_min" if key == "cs_per_min" else
                "vision_pm"  if key == "vision_per_min" else
                "kda",
                None
            )
            if bench is not None:
                by = PAD_TOP + plot_h - plot_h * (bench - lo) / (hi - lo)
                by = max(PAD_TOP, min(PAD_TOP + plot_h, by))
                cv.create_line(PAD_LEFT, by, PAD_LEFT + plot_w, by,
                               fill=info["color"], dash=(6, 4), width=1)

            # Rótulo Y (mín / máx)
            cv.create_text(PAD_LEFT - 4, PAD_TOP,
                           text=info["fmt"].format(hi),
                           font=("Segoe UI", 7), fill=TEXT_DIM, anchor="e")
            cv.create_text(PAD_LEFT - 4, PAD_TOP + plot_h,
                           text=info["fmt"].format(lo),
                           font=("Segoe UI", 7), fill=TEXT_DIM, anchor="e")

            # Coordenadas dos pontos
            coords = []
            for i, v in enumerate(values):
                x = PAD_LEFT + plot_w * i / max(n - 1, 1)
                y = PAD_TOP + plot_h - plot_h * (v - lo) / (hi - lo)
                y = max(PAD_TOP, min(PAD_TOP + plot_h, y))
                coords.append((x, y))

            # Linha de conexão
            if len(coords) >= 2:
                flat = [c for xy in coords for c in xy]
                cv.create_line(*flat, fill=info["color"], width=2, smooth=False)

            # Pontos
            for i, (x, y) in enumerate(coords):
                pt = pts[i]
                win_color = SUCCESS if pt["win"] else DANGER
                cv.create_oval(x - 5, y - 5, x + 5, y + 5,
                               fill=win_color, outline=info["color"], width=2,
                               tags=(f"pt_{key}_{i}",))

        # Legenda no topo direito
        lx = PAD_LEFT + plot_w - 4
        ly = PAD_TOP + 8
        for key, info in SERIES.items():
            if key not in self._active_series:
                continue
            cv.create_line(lx - 24, ly, lx - 8, ly,
                           fill=info["color"], width=2)
            cv.create_text(lx - 28, ly, text=info["label"],
                           font=("Segoe UI", 7), fill=info["color"], anchor="e")
            ly += 14

        # Salva coords para tooltip
        self._coords_cache = {}
        for key in self._active_series:
            values = [pt[key] for pt in pts]
            vmin, vmax = min(values), max(values)
            span = max(vmax - vmin, 0.001)
            pad_v = span * 0.15
            lo, hi = vmin - pad_v, vmax + pad_v
            for i, v in enumerate(values):
                x = PAD_LEFT + plot_w * i / max(n - 1, 1)
                y = PAD_TOP + plot_h - plot_h * (v - lo) / (hi - lo)
                y = max(PAD_TOP, min(PAD_TOP + plot_h, y))
                self._coords_cache.setdefault(i, {})[key] = (x, y, v)

    # ── Tooltip ───────────────────────────────────────────────────────

    def _on_mouse_move(self, event):
        if not self._points:
            return
        n      = len(self._points)
        plot_w = CANVAS_W - PAD_LEFT - PAD_RIGHT
        # Encontra o ponto mais próximo no eixo X
        best_i  = None
        best_dx = float("inf")
        for i in range(n):
            x = PAD_LEFT + plot_w * i / max(n - 1, 1)
            dx = abs(event.x - x)
            if dx < best_dx:
                best_dx = dx
                best_i  = i

        if best_i is None or best_dx > 20:
            self._hide_tooltip()
            return

        pt = self._points[best_i]
        lines = [
            f"Partida {best_i + 1}",
            f"Campeão: {pt['champion']}",
            f"Resultado: {'Vitória' if pt['win'] else 'Derrota'}",
            f"KDA: {pt['kda_str']} ({pt['kda']:.2f})",
            f"CS/min: {pt['cs_per_min']:.1f}",
            f"Vision/min: {pt['vision_per_min']:.2f}",
        ]
        self._show_tooltip(event.x_root + 12, event.y_root - 8, "\n".join(lines))

    def _on_mouse_leave(self, event):
        self._hide_tooltip()

    def _show_tooltip(self, x: int, y: int, text: str):
        if self._tooltip_win and self._tooltip_win.winfo_exists():
            lbl = self._tooltip_win.winfo_children()[0]
            lbl.config(text=text)
            self._tooltip_win.geometry(f"+{x}+{y}")
            return
        win = tk.Toplevel(self)
        win.wm_overrideredirect(True)
        win.geometry(f"+{x}+{y}")
        win.configure(bg=BG_DARK)
        tk.Label(win, text=text,
                 font=("Segoe UI", 9),
                 bg=BG_DARK, fg=TEXT_COLOR,
                 padx=10, pady=6, justify=tk.LEFT,
                 relief=tk.SOLID, bd=1).pack()
        self._tooltip_win = win

    def _hide_tooltip(self):
        if self._tooltip_win and self._tooltip_win.winfo_exists():
            self._tooltip_win.destroy()
        self._tooltip_win = None
