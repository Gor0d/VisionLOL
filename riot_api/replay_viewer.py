# -*- coding: utf-8 -*-
"""
ReplayViewer - Replay animado de partida no minimapa do Summoner's Rift.
Visual design moderno: paleta GitHub Dark, mini-icones, glow, sombras, scrubber.
"""

import tkinter as tk
import time
from PIL import Image, ImageTk, ImageDraw

# ═══════════════════════════════════════════════════════════════════════
#  CONSTANTES DE LAYOUT
# ═══════════════════════════════════════════════════════════════════════
CANVAS_SIZE      = 700
ICON_SIZE        = 30
MINI_ICON_SIZE   = 20        # side panel champion list
MICRO_ICON_SIZE  = 14        # kill feed icons
FRAME_INTERVAL_MS = 33       # ~30fps
HEADER_HEIGHT    = 38
TIMELINE_HEIGHT  = 88
SIDE_PANEL_WIDTH = 285
EVENT_WINDOW_MS  = 5_000
OBJ_WINDOW_MS    = 8_000
KILL_FEED_MAX    = 6
GOLD_GRAPH_W     = 246
GOLD_GRAPH_H     = 55

OBJ_RESPAWN = {
    "DRAGON":       300_000,
    "BARON_NASHOR": 360_000,
    "RIFTHERALD":   360_000,
}

# ═══════════════════════════════════════════════════════════════════════
#  PALETA  (GitHub Dark-inspired, mais profissional)
# ═══════════════════════════════════════════════════════════════════════
BG_DARKEST  = "#0d1117"
BG_DARK     = "#161b22"
BG_MEDIUM   = "#1c2129"
BG_LIGHT    = "#21262d"
BG_HOVER    = "#2d333b"
BORDER      = "#30363d"

ACCENT      = "#58a6ff"
ACCENT_DIM  = "#1a3a5f"
SUCCESS     = "#3fb950"
SUCCESS_DIM = "#0d3318"
DANGER      = "#f85149"
DANGER_DIM  = "#3d1114"
WARNING     = "#d29922"
WARNING_DIM = "#3a2a08"
PURPLE      = "#bc8cff"

TEXT_BRIGHT = "#ffffff"
TEXT_COLOR  = "#e6edf3"
TEXT_DIM    = "#7d8590"

BLUE_TEAM     = "#539bf5"
BLUE_TEAM_DIM = "#162236"
RED_TEAM      = "#e5534b"
RED_TEAM_DIM  = "#2e1212"

# Paletas de glow concêntrico para kills [externo, médio, interno]
_GLOW = {
    "success": ["#0a2e1a", "#0d4a28", SUCCESS],
    "danger":  ["#2e0a0a", "#4a0d0d", DANGER],
    "blue":    ["#0a1a2e", "#0d2a48", BLUE_TEAM],
    "red":     ["#2e0a0a", "#481010", RED_TEAM],
    "neutral": ["#1a1a1a", "#2e2e2e", "#666666"],
}


# ═══════════════════════════════════════════════════════════════════════
#  HOVER BUTTON
# ═══════════════════════════════════════════════════════════════════════
class HoverButton(tk.Button):
    """Botão com efeito de hover suave."""
    def __init__(self, master, hover_bg=None, **kwargs):
        self._normal_bg = kwargs.get("bg", BG_LIGHT)
        self._hover_bg  = hover_bg or BG_HOVER
        super().__init__(master, **kwargs)
        self.bind("<Enter>", lambda e: self.config(bg=self._hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self._normal_bg))


