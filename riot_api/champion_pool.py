# -*- coding: utf-8 -*-
"""
ChampionPoolViewer — tabela de estatísticas por campeão para um jogador.

Exibe: ícone, nome do campeão, partidas, WR%, KDA médio, CS/min, Vision/min.
Ordenado por número de partidas (desc). Suporta scroll.
"""

import tkinter as tk
from tkinter import ttk
import threading
from PIL import Image, ImageTk

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

ICON_SIZE   = 28
MATCH_COUNT = 30   # partidas a buscar para o pool

# Larguras das colunas (pixels)
COL_WIDTHS = {
    "icon":    36,
    "champ":  130,
    "games":   52,
    "wr":      64,
    "kda":     64,
    "cs_min":  68,
    "vis_min": 78,
}
TOTAL_W = sum(COL_WIDTHS.values()) + 16   # + padding


class ChampionPoolViewer(tk.Toplevel):
    """
    Janela de champion pool de um jogador.

    Parâmetros
    ----------
    parent : tk widget
    match_api : MatchAPI
    puuid : str — PUUID do jogador
    player_name : str — exibido no título
    map_viz : MapVisualizer — para carregar ícones de campeão
    """

    def __init__(self, parent, match_api, puuid: str,
                 player_name: str, map_viz=None):
        super().__init__(parent)
        self.match_api   = match_api
        self.puuid       = puuid
        self.player_name = player_name
        self.map_viz     = map_viz

        self.title(f"Champion Pool — {player_name}")
        self.configure(bg=BG_DARKEST)
        self.resizable(False, True)

        self._icon_refs: list = []    # evita GC dos PhotoImage
        self._rows_data: list = []    # dados brutos para copiar
        self._closed    = False

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        threading.Thread(target=self._fetch, daemon=True).start()

    # ── UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG_DARK, height=44)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"🏆  {self.player_name}  — Champion Pool",
                 font=("Segoe UI", 12, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=14, pady=10)

        btn_copy = tk.Button(hdr, text="📋 Copiar",
                             font=("Segoe UI", 9),
                             bg=BG_LIGHT, fg=ACCENT,
                             relief=tk.FLAT, cursor="hand2",
                             padx=10, pady=4,
                             command=self._copy_to_clipboard)
        btn_copy.pack(side=tk.RIGHT, padx=10, pady=8)

        # Cabeçalho da tabela
        self._build_header()

        # Área scrollável
        outer = tk.Frame(self, bg=BG_DARKEST)
        outer.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(outer, bg=BG_DARKEST,
                                 highlightthickness=0, width=TOTAL_W)
        sb = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._table_frame = tk.Frame(self._canvas, bg=BG_DARKEST)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._table_frame, anchor="nw"
        )
        self._table_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind scroll de mouse
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<MouseWheel>", self._on_mousewheel)

        # Loading
        self._loading_lbl = tk.Label(
            self._table_frame,
            text="⏳  Carregando partidas…",
            font=("Segoe UI", 10), bg=BG_DARKEST, fg=ACCENT
        )
        self._loading_lbl.pack(pady=20)

        # Rodapé
        foot = tk.Frame(self, bg=BG_DARK, height=26)
        foot.pack(fill=tk.X, side=tk.BOTTOM)
        foot.pack_propagate(False)
        tk.Label(foot,
                 text=f"Últimas {MATCH_COUNT} partidas · ordenado por mais jogado",
                 font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.LEFT, padx=12, pady=4)

        self.geometry(f"{TOTAL_W + 20}x500")

    def _build_header(self):
        hrow = tk.Frame(self, bg=BG_DARK)
        hrow.pack(fill=tk.X, padx=8, pady=(4, 0))
        cols = [
            ("",          COL_WIDTHS["icon"]),
            ("Campeão",   COL_WIDTHS["champ"]),
            ("Jogos",     COL_WIDTHS["games"]),
            ("WR%",       COL_WIDTHS["wr"]),
            ("KDA",       COL_WIDTHS["kda"]),
            ("CS/min",    COL_WIDTHS["cs_min"]),
            ("Vision/min", COL_WIDTHS["vis_min"]),
        ]
        for text, w in cols:
            tk.Label(hrow, text=text,
                     font=("Segoe UI", 8, "bold"),
                     bg=BG_DARK, fg=TEXT_DIM,
                     width=w // 8, anchor="w").pack(side=tk.LEFT)

    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ── Fetch ─────────────────────────────────────────────────────────

    def _fetch(self):
        try:
            match_ids = self.match_api.get_match_ids(self.puuid, count=MATCH_COUNT)
            if not match_ids:
                self.after(0, self._on_no_data)
                return

            stats: dict[str, dict] = {}

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

                champ = p.get("championName", "Unknown")
                if not champ:
                    continue

                if champ not in stats:
                    stats[champ] = {
                        "games": 0, "wins": 0,
                        "kills": 0, "deaths": 0, "assists": 0,
                        "cs": 0.0, "vision": 0.0, "dur_min": 0.0,
                    }

                s = stats[champ]
                s["games"]   += 1
                if p.get("win"):
                    s["wins"] += 1
                s["kills"]   += p.get("kills",   0)
                s["deaths"]  += p.get("deaths",  0)
                s["assists"] += p.get("assists",  0)
                s["cs"]      += (p.get("totalMinionsKilled", 0) +
                                 p.get("neutralMinionsKilled", 0))
                s["vision"]  += p.get("visionScore", 0)
                s["dur_min"] += dur_min

            rows = []
            for champ, s in sorted(stats.items(),
                                   key=lambda x: x[1]["games"], reverse=True):
                g  = s["games"]
                wr = round(s["wins"] / g * 100) if g else 0
                kda = (s["kills"] + s["assists"]) / max(s["deaths"], 1)
                dur = max(s["dur_min"], 0.01)
                cs_min  = s["cs"]     / dur
                vis_min = s["vision"] / dur
                rows.append({
                    "champ":   champ,
                    "games":   g,
                    "wr":      wr,
                    "kda":     kda,
                    "cs_min":  cs_min,
                    "vis_min": vis_min,
                })

            self.after(0, self._on_data, rows)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_data(self, rows: list):
        self._loading_lbl.destroy()
        self._rows_data = rows
        if not rows:
            self._on_no_data()
            return
        self._render_rows(rows)

    def _on_no_data(self):
        if self._loading_lbl.winfo_exists():
            self._loading_lbl.config(text="⚠  Nenhuma partida encontrada.", fg=WARNING)
        else:
            tk.Label(self._table_frame,
                     text="⚠  Nenhuma partida encontrada.",
                     font=("Segoe UI", 10), bg=BG_DARKEST, fg=WARNING).pack(pady=8)

    def _on_error(self, msg: str):
        if self._loading_lbl.winfo_exists():
            self._loading_lbl.config(text=f"Erro: {msg}", fg=DANGER)

    # ── Renderização ──────────────────────────────────────────────────

    def _render_rows(self, rows: list):
        for i, row in enumerate(rows):
            bg = BG_DARK if i % 2 == 0 else BG_MEDIUM
            self._render_row(row, bg)
            # Carrega ícone em background
            if self.map_viz:
                threading.Thread(
                    target=self._load_icon,
                    args=(row["champ"], i),
                    daemon=True
                ).start()

    def _render_row(self, row: dict, bg: str) -> tk.Frame:
        frame = tk.Frame(self._table_frame, bg=bg)
        frame.pack(fill=tk.X, padx=4, pady=1)
        frame.row_data = row   # para referência futura do ícone

        # Slot para ícone
        icon_lbl = tk.Label(frame, bg=bg,
                            width=COL_WIDTHS["icon"] // 8)
        icon_lbl.pack(side=tk.LEFT, padx=(4, 2))
        frame.icon_lbl = icon_lbl

        # Campeão
        tk.Label(frame, text=row["champ"],
                 font=("Segoe UI", 9, "bold"),
                 bg=bg, fg=TEXT_BRIGHT,
                 width=COL_WIDTHS["champ"] // 8, anchor="w"
                 ).pack(side=tk.LEFT)

        # Jogos
        tk.Label(frame,
                 text=str(row["games"]),
                 font=("Segoe UI", 9),
                 bg=bg, fg=TEXT_COLOR,
                 width=COL_WIDTHS["games"] // 8, anchor="w"
                 ).pack(side=tk.LEFT)

        # WR%
        wr_fg = SUCCESS if row["wr"] >= 50 else DANGER
        tk.Label(frame,
                 text=f"{row['wr']}%",
                 font=("Segoe UI", 9, "bold"),
                 bg=bg, fg=wr_fg,
                 width=COL_WIDTHS["wr"] // 8, anchor="w"
                 ).pack(side=tk.LEFT)

        # KDA
        kda = row["kda"]
        kda_fg = SUCCESS if kda >= 3.0 else (WARNING if kda >= 2.0 else DANGER)
        tk.Label(frame,
                 text=f"{kda:.2f}",
                 font=("Segoe UI", 9),
                 bg=bg, fg=kda_fg,
                 width=COL_WIDTHS["kda"] // 8, anchor="w"
                 ).pack(side=tk.LEFT)

        # CS/min
        tk.Label(frame,
                 text=f"{row['cs_min']:.1f}",
                 font=("Segoe UI", 9),
                 bg=bg, fg=TEXT_COLOR,
                 width=COL_WIDTHS["cs_min"] // 8, anchor="w"
                 ).pack(side=tk.LEFT)

        # Vision/min
        tk.Label(frame,
                 text=f"{row['vis_min']:.2f}",
                 font=("Segoe UI", 9),
                 bg=bg, fg=TEXT_DIM,
                 width=COL_WIDTHS["vis_min"] // 8, anchor="w"
                 ).pack(side=tk.LEFT)

        return frame

    def _on_close(self):
        self._closed = True
        self.destroy()

    def _load_icon(self, champion_name: str, row_index: int):
        if self._closed:
            return
        try:
            img = self.map_viz._download_champion_icon(champion_name)
            if img is None or self._closed:
                return
            img_small = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img_small)

            # Encontra o frame correspondente na UI
            children = self._table_frame.winfo_children()
            if row_index < len(children):
                frame = children[row_index]
                icon_lbl = getattr(frame, "icon_lbl", None)
                if icon_lbl and icon_lbl.winfo_exists() and not self._closed:
                    self.after(0, self._set_icon, icon_lbl, photo)
        except Exception:
            pass

    def _set_icon(self, lbl: tk.Label, photo):
        self._icon_refs.append(photo)   # evita GC
        lbl.config(image=photo)
        lbl.image = photo

    # ── Exportação ────────────────────────────────────────────────────

    def _copy_to_clipboard(self):
        if not self._rows_data:
            return
        header = "Campeão\tJogos\tWR%\tKDA\tCS/min\tVision/min"
        lines  = [header]
        for r in self._rows_data:
            lines.append(
                f"{r['champ']}\t{r['games']}\t{r['wr']}%\t"
                f"{r['kda']:.2f}\t{r['cs_min']:.1f}\t{r['vis_min']:.2f}"
            )
        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