# ═══════════════════════════════════════════════════════════════════════
#  REPLAY VIEWER
# ═══════════════════════════════════════════════════════════════════════
class ReplayViewer:
    """Janela de replay animado com layout moderno."""

    def __init__(self, root, replay_engine, map_visualizer):
        self.root    = root
        self.engine  = replay_engine
        self.map_viz = map_visualizer

        # Playback state
        self._current_ms   = 0
        self._is_playing   = False
        self._speed        = 1.0
        self._last_tick    = time.perf_counter()
        self._after_id     = None
        self._frame_counter = 0

        # Visibility
        self._visible       = {}
        self._towers_visible = True
        self._wards_visible  = True

        # Canvas items
        self._champ_items      = {}   # {pid: img_id}
        self._champ_labels     = {}   # {pid: text_id}
        self._champ_shadows    = {}   # {pid: oval_id}
        self._champ_photos     = {}   # {pid: PhotoImage}
        self._champ_photos_gray= {}
        self._mini_photos      = {}   # {pid: PhotoImage 20px}
        self._micro_photos     = {}   # {pid: PhotoImage 14px}
        self._ward_items       = {}   # {ward_id: item_id}
        self._event_pool       = []   # [(glow_o, glow_m, glow_i, txt)]
        self._obj_pool         = []   # [(oval, txt)]
        self._timeline_cursor  = None
        self._timeline_scrubber= None
        self._tower_items      = {}   # {key: (rect, txt)}
        self._recall_items     = {}   # {pid: (oval, arc, txt)}
        self._death_labels     = {}   # {pid: txt}
        self._levelup_items    = {}   # {pid: oval}
        self._special_pool     = []   # [txt_id]
        self._killfeed_items   = []   # [(k_img, txt, v_img)]
        self._skilllup_items   = {}   # {pid: txt}
        self._obj_timer_items  = []   # [(oval, txt)]
        self._gold_history     = []   # [(ms, diff)]

        # Side-panel widget refs (definidos em _create_side_panel)
        self._champ_icon_labels = {}
        self._stat_labels       = {}

        # Janela
        self.win = tk.Toplevel(root)
        self.win.title("VisionLOL – Match Replay")
        self.win.configure(bg=BG_DARKEST)
        self.win.geometry(
            f"{CANVAS_SIZE + SIDE_PANEL_WIDTH + 24}"
            f"x{CANVAS_SIZE + TIMELINE_HEIGHT + HEADER_HEIGHT + 90}"
        )
        self.win.resizable(True, True)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._create_layout()
        self._load_assets()
        self._create_canvas_items()
        self._update_side_panel()

        self._last_tick = time.perf_counter()
        self._animation_tick()

        # Render da timeline acionado pelo evento <Configure> do canvas
        # (garante que winfo_width() já retorna o tamanho real)
        self._timeline_rendered = False
        self.timeline_canvas.bind("<Configure>", self._on_timeline_configure)

    def _on_timeline_configure(self, event):
        """Renderiza marcadores quando o canvas tem largura real (>50px)."""
        if event.width > 50:
            self._render_timeline_markers()
            # Rebind para redesenhar ao redimensionar a janela
            self.timeline_canvas.bind("<Configure>", self._on_timeline_resize)

    def _on_timeline_resize(self, event):
        """Redesenha a timeline ao redimensionar."""
        if event.width > 50:
            self.timeline_canvas.delete("all")
            self._timeline_cursor   = None
            self._timeline_scrubber = None
            self._render_timeline_markers()

    # ─────────────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────────────

    def _create_layout(self):
        self._create_header(self.win)

        body = tk.Frame(self.win, bg=BG_DARKEST)
        body.pack(fill=tk.BOTH, expand=True, padx=8)

        # Canvas com moldura de borda
        canvas_wrap = tk.Frame(body, bg=BORDER, padx=1, pady=1)
        canvas_wrap.pack(side=tk.LEFT, padx=(0, 8), pady=6)

        self.canvas = tk.Canvas(
            canvas_wrap, width=CANVAS_SIZE, height=CANVAS_SIZE,
            bg="#080c14", highlightthickness=0
        )
        self.canvas.pack()

        self._create_side_panel(body)
        self._create_timeline(self.win)
        self._create_controls(self.win)

    def _create_header(self, parent):
        """Barra superior: título | matchup | duração | hotkeys."""
        hdr = tk.Frame(parent, bg=BG_DARK, height=HEADER_HEIGHT)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 0))
        hdr.pack_propagate(False)

        # Separador vertical helper
        def vsep():
            tk.Frame(hdr, bg=BORDER, width=1).pack(
                side=tk.LEFT, fill=tk.Y, pady=7
            )

        tk.Label(
            hdr, text="VISIONLOL  REPLAY",
            font=("Segoe UI", 11, "bold"), bg=BG_DARK, fg=ACCENT
        ).pack(side=tk.LEFT, padx=14)

        vsep()

        t_info  = self.engine.pid_map.get(self.engine.target_pid, {})
        opp_pid = self.engine.get_opponent_pid()
        o_info  = self.engine.pid_map.get(opp_pid, {})

        tk.Label(
            hdr,
            text=f"{t_info.get('champion','?')}  vs  {o_info.get('champion','?')}",
            font=("Segoe UI", 11), bg=BG_DARK, fg=TEXT_COLOR
        ).pack(side=tk.LEFT, padx=18)

        # Duração + hotkeys no lado direito
        tk.Label(
            hdr,
            text="T: torres   W: wards   1-5: velocidade   Space: play",
            font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM
        ).pack(side=tk.RIGHT, padx=14)

        vsep()

        tk.Label(
            hdr,
            text=self.engine.format_time(self.engine.game_duration_ms),
            font=("Consolas", 11, "bold"), bg=BG_DARK, fg=TEXT_DIM
        ).pack(side=tk.RIGHT, padx=12)

    def _create_side_panel(self, parent):
        panel = tk.Frame(parent, bg=BG_DARKEST, width=SIDE_PANEL_WIDTH)
        panel.pack(side=tk.RIGHT, fill=tk.Y, pady=6)
        panel.pack_propagate(False)

        # ── CARD: Matchup ──────────────────────────────────────────
        card = self._card(panel)
        self._section_title(card, "MATCHUP")

        target_pid = self.engine.target_pid
        opp_pid    = self.engine.get_opponent_pid()

        # Você
        you_row = tk.Frame(card, bg=BG_MEDIUM)
        you_row.pack(fill=tk.X, padx=10, pady=(2, 0))
        self._target_icon_label = tk.Label(you_row, bg=BG_MEDIUM)
        self._target_icon_label.pack(side=tk.LEFT, padx=(0, 7))
        you_info = tk.Frame(you_row, bg=BG_MEDIUM)
        you_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            you_info,
            text=self.engine.pid_map.get(target_pid, {}).get("champion", "?"),
            font=("Segoe UI", 10, "bold"), bg=BG_MEDIUM, fg=WARNING, anchor=tk.W
        ).pack(fill=tk.X)
        self._target_stats = tk.Label(
            you_info, text="Lv1  0/0/0  0cs",
            font=("Consolas", 8), bg=BG_MEDIUM, fg=TEXT_COLOR, anchor=tk.W
        )
        self._target_stats.pack(fill=tk.X)

        # VS divider
        vs = tk.Frame(card, bg=BG_MEDIUM)
        vs.pack(fill=tk.X, padx=16, pady=3)
        tk.Frame(vs, bg=BORDER, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(vs, text=" VS ", font=("Segoe UI", 7, "bold"),
                 bg=BG_MEDIUM, fg=TEXT_DIM).pack(side=tk.LEFT)
        tk.Frame(vs, bg=BORDER, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Oponente
        opp_row = tk.Frame(card, bg=BG_MEDIUM)
        opp_row.pack(fill=tk.X, padx=10, pady=(0, 2))
        self._opp_icon_label = tk.Label(opp_row, bg=BG_MEDIUM)
        self._opp_icon_label.pack(side=tk.LEFT, padx=(0, 7))
        opp_frame = tk.Frame(opp_row, bg=BG_MEDIUM)
        opp_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            opp_frame,
            text=self.engine.pid_map.get(opp_pid, {}).get("champion", "?"),
            font=("Segoe UI", 10, "bold"), bg=BG_MEDIUM, fg=RED_TEAM, anchor=tk.W
        ).pack(fill=tk.X)
        self._opp_stats = tk.Label(
            opp_frame, text="Lv1  0/0/0  0cs",
            font=("Consolas", 8), bg=BG_MEDIUM, fg=TEXT_COLOR, anchor=tk.W
        )
        self._opp_stats.pack(fill=tk.X)

        # Gold diff
        gd = tk.Frame(card, bg=BG_MEDIUM)
        gd.pack(fill=tk.X, padx=10, pady=(6, 2))
        self._gold_diff_label = tk.Label(
            gd, text="Gold:  +0",
            font=("Consolas", 9, "bold"), bg=BG_MEDIUM, fg=SUCCESS, anchor=tk.W
        )
        self._gold_diff_label.pack(fill=tk.X)

        # Gold graph
        self._gold_graph = tk.Canvas(
            card, width=GOLD_GRAPH_W, height=GOLD_GRAPH_H,
            bg="#090d16", highlightthickness=1, highlightbackground=BORDER
        )
        self._gold_graph.pack(padx=10, pady=(0, 8))

        # ── CARD: Objective timers ─────────────────────────────────
        self._obj_frame = self._card(panel)
        self._obj_timer_labels = {}

        # ── CARD: Champions ────────────────────────────────────────
        champ_card = self._card(panel, expand=True)
        self._section_title(champ_card, "CAMPEÕES")

        blue = [(p, i) for p, i in self.engine.pid_map.items() if i["team_id"] == 100]
        red  = [(p, i) for p, i in self.engine.pid_map.items() if i["team_id"] == 200]

        for team_label, team_color, team_list in [
            ("BLUE", BLUE_TEAM, blue),
            ("RED",  RED_TEAM,  red),
        ]:
            # Cabeçalho de time com barra colorida
            th = tk.Frame(champ_card, bg=BG_MEDIUM)
            th.pack(fill=tk.X, padx=10, pady=(6, 2))
            tk.Frame(th, bg=team_color, width=3).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
            tk.Label(th, text=team_label, font=("Segoe UI", 8, "bold"),
                     bg=BG_MEDIUM, fg=team_color).pack(side=tk.LEFT)

            for pid, info in team_list:
                row = tk.Frame(champ_card, bg=BG_MEDIUM)
                row.pack(fill=tk.X, padx=6, pady=1)

                default_on = pid in (self.engine.target_pid, opp_pid)
                var = tk.BooleanVar(value=default_on)
                self._visible[pid] = var

                tk.Checkbutton(
                    row, variable=var, bg=BG_MEDIUM,
                    selectcolor=BG_LIGHT, activebackground=BG_MEDIUM,
                    command=lambda p=pid: self._toggle_champion(p)
                ).pack(side=tk.LEFT)

                # Mini-ícone placeholder (preenchido em _load_assets)
                icon_lbl = tk.Label(row, bg=BG_MEDIUM)
                icon_lbl.pack(side=tk.LEFT, padx=(0, 5))
                self._champ_icon_labels[pid] = icon_lbl

                champ     = info.get("champion", "?")
                is_target = pid == self.engine.target_pid
                name_fg   = WARNING if is_target else TEXT_COLOR
                name_txt  = champ + (" ★" if is_target else "")
                tk.Label(row, text=name_txt, font=("Segoe UI", 9),
                         bg=BG_MEDIUM, fg=name_fg, anchor=tk.W).pack(side=tk.LEFT)

                stat_lbl = tk.Label(row, text="Lv1", font=("Consolas", 8),
                                    bg=BG_MEDIUM, fg=TEXT_DIM, anchor=tk.E)
                stat_lbl.pack(side=tk.RIGHT, padx=(0, 6))
                self._stat_labels[pid] = stat_lbl

        # ── CARD: Velocidade + tempo ───────────────────────────────
        spd_card = self._card(panel)
        self._section_title(spd_card, "VELOCIDADE")

        pill = tk.Frame(spd_card, bg=BG_LIGHT)
        pill.pack(fill=tk.X, padx=10, pady=(0, 6))

        self._speed_buttons = {}
        for spd in [0.5, 1, 2, 4, 8]:
            active = spd == 1
            btn = HoverButton(
                pill, text=f"{spd}x",
                font=("Segoe UI", 9, "bold"),
                bg=ACCENT if active else BG_LIGHT,
                fg=TEXT_BRIGHT if active else TEXT_DIM,
                hover_bg=ACCENT if active else BG_HOVER,
                bd=0, padx=4, pady=4, cursor="hand2",
                command=lambda s=spd: self._set_speed(s)
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
            self._speed_buttons[spd] = btn

        self._time_label = tk.Label(
            spd_card, text="0:00 / 0:00",
            font=("Consolas", 17, "bold"), bg=BG_MEDIUM, fg=ACCENT
        )
        self._time_label.pack(fill=tk.X, padx=10, pady=(4, 10))

    # helpers de layout ───────────────────────────────────────────────

    def _card(self, parent, expand=False):
        """Frame com borda e background card."""
        f = tk.Frame(parent, bg=BG_MEDIUM,
                     highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill=tk.BOTH if expand else tk.X,
               expand=expand, pady=(0, 6))
        return f

    def _section_title(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"),
                 bg=BG_MEDIUM, fg=TEXT_DIM).pack(anchor=tk.W, padx=10, pady=(7, 2))

    # ─────────────────────────────────────────────────────────────────
    #  TIMELINE
    # ─────────────────────────────────────────────────────────────────

    def _create_timeline(self, parent):
        wrap = tk.Frame(parent, bg=BG_DARKEST)
        wrap.pack(fill=tk.X, padx=8, pady=(2, 0))

        self.timeline_canvas = tk.Canvas(
            wrap, height=TIMELINE_HEIGHT, bg=BG_DARK,
            highlightthickness=1, highlightbackground=BORDER
        )
        self.timeline_canvas.pack(fill=tk.X)
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self._on_timeline_drag)

    # ─────────────────────────────────────────────────────────────────
    #  CONTROLES
    # ─────────────────────────────────────────────────────────────────

    def _create_controls(self, parent):
        frame = tk.Frame(parent, bg=BG_DARKEST)
        frame.pack(fill=tk.X, padx=8, pady=(5, 10))

        for text, cmd, bg, hover in [
            ("|◀",     lambda: self._seek(0),                              BG_LIGHT, BG_HOVER),
            ("◀◀",    lambda: self._seek(self._current_ms - 30_000),      BG_LIGHT, BG_HOVER),
            ("  ▶  PLAY  ", self._toggle_play_pause,                       ACCENT,   "#4090e0"),
            ("▶▶",    lambda: self._seek(self._current_ms + 30_000),      BG_LIGHT, BG_HOVER),
            ("▶|",     lambda: self._seek(self.engine.game_duration_ms),   BG_LIGHT, BG_HOVER),
        ]:
            is_play = "PLAY" in text
            btn = HoverButton(
                frame, text=text, command=cmd,
                font=("Segoe UI", 11 if is_play else 10, "bold"),
                bg=bg, fg=TEXT_BRIGHT if is_play else TEXT_COLOR,
                hover_bg=hover, bd=0,
                padx=18 if is_play else 8, pady=5, cursor="hand2"
            )
            btn.pack(side=tk.LEFT, padx=2)
            if is_play:
                self._play_btn = btn

        self._ctrl_time = tk.Label(
            frame, text="0:00 / 0:00",
            font=("Consolas", 10), bg=BG_DARKEST, fg=TEXT_DIM
        )
        self._ctrl_time.pack(side=tk.RIGHT, padx=12)

        # Atalhos de teclado
        self.win.bind("<space>",  lambda e: self._toggle_play_pause())
        self.win.bind("<Left>",   lambda e: self._seek(self._current_ms - 10_000))
        self.win.bind("<Right>",  lambda e: self._seek(self._current_ms + 10_000))
        self.win.bind("1", lambda e: self._set_speed(0.5))
        self.win.bind("2", lambda e: self._set_speed(1))
        self.win.bind("3", lambda e: self._set_speed(2))
        self.win.bind("4", lambda e: self._set_speed(4))
        self.win.bind("5", lambda e: self._set_speed(8))
        self.win.bind("t", lambda e: self._toggle_all_towers())
        self.win.bind("w", lambda e: self._toggle_all_wards())

    # ─────────────────────────────────────────────────────────────────
    #  ASSETS
    # ─────────────────────────────────────────────────────────────────

    def _load_assets(self):
        # Minimap background
        mm = self.map_viz._download_minimap()
        if mm:
            resized = mm.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
            overlay = Image.new("RGBA", resized.size, (0, 0, 0, 45))
            resized = Image.alpha_composite(resized, overlay)
            self._bg_photo = ImageTk.PhotoImage(resized.convert("RGB"))
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self._bg_photo, tags="bg")

        target_pid = self.engine.target_pid
        opp_pid    = self.engine.get_opponent_pid()

        for pid, info in self.engine.pid_map.items():
            champ   = info.get("champion", "?")
            team_id = info.get("team_id", 100)

            icon_pil = self.map_viz._download_champion_icon(champ)

            if icon_pil:
                # 30 px (mapa) — com borda dourada para o target
                bordered = self.map_viz._create_bordered_icon(icon_pil, team_id, size=ICON_SIZE)
                if pid == target_pid:
                    bordered = self._add_gold_border(bordered)
                self._champ_photos[pid] = ImageTk.PhotoImage(bordered)

                # Versão cinza (morte)
                gray = bordered.convert("L").convert("RGBA")
                tint = Image.new("RGBA", gray.size, (80, 20, 20, 110))
                self._champ_photos_gray[pid] = ImageTk.PhotoImage(
                    Image.alpha_composite(gray, tint)
                )

                # 20 px — side panel
                mini = self.map_viz._create_bordered_icon(icon_pil, team_id, size=MINI_ICON_SIZE)
                self._mini_photos[pid] = ImageTk.PhotoImage(mini)

                # 14 px — kill feed
                micro = self.map_viz._create_bordered_icon(icon_pil, team_id, size=MICRO_ICON_SIZE)
                self._micro_photos[pid] = ImageTk.PhotoImage(micro)

            else:
                # Fallback: círculo colorido
                color = (83, 155, 245, 200) if team_id == 100 else (229, 83, 75, 200)
                for size, store in [
                    (ICON_SIZE + 6,        self._champ_photos),
                    (ICON_SIZE + 6,        self._champ_photos_gray),
                    (MINI_ICON_SIZE + 4,   self._mini_photos),
                    (MICRO_ICON_SIZE + 2,  self._micro_photos),
                ]:
                    fb = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                    ImageDraw.Draw(fb).ellipse([0, 0, size - 1, size - 1], fill=color)
                    store[pid] = ImageTk.PhotoImage(fb)

        # Preenche ícones no side panel
        for pid, lbl in self._champ_icon_labels.items():
            ph = self._mini_photos.get(pid)
            if ph:
                lbl.config(image=ph)
                lbl._photo = ph   # evita GC

        # Ícones do matchup
        for attr, pid in [("_target_icon_label", target_pid),
                           ("_opp_icon_label",    opp_pid)]:
            ph = self._mini_photos.get(pid)
            if ph:
                lbl = getattr(self, attr)
                lbl.config(image=ph)
                lbl._photo = ph

    def _add_gold_border(self, img):
        b = 2
        ns = (img.width + b * 2, img.height + b * 2)
        result = Image.new("RGBA", ns, (0, 0, 0, 0))
        ImageDraw.Draw(result).ellipse([0, 0, ns[0]-1, ns[1]-1], fill=(255, 215, 0, 255))
        result.paste(img, (b, b), img)
        return result

    # ─────────────────────────────────────────────────────────────────
    #  CANVAS ITEMS
    # ─────────────────────────────────────────────────────────────────

    def _create_canvas_items(self):
        # Sombra + ícone + label por campeão
        for pid in self.engine.pid_map:
            photo = self._champ_photos.get(pid)
            if not photo:
                continue

            shadow = self.canvas.create_oval(
                -60, -60, -40, -40, fill="#000000", outline="",
                tags=f"shadow_{pid}"
            )
            self._champ_shadows[pid] = shadow

            item = self.canvas.create_image(-50, -50, image=photo, tags=f"champ_{pid}")
            self._champ_items[pid] = item

            short = self.engine.pid_map[pid].get("champion", "?")[:6]
            lbl = self.canvas.create_text(
                -50, -50, text=short, fill=TEXT_COLOR,
                font=("Segoe UI", 7), tags=f"label_{pid}"
            )
            self._champ_labels[pid] = lbl

            if not self._visible.get(pid, tk.BooleanVar(value=False)).get():
                for itm in (item, lbl, shadow):
                    self.canvas.itemconfigure(itm, state="hidden")

        # Pool de kills — 3 ovals de glow + texto
        for _ in range(15):
            go = self.canvas.create_oval(0,0,0,0, fill="",outline="", state="hidden", tags="glow")
            gm = self.canvas.create_oval(0,0,0,0, fill="",outline="", state="hidden", tags="glow")
            gi = self.canvas.create_oval(0,0,0,0, fill="",outline="", state="hidden", tags="glow")
            tx = self.canvas.create_text(0,0, text="", fill=TEXT_COLOR,
                                          font=("Segoe UI", 7), state="hidden", tags="evtlabel")
            self._event_pool.append((go, gm, gi, tx))

        # Pool de objetivos
        for _ in range(8):
            ov = self.canvas.create_oval(0,0,0,0, fill="",outline="", width=2,
                                          state="hidden", tags="obj_marker")
            tx = self.canvas.create_text(0,0, text="", fill=TEXT_BRIGHT,
                                          font=("Segoe UI", 10,"bold"), state="hidden",
                                          tags="obj_label")
            self._obj_pool.append((ov, tx))

        # Torres — quadrado preenchido + letra "T"
        for t in self.engine.get_tower_states_at(0):
            cx, cy = self.engine.game_to_canvas(t["x"], t["y"], CANVAS_SIZE)
            is_blue = t["team"] == 100
            fill    = BLUE_TEAM_DIM if is_blue else RED_TEAM_DIM
            outline = BLUE_TEAM    if is_blue else RED_TEAM
            s = 6
            rect = self.canvas.create_rectangle(
                cx-s, cy-s, cx+s, cy+s, fill=fill, outline=outline, width=1, tags="tower"
            )
            txt = self.canvas.create_text(
                cx, cy, text="T", fill=outline,
                font=("Segoe UI", 6, "bold"), tags="tower_lbl"
            )
            self._tower_items[t["key"]] = (rect, txt)

        # Recall indicators
        for pid in self.engine.pid_map:
            ov  = self.canvas.create_oval(0,0,0,0, fill="", outline=ACCENT,
                                           width=2, state="hidden", tags="recall")
            arc = self.canvas.create_arc(0,0,0,0, fill="", outline="#7ee8fa",
                                          width=3, start=90, extent=0,
                                          state="hidden", style="arc", tags="recall_arc")
            tx  = self.canvas.create_text(0,0, text="RECALL", fill=ACCENT,
                                           font=("Segoe UI", 7, "bold"),
                                           state="hidden", tags="recall_txt")
            self._recall_items[pid] = (ov, arc, tx)

        # Death labels
        for pid in self.engine.pid_map:
            tx = self.canvas.create_text(0,0, text="", fill=DANGER,
                                          font=("Consolas", 8, "bold"),
                                          state="hidden", tags="death_tmr")
            self._death_labels[pid] = tx

        # Level-up flash
        for pid in self.engine.pid_map:
            ov = self.canvas.create_oval(0,0,0,0, fill="", outline=WARNING,
                                          width=2, state="hidden", tags="levelup")
            self._levelup_items[pid] = ov

        # Special kill labels
        for _ in range(5):
            tx = self.canvas.create_text(0,0, text="", fill=WARNING,
                                          font=("Segoe UI", 12, "bold"),
                                          state="hidden", tags="spkill")
            self._special_pool.append(tx)

        # Kill feed com micro-ícones (canto superior direito)
        KF_RIGHT = CANVAS_SIZE - 8
        for i in range(KILL_FEED_MAX):
            y = 14 + i * 20
            k_img = self.canvas.create_image(
                KF_RIGHT - 54, y, state="hidden", tags="kf_icon"
            )
            txt = self.canvas.create_text(
                KF_RIGHT - 38, y, text="", anchor=tk.W,
                fill=TEXT_COLOR, font=("Consolas", 8),
                state="hidden", tags="kf_txt"
            )
            v_img = self.canvas.create_image(
                KF_RIGHT - 7, y, state="hidden", tags="kf_icon"
            )
            self._killfeed_items.append((k_img, txt, v_img))

        # Skill-up labels (Q/W/E/R)
        for pid in self.engine.pid_map:
            tx = self.canvas.create_text(0,0, text="", fill=SUCCESS,
                                          font=("Segoe UI", 9, "bold"),
                                          state="hidden", tags="skillup")
            self._skilllup_items[pid] = tx

        # Objective respawn timers no mapa
        for _ in range(4):
            ov = self.canvas.create_oval(0,0,0,0, fill="", outline="",
                                          width=2, state="hidden", tags="obj_tmr")
            tx = self.canvas.create_text(0,0, text="", fill=TEXT_COLOR,
                                          font=("Consolas", 9, "bold"),
                                          state="hidden", tags="obj_tmr_txt")
            self._obj_timer_items.append((ov, tx))

    # ─────────────────────────────────────────────────────────────────
    #  TIMELINE BAR
    # ─────────────────────────────────────────────────────────────────

    def _render_timeline_markers(self):
        # ── Layout (h=88, ty=40) ──────────────────────────────────────
        # y= 4–15  : objectives (ovals)
        # y=16–36  : blue team kill marks (sobem da track)
        # y=34–46  : TRACK + teamfight zones (±6)
        # y=44–64  : red team kill marks (descem da track)
        # y=60–66  : torres destruídas
        # y=68–71  : recalls (barra fina — apenas target)
        # y=74–82  : marcas de tempo + texto
        # ─────────────────────────────────────────────────────────────
        w   = self.timeline_canvas.winfo_width()
        h   = TIMELINE_HEIGHT   # 88
        dur = max(self.engine.game_duration_ms, 1)
        pad = 28
        ty  = 40                # centro da track (não h//2)

        def px(ms):
            return pad + (ms / dur) * (w - pad * 2)

        # ── Track ────────────────────────────────────────────────────
        self.timeline_canvas.create_rectangle(
            pad, ty - 3, w - pad, ty + 3, fill=BG_LIGHT, outline=""
        )
        # Caps arredondados nos extremos
        for ex in (pad, w - pad):
            self.timeline_canvas.create_oval(ex-4, ty-4, ex+4, ty+4, fill=BG_LIGHT, outline="")

        # ── Teamfight zones (fundo sutil ±6 ao redor da track) ───────
        for tf in self.engine.get_teamfights():
            x1 = px(tf["start_ms"])
            x2 = max(px(tf["end_ms"]), x1 + 5)
            self.timeline_canvas.create_rectangle(
                x1, ty - 6, x2, ty + 6,
                fill=WARNING_DIM, outline=WARNING, width=1
            )

        # ── Time marks (a cada 5 min) — zona segura no fundo ─────────
        for mins in range(0, dur // 60000 + 1, 5):
            x = px(mins * 60000)
            # traço curto no centro da track
            self.timeline_canvas.create_line(x, ty - 5, x, ty + 5, fill=BORDER, width=1)
            # texto bem abaixo da track, zona exclusiva
            self.timeline_canvas.create_text(
                x, ty + 36, text=f"{mins}m",
                fill=TEXT_DIM, font=("Segoe UI", 7)
            )

        # ── Kill marks ───────────────────────────────────────────────
        for k in self.engine.get_all_kills():
            x    = px(k["timestamp_ms"])
            team = self.engine.pid_map.get(k["killer_pid"], {}).get("team_id", 100)
            if team == 100:
                # Blue team: marca acima da track (sobe até y=19)
                self.timeline_canvas.create_line(x, ty - 4, x, ty - 19, fill=BLUE_TEAM, width=1)
            else:
                # Red team: marca abaixo da track (desce até y=61)
                self.timeline_canvas.create_line(x, ty + 4, x, ty + 19, fill=RED_TEAM, width=1)

        # ── Objective markers (topo — zona exclusiva y=4-14) ─────────
        OBJ_LETTER = {"DRAGON": "D", "BARON_NASHOR": "B", "RIFTHERALD": "H"}
        OBJ_COLOR  = {"DRAGON": PURPLE, "BARON_NASHOR": "#8b008b", "RIFTHERALD": WARNING}
        for o in self.engine.get_all_objectives():
            x  = px(o["timestamp_ms"])
            c  = OBJ_COLOR.get(o["monster_type"], PURPLE)
            lt = OBJ_LETTER.get(o["monster_type"], "?")
            r  = 5
            # oval centrado em y=9 (topo)
            self.timeline_canvas.create_oval(x-r, 4, x+r, 4+r*2, fill=c, outline=TEXT_BRIGHT, width=1)
            self.timeline_canvas.create_text(x, 4 + r, text=lt, fill=TEXT_BRIGHT, font=("Segoe UI", 6, "bold"))

        # ── Torres destruídas (y=60-66 — faixa exclusiva) ────────────
        for b in self.engine.get_all_buildings():
            x = px(b["timestamp_ms"])
            self.timeline_canvas.create_rectangle(
                x - 3, ty + 22, x + 3, ty + 28,
                fill=WARNING_DIM, outline=WARNING, width=1
            )
            self.timeline_canvas.create_text(
                x, ty + 25, text="T", fill=WARNING, font=("Segoe UI", 5, "bold")
            )

        # ── Recall bars (y=68-71 — faixa fina target only) ───────────
        for r in self.engine.get_all_recalls():
            if r["pid"] != self.engine.target_pid:
                continue
            x1 = px(r["timestamp_ms"])
            x2 = max(px(r["end_ms"]), x1 + 3)
            self.timeline_canvas.create_rectangle(
                x1, ty + 30, x2, ty + 33,
                fill=ACCENT_DIM, outline=ACCENT, width=1
            )

        # ── Cursor + scrubber (renderizados por último → sempre no topo)
        self._timeline_cursor = self.timeline_canvas.create_line(
            pad, 2, pad, h - 2, fill=ACCENT, width=2, tags="cursor"
        )
        self._timeline_scrubber = self.timeline_canvas.create_oval(
            pad - 6, ty - 6, pad + 6, ty + 6,
            fill=ACCENT, outline=TEXT_BRIGHT, width=1, tags="scrubber"
        )

    # ─────────────────────────────────────────────────────────────────
    #  ANIMATION LOOP
    # ─────────────────────────────────────────────────────────────────

    def _animation_tick(self):
        now = time.perf_counter()

        if self._is_playing:
            elapsed_ms = int((now - self._last_tick) * 1000 * self._speed)
            self._current_ms = min(self._current_ms + elapsed_ms, self.engine.game_duration_ms)
            if self._current_ms >= self.engine.game_duration_ms:
                self._is_playing = False
                self._update_play_button()

        self._last_tick = now
        self._frame_counter += 1

        self._update_champions()
        self._update_events()
        self._update_objectives()
        self._update_wards()
        self._update_recalls()
        self._update_level_ups()
        self._update_skill_ups()
        self._update_special_kills()
        self._update_killfeed()
        self._update_timeline_cursor()
        self._update_time_label()

        if self._frame_counter % 15 == 0:
            self._update_side_panel()
            self._update_towers()
            self._update_obj_timers()
            self._update_gold_graph()

        self._after_id = self.win.after(FRAME_INTERVAL_MS, self._animation_tick)

    # ─────────────────────────────────────────────────────────────────
    #  UPDATE METHODS
    # ─────────────────────────────────────────────────────────────────

    def _update_champions(self):
        positions = self.engine.get_positions_at(self._current_ms)

        for pid, (gx, gy) in positions.items():
            if pid not in self._champ_items:
                continue

            visible   = self._visible.get(pid, tk.BooleanVar(value=False)).get()
            item      = self._champ_items[pid]
            label     = self._champ_labels[pid]
            shadow    = self._champ_shadows.get(pid)
            death_lbl = self._death_labels.get(pid)

            if not visible or (gx == 0 and gy == 0):
                for itm in filter(None, [item, label, shadow, death_lbl]):
                    self.canvas.itemconfigure(itm, state="hidden")
                continue

            cx, cy = self.engine.game_to_canvas(gx, gy, CANVAS_SIZE)

            # Sombra levemente deslocada
            if shadow:
                sr = ICON_SIZE // 3
                self.canvas.coords(shadow, cx-sr, cy+3, cx+sr, cy+sr+5)
                self.canvas.itemconfigure(shadow, state="normal")

            self.canvas.coords(item,  cx, cy)
            self.canvas.coords(label, cx, cy + ICON_SIZE//2 + 8)
            self.canvas.itemconfigure(item,  state="normal")
            self.canvas.itemconfigure(label, state="normal")

            is_dead, respawn_ms = self.engine.is_dead_at(pid, self._current_ms)
            if is_dead:
                ph = self._champ_photos_gray.get(pid)
                if ph:
                    self.canvas.itemconfigure(item, image=ph)
                if death_lbl:
                    remaining = max(0, (respawn_ms - self._current_ms) // 1000)
                    self.canvas.coords(death_lbl, cx, cy - ICON_SIZE//2 - 6)
                    self.canvas.itemconfigure(death_lbl, text=f"{remaining}s", state="normal")
            else:
                ph = self._champ_photos.get(pid)
                if ph:
                    self.canvas.itemconfigure(item, image=ph)
                if death_lbl:
                    self.canvas.itemconfigure(death_lbl, state="hidden")

    def _update_events(self):
        """Kill markers com glow de 3 anéis concêntricos."""
        events = self.engine.get_active_events_at(self._current_ms, EVENT_WINDOW_MS)

        for go, gm, gi, tx in self._event_pool:
            for itm in (go, gm, gi, tx):
                self.canvas.itemconfigure(itm, state="hidden")

        for i, ev in enumerate(events):
            if i >= len(self._event_pool):
                break

            go, gm, gi, tx = self._event_pool[i]
            cx, cy = self.engine.game_to_canvas(ev["x"], ev["y"], CANVAS_SIZE)
            age      = ev.get("age_ms", 0)
            progress = age / EVENT_WINDOW_MS

            base_r = int(14 * (1.0 - progress * 0.5))
            if age < 300:
                base_r = int(base_r * 1.5)

            killer = ev.get("killer_pid", 0)
            victim = ev.get("victim_pid", 0)
            if   killer == self.engine.target_pid:    palette = _GLOW["success"]
            elif victim == self.engine.target_pid:    palette = _GLOW["danger"]
            else:
                kt = self.engine.pid_map.get(killer, {}).get("team_id", 0)
                palette = _GLOW["blue"] if kt == self.engine.target_team else _GLOW["red"]
            if progress > 0.6:
                palette = _GLOW["neutral"]

            for ring_item, color_idx, mult in [
                (go, 0, 2.0), (gm, 1, 1.35), (gi, 2, 0.7)
            ]:
                r = int(base_r * mult)
                self.canvas.coords(ring_item, cx-r, cy-r, cx+r, cy+r)
                self.canvas.itemconfigure(ring_item, fill=palette[color_idx],
                                           outline="", state="normal")

            victim_champ = self.engine.pid_map.get(victim, {}).get("champion", "?")
            killer_champ = self.engine.pid_map.get(killer, {}).get("champion", "?")
            self.canvas.coords(tx, cx, cy + base_r + 10)
            self.canvas.itemconfigure(
                tx, text=f"{killer_champ[:5]} › {victim_champ[:5]}",
                fill=TEXT_COLOR if progress < 0.5 else TEXT_DIM, state="normal"
            )

    def _update_objectives(self):
        events = self.engine.get_active_objectives_at(self._current_ms, OBJ_WINDOW_MS)

        for ov, tx in self._obj_pool:
            self.canvas.itemconfigure(ov, state="hidden")
            self.canvas.itemconfigure(tx, state="hidden")

        pool_i = 0
        for ev in events:
            if pool_i >= len(self._obj_pool):
                break
            if ev.get("event_type") == "building":
                continue

            ov, tx = self._obj_pool[pool_i]
            pool_i += 1

            cx, cy = self.engine.game_to_canvas(ev["x"], ev["y"], CANVAS_SIZE)
            age    = ev.get("age_ms", 0)
            pulse  = 1.0 + 0.15 * ((age // 400) % 2)
            r      = int(14 * pulse)

            kt = ev.get("killer_team", 0)
            if kt == self.engine.target_team:
                fill, outline = SUCCESS_DIM, SUCCESS
            else:
                fill, outline = DANGER_DIM, DANGER

            self.canvas.coords(ov, cx-r, cy-r, cx+r, cy+r)
            self.canvas.itemconfigure(ov, fill=fill, outline=outline, state="normal")

            letter = {"DRAGON":"D","BARON_NASHOR":"B","RIFTHERALD":"H"}.get(
                ev.get("monster_type",""), "?")
            self.canvas.coords(tx, cx, cy)
            self.canvas.itemconfigure(tx, text=letter, state="normal")

    def _update_wards(self):
        if not self._wards_visible:
            return

        active     = self.engine.get_active_wards_at(self._current_ms)
        active_ids = {w["id"] for w in active}

        for wid in list(self._ward_items):
            if wid not in active_ids:
                self.canvas.delete(self._ward_items.pop(wid))

        for w in active:
            wid = w["id"]
            if wid in self._ward_items:
                continue

            cx, cy    = self.engine.game_to_canvas(w["x"], w["y"], CANVAS_SIZE)
            is_ally   = w["team_id"] == self.engine.target_team
            is_ctrl   = w["ward_type"] == "CONTROL_WARD"

            if is_ally:
                fill, outline = (WARNING, "#ffe066") if not is_ctrl else ("#ff8c00", "#ffd060")
            else:
                fill, outline = ("#992222", "#cc4444") if not is_ctrl else ("#660000", "#aa2222")

            s = 5 if not is_ally else 6

            if is_ctrl:
                # Diamante (losango) para control ward
                item = self.canvas.create_polygon(
                    cx, cy-s-1, cx+s, cy, cx, cy+s+1, cx-s, cy,
                    fill=fill, outline=outline, width=1, tags="ward"
                )
            else:
                # Círculo pequeno para trinket
                item = self.canvas.create_oval(
                    cx-s, cy-s, cx+s, cy+s,
                    fill=fill, outline=outline, width=1, tags="ward"
                )

            self._ward_items[wid] = item

    def _update_timeline_cursor(self):
        if not self._timeline_cursor:
            return
        self.timeline_canvas.update_idletasks()
        w = self.timeline_canvas.winfo_width()
        if w < 50:
            return

        pad = 28
        ty  = 40   # mesmo valor do _render_timeline_markers
        dur = max(self.engine.game_duration_ms, 1)
        x   = pad + (self._current_ms / dur) * (w - pad * 2)

        self.timeline_canvas.coords(self._timeline_cursor, x, 2, x, TIMELINE_HEIGHT - 2)
        if self._timeline_scrubber:
            self.timeline_canvas.coords(self._timeline_scrubber, x-6, ty-6, x+6, ty+6)
        self.timeline_canvas.tag_raise("scrubber")
        self.timeline_canvas.tag_raise("cursor")

    def _update_time_label(self):
        current = self.engine.format_time(self._current_ms)
        total   = self.engine.format_time(self.engine.game_duration_ms)
        text    = f"{current} / {total}"
        self._time_label.config(text=text)
        self._ctrl_time.config(text=text)

    def _update_side_panel(self):
        stats = self.engine.get_stats_at(self._current_ms)

        ts        = stats.get(self.engine.target_pid, {})
        tg        = ts.get("gold", 0)
        opp_pid   = self.engine.get_opponent_pid()
        os_       = stats.get(opp_pid, {})
        og        = os_.get("gold", 0)
        gold_diff = tg - og

        self._target_stats.config(
            text=f"Lv{ts.get('level',1)}  "
                 f"{ts.get('kills',0)}/{ts.get('deaths',0)}/{ts.get('assists',0)}  "
                 f"{ts.get('cs',0)}cs  {tg//100/10:.1f}k"
        )
        self._opp_stats.config(
            text=f"Lv{os_.get('level',1)}  "
                 f"{os_.get('kills',0)}/{os_.get('deaths',0)}/{os_.get('assists',0)}  "
                 f"{os_.get('cs',0)}cs  {og//100/10:.1f}k"
        )

        sign  = "+" if gold_diff >= 0 else ""
        color = SUCCESS if gold_diff >= 0 else DANGER
        self._gold_diff_label.config(text=f"Gold:  {sign}{gold_diff:,}", fg=color)

        for pid, lbl in self._stat_labels.items():
            s      = stats.get(pid, {})
            is_dead, _ = self.engine.is_dead_at(pid, self._current_ms)
            skull  = " ☠" if is_dead else ""
            lbl.config(
                text=f"Lv{s.get('level',1)} {s.get('kills',0)}/{s.get('deaths',0)}{skull}",
                fg=DANGER if is_dead else TEXT_DIM,
            )

    def _update_towers(self):
        towers = self.engine.get_tower_states_at(self._current_ms)
        for t in towers:
            items = self._tower_items.get(t["key"])
            if not items:
                continue
            rect, txt = items
            state = "normal" if (t["alive"] and self._towers_visible) else "hidden"
            self.canvas.itemconfigure(rect, state=state)
            self.canvas.itemconfigure(txt,  state=state)

    def _update_recalls(self):
        active     = self.engine.get_active_recalls_at(self._current_ms)
        active_pids = {r["pid"] for r in active}
        positions  = self.engine.get_positions_at(self._current_ms)

        for pid, (ov, arc, tx) in self._recall_items.items():
            if pid not in active_pids:
                for itm in (ov, arc, tx):
                    self.canvas.itemconfigure(itm, state="hidden")

        for r in active:
            pid = r["pid"]
            if pid not in self._recall_items:
                continue
            if not self._visible.get(pid, tk.BooleanVar(value=False)).get():
                continue

            gx, gy = positions.get(pid, (0, 0))
            if not (gx or gy):
                continue

            cx, cy   = self.engine.game_to_canvas(gx, gy, CANVAS_SIZE)
            rad      = ICON_SIZE//2 + 8
            progress = r.get("progress", 0)
            ov, arc, tx = self._recall_items[pid]

            self.canvas.coords(ov, cx-rad, cy-rad, cx+rad, cy+rad)
            self.canvas.itemconfigure(ov, state="normal")

            extent = int(360 * progress)
            self.canvas.coords(arc, cx-rad, cy-rad, cx+rad, cy+rad)
            self.canvas.itemconfigure(arc, extent=-extent, state="normal")

            remaining = max(0, r["end_ms"] - self._current_ms) // 1000
            self.canvas.coords(tx, cx, cy+rad+10)
            self.canvas.itemconfigure(tx, text=f"RECALL {remaining}s", state="normal")

    def _update_level_ups(self):
        active      = self.engine.get_active_level_ups_at(self._current_ms, window_ms=2000)
        active_pids = {lu["pid"] for lu in active}
        positions   = self.engine.get_positions_at(self._current_ms)

        for pid, ov in self._levelup_items.items():
            if pid not in active_pids:
                self.canvas.itemconfigure(ov, state="hidden")

        for lu in active:
            pid = lu["pid"]
            ov  = self._levelup_items.get(pid)
            if not ov:
                continue
            if not self._visible.get(pid, tk.BooleanVar(value=False)).get():
                continue

            gx, gy = positions.get(pid, (0, 0))
            if not (gx or gy):
                continue

            cx, cy   = self.engine.game_to_canvas(gx, gy, CANVAS_SIZE)
            age      = lu.get("age_ms", 0)
            progress = age / 2000
            rad      = int(ICON_SIZE//2 + 4 + 12 * progress)
            width    = max(1, int(3 * (1.0 - progress)))
            bright   = max(80, int(255 * (1.0 - progress * 0.7)))
            color    = f"#{bright:02x}{int(bright*0.85):02x}{0:02x}"

            self.canvas.coords(ov, cx-rad, cy-rad, cx+rad, cy+rad)
            self.canvas.itemconfigure(ov, outline=color, width=width, state="normal")

    def _update_special_kills(self):
        active = self.engine.get_active_special_kills_at(self._current_ms, window_ms=4000)
        for tx in self._special_pool:
            self.canvas.itemconfigure(tx, state="hidden")

        LABELS = {
            "KILL_FIRST_BLOOD": "FIRST BLOOD!",
            "KILL_MULTI":   "DOUBLE KILL!",
            "KILL_TRIPLE":  "TRIPLE KILL!",
            "KILL_QUADRA":  "QUADRA KILL!",
            "KILL_PENTA":   "PENTA KILL!",
            "KILL_ACE":     "ACE!",
        }

        for i, sk in enumerate(active):
            if i >= len(self._special_pool):
                break
            tx_id = self._special_pool[i]
            cx, cy   = self.engine.game_to_canvas(sk["x"], sk["y"], CANVAS_SIZE)
            age      = sk.get("age_ms", 0)
            progress = age / 4000
            label    = LABELS.get(sk["kill_type"], sk["kill_type"].replace("KILL_",""))

            self.canvas.coords(tx_id, cx, cy - ICON_SIZE - int(20*progress))
            self.canvas.itemconfigure(
                tx_id, text=label,
                fill=WARNING if progress < 0.7 else TEXT_DIM,
                state="normal"
            )

    def _update_killfeed(self):
        events = self.engine.get_active_events_at(self._current_ms, window_ms=12000)
        events.sort(key=lambda e: e.get("age_ms", 0))

        for i, (k_img, txt_id, v_img) in enumerate(self._killfeed_items):
            if i < len(events):
                ev     = events[i]
                killer = ev.get("killer_pid", 0)
                victim = ev.get("victim_pid", 0)
                age    = ev.get("age_ms", 0)

                if   killer == self.engine.target_pid: color = SUCCESS
                elif victim == self.engine.target_pid: color = DANGER
                else:
                    kt    = self.engine.pid_map.get(killer, {}).get("team_id", 0)
                    color = BLUE_TEAM if kt == self.engine.target_team else RED_TEAM
                if age > 8000:
                    color = TEXT_DIM

                k_ph = self._micro_photos.get(killer)
                v_ph = self._micro_photos.get(victim)
                if k_ph:
                    self.canvas.itemconfigure(k_img, image=k_ph, state="normal")
                if v_ph:
                    self.canvas.itemconfigure(v_img, image=v_ph, state="normal")
                self.canvas.itemconfigure(txt_id, text=" › ", fill=color, state="normal")
            else:
                for itm in (k_img, txt_id, v_img):
                    self.canvas.itemconfigure(itm, state="hidden")

    def _update_skill_ups(self):
        active      = self.engine.get_active_level_ups_at(self._current_ms, window_ms=2000)
        active_pids = set()
        positions   = self.engine.get_positions_at(self._current_ms)

        for lu in active:
            pid = lu["pid"]
            active_pids.add(pid)
            tx = self._skilllup_items.get(pid)
            if not tx:
                continue
            if not self._visible.get(pid, tk.BooleanVar(value=False)).get():
                continue

            gx, gy = positions.get(pid, (0, 0))
            if not (gx or gy):
                continue

            cx, cy   = self.engine.game_to_canvas(gx, gy, CANVAS_SIZE)
            age      = lu.get("age_ms", 0)
            progress = age / 2000

            skill_text = f"Lv{lu.get('level', 0)}"
            for su in self.engine._skill_ups:
                if su["pid"] == pid and abs(su["timestamp_ms"] - lu["timestamp_ms"]) < 2000:
                    skill_text = f"Lv{lu.get('level', 0)} +{su['skill_name']}"
                    break

            if progress < 0.8:
                self.canvas.coords(tx, cx, cy + ICON_SIZE//2 + 18 + int(6*progress))
                self.canvas.itemconfigure(tx, text=skill_text, state="normal")
            else:
                self.canvas.itemconfigure(tx, state="hidden")

        for pid, tx in self._skilllup_items.items():
            if pid not in active_pids:
                self.canvas.itemconfigure(tx, state="hidden")

    def _update_obj_timers(self):
        OBJ_POS = {
            "DRAGON":       (9866, 4414),
            "BARON_NASHOR": (5007, 10471),
            "RIFTHERALD":   (5007, 10471),
        }
        OBJ_COLOR = {"DRAGON": PURPLE, "BARON_NASHOR": "#8b008b", "RIFTHERALD": WARNING}
        OBJ_NAME  = {"DRAGON": "Dragon", "BARON_NASHOR": "Baron", "RIFTHERALD": "Herald"}

        active = []
        for obj in self.engine.get_all_objectives():
            mtype   = obj.get("monster_type", "")
            respawn = OBJ_RESPAWN.get(mtype, 0)
            if not respawn:
                continue
            kill_ms    = obj["timestamp_ms"]
            respawn_ms = kill_ms + respawn
            if kill_ms <= self._current_ms < respawn_ms:
                remaining = (respawn_ms - self._current_ms) // 1000
                gx, gy = OBJ_POS.get(mtype, (0, 0))
                active.append({"type": mtype, "remaining_s": remaining, "gx": gx, "gy": gy})

        for i, (ov, tx) in enumerate(self._obj_timer_items):
            if i < len(active):
                t   = active[i]
                cx, cy = self.engine.game_to_canvas(t["gx"], t["gy"], CANVAS_SIZE)
                r   = 18
                col = OBJ_COLOR.get(t["type"], TEXT_DIM)
                self.canvas.coords(ov, cx-r, cy-r, cx+r, cy+r)
                self.canvas.itemconfigure(ov, outline=col, width=2, state="normal")
                m, s = divmod(t["remaining_s"], 60)
                self.canvas.coords(tx, cx, cy)
                self.canvas.itemconfigure(tx, text=f"{t['type'][0]} {m}:{s:02d}",
                                           fill=col, state="normal")
            else:
                self.canvas.itemconfigure(ov, state="hidden")
                self.canvas.itemconfigure(tx, state="hidden")

        # Side panel labels
        for w in self._obj_frame.winfo_children():
            w.destroy()

        if active:
            self._section_title(self._obj_frame, "OBJETIVOS")
            for t in active:
                col = OBJ_COLOR.get(t["type"], TEXT_DIM)
                m, s = divmod(t["remaining_s"], 60)
                tk.Label(
                    self._obj_frame,
                    text=f"  {OBJ_NAME.get(t['type'], t['type'])}: {m}:{s:02d}",
                    font=("Consolas", 9, "bold"), bg=BG_MEDIUM, fg=col, anchor=tk.W
                ).pack(fill=tk.X, padx=4, pady=1)

    def _update_gold_graph(self):
        stats      = self.engine.get_stats_at(self._current_ms)
        tg         = stats.get(self.engine.target_pid, {}).get("gold", 0)
        og         = stats.get(self.engine.get_opponent_pid(), {}).get("gold", 0)
        diff       = tg - og
        minute     = self._current_ms // 60000

        if not self._gold_history or self._gold_history[-1][0] // 60000 < minute:
            self._gold_history.append((self._current_ms, diff))
        else:
            self._gold_history[-1] = (self._current_ms, diff)

        gc = self._gold_graph
        gc.delete("all")
        w, h = GOLD_GRAPH_W, GOLD_GRAPH_H
        my   = h // 2

        gc.create_line(0, my, w, my, fill=BORDER, width=1, dash=(2, 4))

        if len(self._gold_history) < 2:
            return

        max_d  = max(abs(d) for _, d in self._gold_history)
        max_d  = max(max_d, 500)
        sy     = (my - 4) / max_d
        dur    = max(self.engine.game_duration_ms, 1)
        pts    = [(ms/dur*w, my - d*sy) for ms, d in self._gold_history]

        if len(pts) >= 2:
            last_d = self._gold_history[-1][1]
            flat_fill = [coord for p in [(pts[0][0], my)] + pts + [(pts[-1][0], my)]
                         for coord in p]
            gc.create_polygon(*flat_fill, fill=SUCCESS_DIM if last_d >= 0 else DANGER_DIM, outline="")
            flat_line = [coord for p in pts for coord in p]
            gc.create_line(*flat_line, fill=SUCCESS if last_d >= 0 else DANGER, width=2, smooth=True)

        gc.create_text(4, 4,    text=f"+{max_d//1000:.0f}k", anchor=tk.NW, fill=TEXT_DIM, font=("Segoe UI",6))
        gc.create_text(4, h-4,  text=f"-{max_d//1000:.0f}k", anchor=tk.SW, fill=TEXT_DIM, font=("Segoe UI",6))

    # ─────────────────────────────────────────────────────────────────
    #  PLAYBACK CONTROLS
    # ─────────────────────────────────────────────────────────────────

    def _toggle_play_pause(self):
        self._is_playing = not self._is_playing
        self._last_tick  = time.perf_counter()
        self._update_play_button()

    def _update_play_button(self):
        if self._is_playing:
            self._play_btn.config(text="  ▐▐  PAUSE  ", bg=DANGER)
            self._play_btn._normal_bg = DANGER
            self._play_btn._hover_bg  = "#c03030"
        else:
            self._play_btn.config(text="  ▶  PLAY  ", bg=ACCENT)
            self._play_btn._normal_bg = ACCENT
            self._play_btn._hover_bg  = "#4090e0"

    def _set_speed(self, speed):
        self._speed = speed
        for spd, btn in self._speed_buttons.items():
            active = spd == speed
            btn.config(bg=ACCENT if active else BG_LIGHT,
                       fg=TEXT_BRIGHT if active else TEXT_DIM)
            btn._normal_bg = ACCENT if active else BG_LIGHT
            btn._hover_bg  = ACCENT if active else BG_HOVER

    def _seek(self, target_ms):
        self._current_ms = max(0, min(target_ms, self.engine.game_duration_ms))
        for item in self._ward_items.values():
            self.canvas.delete(item)
        self._ward_items.clear()
        for ov, arc, tx in self._recall_items.values():
            for itm in (ov, arc, tx):
                self.canvas.itemconfigure(itm, state="hidden")
        for ov in self._levelup_items.values():
            self.canvas.itemconfigure(ov, state="hidden")
        for tx in self._special_pool:
            self.canvas.itemconfigure(tx, state="hidden")

    def _toggle_champion(self, pid):
        visible = self._visible[pid].get()
        state   = "normal" if visible else "hidden"
        for store in (self._champ_items, self._champ_labels, self._champ_shadows):
            itm = store.get(pid)
            if itm:
                self.canvas.itemconfigure(itm, state=state)

    def _toggle_all_towers(self):
        self._towers_visible = not self._towers_visible
        state = "normal" if self._towers_visible else "hidden"
        for rect, txt in self._tower_items.values():
            self.canvas.itemconfigure(rect, state=state)
            self.canvas.itemconfigure(txt,  state=state)

    def _toggle_all_wards(self):
        self._wards_visible = not self._wards_visible
        if not self._wards_visible:
            for item in self._ward_items.values():
                self.canvas.delete(item)
            self._ward_items.clear()

    # ─────────────────────────────────────────────────────────────────
    #  TIMELINE INTERACTION
    # ─────────────────────────────────────────────────────────────────

    def _on_timeline_click(self, event):
        self._seek_from_timeline(event.x)

    def _on_timeline_drag(self, event):
        self._seek_from_timeline(event.x)

    def _seek_from_timeline(self, x):
        w = self.timeline_canvas.winfo_width()
        if w < 50:
            return
        pad   = 28
        ratio = max(0.0, min(1.0, (x - pad) / max(w - pad * 2, 1)))
        self._seek(int(ratio * self.engine.game_duration_ms))

    # ─────────────────────────────────────────────────────────────────
    #  CLEANUP
    # ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        if self._after_id:
            self.win.after_cancel(self._after_id)
            self._after_id = None
        self.win.destroy()
