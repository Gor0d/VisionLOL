# -*- coding: utf-8 -*-
"""
TeamViewer - Aba de gerenciamento e acompanhamento de roster de time.
Desenvolvido para paiN Gaming (CBLOL) — rastreia soloq dos 5 jogadores.
"""

import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser, filedialog
import threading
import json
import os
from PIL import Image, ImageTk

# ═══════════════════════════════════════════════════════════════════════
#  PALETA  (alinhada ao ReplayViewer / DashboardViewer)
# ═══════════════════════════════════════════════════════════════════════
BG_DARKEST  = "#0d1117"
BG_DARK     = "#161b22"
BG_MEDIUM   = "#1c2129"
BG_LIGHT    = "#21262d"
BG_HOVER    = "#2d333b"
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

DEFAULT_TEAM = {
    "name":         "Meu Time",
    "subtitle":     "BR1",
    "banner_color": "#1a3a5f",
    "logo_path":    "",
}

# ═══════════════════════════════════════════════════════════════════════
#  ROSTER PADRÃO (editável via ⚙ na aba Time)
# ═══════════════════════════════════════════════════════════════════════
DEFAULT_ROSTER = [
    {"game_name": "Robo",     "tag_line": "BR1",  "role": "TOP",     "display": "Robo"},
    {"game_name": "Cariok",   "tag_line": "BR1",  "role": "JUNGLE",  "display": "Cariok"},
    {"game_name": "Tinowns",  "tag_line": "BR1",  "role": "MID",     "display": "Tinowns"},
    {"game_name": "Trigger",  "tag_line": "BR1",  "role": "ADC",     "display": "Trigger"},
    {"game_name": "Kuri",     "tag_line": "BR1",  "role": "SUPPORT", "display": "Kuri"},
]

ROSTER_FILE = os.path.join(os.path.dirname(__file__), "..", "team_roster.json")
ICON_SIZE   = 36   # ícone do campeão nos cards
HISTORY_N  = 10   # últimas N partidas para resumo


# ═══════════════════════════════════════════════════════════════════════
#  TEAM VIEWER
# ═══════════════════════════════════════════════════════════════════════
class TeamViewer(tk.Frame):
    """Frame que representa a aba 'Time' no notebook principal."""

    def __init__(self, parent, match_api, map_visualizer, root,
                 scrim_server=None):
        super().__init__(parent, bg=BG_DARKEST)
        self.match_api    = match_api
        self.map_viz      = map_visualizer
        self.root_window  = root         # janela raiz (para abrir Toplevels)
        self.scrim_server = scrim_server  # ScrimServer | None

        self._roster: list[dict]            = []   # [{game_name, tag_line, role, display, ...}]
        self._player_cards: list[PlayerCard] = []

        self._load_roster()
        self._build_ui()
        self._refresh_all(auto=True)
        # Live check 15s após startup (dá tempo para o fetch inicial completar)
        self.after(15_000, self._periodic_live_check)
        # Auto-refresh de dados a cada 10 minutos
        self.after(600_000, self._periodic_refresh)

    # ─────────────────────────────────────────────────────────────────
    #  PERSISTÊNCIA DO ROSTER
    # ─────────────────────────────────────────────────────────────────

    def _load_roster(self):
        try:
            with open(ROSTER_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # backward compat: formato antigo era só lista de jogadores
                self._team_cfg = dict(DEFAULT_TEAM)
                self._roster = data
                self._save_roster()
            else:
                self._team_cfg = {**DEFAULT_TEAM, **data.get("team", {})}
                self._roster = data.get("players", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self._team_cfg = dict(DEFAULT_TEAM)
            self._roster = [dict(p) for p in DEFAULT_ROSTER]
            self._save_roster()

    def _save_roster(self):
        try:
            with open(ROSTER_FILE, "w", encoding="utf-8") as f:
                json.dump({"team": self._team_cfg, "players": self._roster},
                          f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────
    #  LAYOUT PRINCIPAL
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Banner do time (customizável via ⚙)
        self._build_header()

        # Container central com os cards dos jogadores
        self._cards_frame = tk.Frame(self, bg=BG_DARKEST)
        self._cards_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        # Cabeçalho da tabela
        self._build_table_header()

        # Cards dos jogadores
        self._player_cards = []
        for p in self._roster:
            card = PlayerCard(
                self._cards_frame, p,
                self.match_api, self.map_viz, self.root_window,
                on_edit=self._on_edit_player,
                on_remove=self._on_remove_player,
                on_save=self._save_roster,
            )
            card.pack(fill=tk.X, pady=1)
            self._player_cards.append(card)

        # Rodapé com agregados do time
        self._footer_frame = tk.Frame(self, bg=BG_DARK, height=36)
        self._footer_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        self._footer_frame.pack_propagate(False)

        self._footer_lbl = tk.Label(
            self._footer_frame, text="Aguardando dados…",
            font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_DIM
        )
        self._footer_lbl.pack(side=tk.LEFT, padx=10, pady=8)

    def _build_header(self):
        color = self._team_cfg.get("banner_color", DEFAULT_TEAM["banner_color"])

        hdr = tk.Frame(self, bg=color, height=58)
        hdr.pack(fill=tk.X, padx=12, pady=(8, 6))
        hdr.pack_propagate(False)
        self._hdr = hdr

        # Logo / nome do time
        logo_frame = tk.Frame(hdr, bg=color)
        logo_frame.pack(side=tk.LEFT, padx=14, pady=8)

        self._team_logo_ph = None
        logo_path = self._team_cfg.get("logo_path", "")
        logo_loaded = False
        if logo_path and os.path.isfile(logo_path):
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                target_h = 42
                ratio = target_h / logo_img.height
                target_w = int(logo_img.width * ratio)
                logo_img = logo_img.resize((target_w, target_h), Image.LANCZOS)
                self._team_logo_ph = ImageTk.PhotoImage(logo_img)
                tk.Label(logo_frame, image=self._team_logo_ph,
                         bg=color).pack(side=tk.LEFT, padx=(0, 10))
                logo_loaded = True
            except Exception:
                pass

        if not logo_loaded:
            tk.Label(logo_frame, text=self._team_cfg.get("name", "Meu Time"),
                     font=("Segoe UI", 18, "bold"),
                     bg=color, fg=TEXT_BRIGHT).pack(side=tk.LEFT)

        subtitle = self._team_cfg.get("subtitle", "")
        if subtitle:
            tk.Label(logo_frame, text=f"  {subtitle}",
                     font=("Segoe UI", 10),
                     bg=color, fg="#a8c4e0").pack(side=tk.LEFT, pady=4)

        # Botões de ação no lado direito
        btn_area = tk.Frame(hdr, bg=color)
        btn_area.pack(side=tk.RIGHT, padx=14, pady=10)

        _hbtn(btn_area, "⚙ Time", self._edit_team_config,
              bg="#2d333b").pack(side=tk.LEFT, padx=(0, 6))
        _hbtn(btn_area, "＋ Jogador", self._on_add_player,
              bg="#1a5f3f").pack(side=tk.LEFT, padx=(0, 6))
        _hbtn(btn_area, "↺ Atualizar tudo", self._refresh_all,
              bg="#1a3a5f").pack(side=tk.LEFT, padx=(0, 6))
        _hbtn(btn_area, "🕸 Radar do Time", self._open_team_radar,
              bg="#2a1a5f").pack(side=tk.LEFT, padx=(0, 6))
        _hbtn(btn_area, "⚔ Scrims", self._open_scrims,
              bg="#5f1a1a").pack(side=tk.LEFT)

        self._last_update_lbl = tk.Label(
            hdr, text="", font=("Segoe UI", 8),
            bg=color, fg="#a8c4e0"
        )
        self._last_update_lbl.pack(side=tk.RIGHT, padx=4)

    def _rebuild_header(self):
        self._hdr.destroy()
        self._build_header()
        self._hdr.pack_configure(before=self._cards_frame)

    def _edit_team_config(self):
        color = self._team_cfg.get("banner_color", DEFAULT_TEAM["banner_color"])

        dlg = tk.Toplevel(self.root_window)
        dlg.title("Configurar Time")
        dlg.resizable(False, False)
        dlg.configure(bg=BG_DARK)
        dlg.grab_set()

        pad = {"padx": 12, "pady": 6}

        def _lbl(text, row):
            tk.Label(dlg, text=text, bg=BG_DARK, fg=TEXT_COLOR,
                     font=("Segoe UI", 10), anchor="w").grid(
                row=row, column=0, sticky="w", **pad)

        def _entry(var, row, width=28):
            e = tk.Entry(dlg, textvariable=var, bg=BG_LIGHT, fg=TEXT_BRIGHT,
                         width=width, font=("Segoe UI", 10),
                         insertbackground=TEXT_BRIGHT, relief=tk.FLAT)
            e.grid(row=row, column=1, columnspan=2, sticky="ew",
                   padx=(0, 12), pady=6)
            return e

        # Nome do time
        name_var = tk.StringVar(value=self._team_cfg.get("name", ""))
        _lbl("Nome do Time:", 0)
        _entry(name_var, 0)

        # Legenda (ex: "CBLOL · BR1")
        sub_var = tk.StringVar(value=self._team_cfg.get("subtitle", ""))
        _lbl("Legenda:", 1)
        _entry(sub_var, 1)

        # Cor do banner
        color_var = tk.StringVar(value=color)
        _lbl("Cor do Banner:", 2)

        color_row = tk.Frame(dlg, bg=BG_DARK)
        color_row.grid(row=2, column=1, columnspan=2, sticky="ew",
                       padx=(0, 12), pady=6)

        color_entry = tk.Entry(color_row, textvariable=color_var,
                               bg=BG_LIGHT, fg=TEXT_BRIGHT, width=10,
                               font=("Segoe UI", 10),
                               insertbackground=TEXT_BRIGHT, relief=tk.FLAT)
        color_entry.pack(side=tk.LEFT)

        color_preview = tk.Frame(color_row, bg=color_var.get(), width=24, height=24)
        color_preview.pack(side=tk.LEFT, padx=6)
        color_preview.pack_propagate(False)

        def pick_color():
            result = colorchooser.askcolor(
                color=color_var.get(), parent=dlg, title="Cor do Banner")
            if result[1]:
                color_var.set(result[1])
                color_preview.config(bg=result[1])

        color_entry.bind("<FocusOut>",
                         lambda e: color_preview.config(bg=color_var.get()))

        tk.Button(color_row, text="🎨", command=pick_color,
                  bg=BG_LIGHT, fg=TEXT_COLOR, font=("Segoe UI", 10),
                  relief=tk.FLAT, cursor="hand2", padx=6
                  ).pack(side=tk.LEFT)

        # Logo
        logo_var = tk.StringVar(value=self._team_cfg.get("logo_path", ""))
        _lbl("Logo (PNG/JPG):", 3)

        logo_row = tk.Frame(dlg, bg=BG_DARK)
        logo_row.grid(row=3, column=1, columnspan=2, sticky="ew",
                      padx=(0, 12), pady=6)

        tk.Entry(logo_row, textvariable=logo_var, bg=BG_LIGHT, fg=TEXT_BRIGHT,
                 width=22, font=("Segoe UI", 10),
                 insertbackground=TEXT_BRIGHT, relief=tk.FLAT).pack(side=tk.LEFT)

        def browse_logo():
            path = filedialog.askopenfilename(
                parent=dlg, title="Selecionar Logo",
                filetypes=[("Imagens", "*.png *.jpg *.jpeg"), ("Todos", "*.*")])
            if path:
                logo_var.set(path)

        tk.Button(logo_row, text="📁 Browse", command=browse_logo,
                  bg=BG_LIGHT, fg=TEXT_COLOR, font=("Segoe UI", 9),
                  relief=tk.FLAT, cursor="hand2", padx=8, pady=2
                  ).pack(side=tk.LEFT, padx=(6, 0))

        # Botão salvar
        def save():
            self._team_cfg["name"]         = name_var.get().strip() or "Meu Time"
            self._team_cfg["subtitle"]     = sub_var.get().strip()
            self._team_cfg["banner_color"] = color_var.get().strip() or DEFAULT_TEAM["banner_color"]
            self._team_cfg["logo_path"]    = logo_var.get().strip()
            self._save_roster()
            self._rebuild_header()
            dlg.destroy()

        tk.Button(dlg, text="Salvar", command=save,
                  bg=SUCCESS, fg=TEXT_BRIGHT,
                  font=("Segoe UI", 11, "bold"),
                  relief=tk.FLAT, cursor="hand2", padx=20, pady=8
                  ).grid(row=4, column=0, columnspan=3, pady=(8, 14))

    def _build_table_header(self):
        row = tk.Frame(self._cards_frame, bg=BG_MEDIUM)
        row.pack(fill=tk.X, pady=(0, 2))

        _hcol(row, "ROLE",   5)
        _hcol(row, "JOGADOR", 14)
        _hcol(row, "TOP CAMPEÕES",   28)
        _hcol(row, "ÚLTIMAS 10",     18)
        _hcol(row, "WR",      6)
        _hcol(row, "KDA",     8)
        _hcol(row, "",       12)   # botões

    # ─────────────────────────────────────────────────────────────────
    #  REFRESH
    # ─────────────────────────────────────────────────────────────────

    def _refresh_all(self, auto=False):
        """Inicia fetch de stats de todos os jogadores em background."""
        for card in self._player_cards:
            card.start_fetch()
        if not auto:
            import time as _time
            self._last_update_lbl.config(
                text=f"Atualizado às {_time.strftime('%H:%M')}"
            )
        # Agenda atualização do rodapé após delay
        self.after(3000, self._update_footer)

    def _periodic_refresh(self):
        """Auto-refresh a cada 10 minutos."""
        self._refresh_all(auto=True)
        self.after(600_000, self._periodic_refresh)

    def _periodic_live_check(self):
        """Verifica status ao vivo de cada jogador com intervalo escalonado."""
        for i, card in enumerate(self._player_cards):
            self.after(i * 4_000, card.check_live)   # 4s entre cada jogador
        self.after(60_000, self._periodic_live_check)

    def _update_footer(self):
        """Agrega estatísticas de todos os cards prontos."""
        total_games = wins = 0
        for card in self._player_cards:
            g = card.stats.get("games", 0)
            w = card.stats.get("wins", 0)
            total_games += g
            wins += w
        if total_games > 0:
            wr = int(wins / total_games * 100)
            wr_col = SUCCESS if wr >= 50 else DANGER
            self._footer_lbl.config(
                text=f"Time — {total_games} partidas rastreadas  ·  WR coletivo: {wr}%",
                fg=wr_col
            )
        # Reagenda para quando mais cards terminarem
        if any(c.stats.get("loading") for c in self._player_cards):
            self.after(2000, self._update_footer)

    # ─────────────────────────────────────────────────────────────────
    #  EDIÇÃO DO ROSTER
    # ─────────────────────────────────────────────────────────────────

    def _open_team_radar(self):
        """Abre janela com mini-radares de todos os jogadores do time."""
        from riot_api.performance_radar import TeamRadarView, compute_player_metrics, normalize_metrics

        players_data = []
        for card in self._player_cards:
            if not card.stats.get("summaries"):
                continue
            puuid     = card.stats.get("puuid")
            summaries = card.stats["summaries"]
            cache     = {mid: self.match_api.get_match_data(mid)
                         for mid, _, _ in summaries}
            role      = card.player.get("role", "MID")
            raw       = compute_player_metrics(summaries, cache, puuid)
            norm      = normalize_metrics(raw, role)
            players_data.append({
                "player":  card.player,
                "raw":     raw,
                "norm":    norm,
                "n_games": len(summaries),
            })

        if not players_data:
            messagebox.showinfo(
                "Aguarde",
                "Aguarde o carregamento dos dados de todos os jogadores.",
                parent=self.root_window
            )
            return

        TeamRadarView(self.root_window, players_data)

    def _open_scrims(self):
        """Abre o dashboard de scrims."""
        from riot_api.scrim_dashboard import ScrimDashboard
        ScrimDashboard(
            self.root_window,
            match_api=self.match_api,
            roster=self._roster,
            map_visualizer=self.map_viz,
            server=self.scrim_server,
        )

    def _on_add_player(self):
        name = simpledialog.askstring(
            "Adicionar Jogador",
            "Riot ID (ex: Tinowns#BR1):",
            parent=self.root_window
        )
        if not name or "#" not in name:
            return
        game_name, tag = name.split("#", 1)
        role = simpledialog.askstring(
            "Role", "Role (TOP / JUNGLE / MID / ADC / SUPPORT):",
            parent=self.root_window
        ) or "MID"

        player = {"game_name": game_name.strip(),
                  "tag_line":  tag.strip(),
                  "role":      role.strip().upper(),
                  "display":   game_name.strip()}
        self._roster.append(player)
        self._save_roster()
        self._rebuild_cards()

    def _on_edit_player(self, player: dict):
        old_id = f"{player['game_name']}#{player['tag_line']}"
        new_id = simpledialog.askstring(
            "Editar Riot ID",
            f"Riot ID atual: {old_id}\nNovo Riot ID:",
            parent=self.root_window,
            initialvalue=old_id,
        )
        if not new_id or "#" not in new_id:
            return
        g, t = new_id.split("#", 1)
        player["game_name"] = g.strip()
        player["tag_line"]  = t.strip()
        player["display"]   = g.strip()
        self._save_roster()
        self._rebuild_cards()

    def _on_remove_player(self, player: dict):
        ok = messagebox.askyesno(
            "Remover", f"Remover {player['display']} do roster?",
            parent=self.root_window
        )
        if ok:
            self._roster = [p for p in self._roster
                            if p is not player]
            self._save_roster()
            self._rebuild_cards()

    def _rebuild_cards(self):
        for c in self._player_cards:
            c.destroy()
        self._player_cards.clear()
        for p in self._roster:
            card = PlayerCard(
                self._cards_frame, p,
                self.match_api, self.map_viz, self.root_window,
                on_edit=self._on_edit_player,
                on_remove=self._on_remove_player,
                on_save=self._save_roster,
            )
            card.pack(fill=tk.X, pady=1)
            self._player_cards.append(card)
        self._refresh_all()


# ═══════════════════════════════════════════════════════════════════════
#  PLAYER CARD
# ═══════════════════════════════════════════════════════════════════════
class PlayerCard(tk.Frame):
    """Linha de um jogador no roster: role | nome | top camps | histórico | WR | botões.
    Suporta múltiplas contas (main + smurfs/alts) com stats agregadas.
    """

    def __init__(self, parent, player: dict, match_api, map_viz,
                 root_window, on_edit, on_remove, on_save=None):
        super().__init__(parent, bg=BG_DARK, pady=0)

        self.player      = player
        self.match_api   = match_api
        self.map_viz     = map_viz
        self.root_window = root_window
        self._on_edit    = on_edit
        self._on_remove  = on_remove
        self._on_save    = on_save or (lambda: None)

        self.stats: dict = {"loading": False}
        self._icon_refs: list[ImageTk.PhotoImage] = []   # evita gc
        self._destroyed = False

        self._build()

    def destroy(self):
        self._destroyed = True
        super().destroy()

    # ─────────────────────────────────────────────────────────────────
    #  CONTAS ALTERNATIVAS
    # ─────────────────────────────────────────────────────────────────

    def _rebuild_alts_row(self):
        """Reconstrói a linha de contas alternativas."""
        for w in self._alts_row.winfo_children():
            w.destroy()

        alts = self.player.get("alt_accounts", [])

        # Ícone + label "alts:"
        tk.Label(self._alts_row, text="⚡ alts:",
                 font=("Segoe UI", 7, "bold"),
                 bg=BG_MEDIUM, fg=TEXT_DIM).pack(side=tk.LEFT, padx=(6, 4), pady=3)

        # Chips de cada conta alt
        for alt in alts:
            rid = f"{alt['game_name']}#{alt['tag_line']}"
            chip = tk.Frame(self._alts_row, bg=BG_LIGHT)
            chip.pack(side=tk.LEFT, padx=(0, 3), pady=2)
            tk.Label(chip, text=rid,
                     font=("Segoe UI", 7), bg=BG_LIGHT, fg=TEXT_COLOR,
                     padx=5, pady=2).pack(side=tk.LEFT)
            tk.Button(chip, text="×",
                      font=("Segoe UI", 7, "bold"),
                      bg=BG_LIGHT, fg=TEXT_DIM,
                      relief=tk.FLAT, cursor="hand2",
                      padx=3, pady=1,
                      command=lambda a=alt: self._on_remove_alt(a)
                      ).pack(side=tk.LEFT)

        # Botão adicionar conta (sempre visível)
        tk.Button(self._alts_row, text="＋ conta",
                  font=("Segoe UI", 7, "bold"),
                  bg=BG_DARKEST, fg=ACCENT,
                  relief=tk.FLAT, cursor="hand2",
                  padx=6, pady=2,
                  command=self._on_add_alt
                  ).pack(side=tk.LEFT, padx=(4 if alts else 0, 0))

    def _on_add_alt(self):
        """Adiciona uma conta alternativa via diálogo."""
        name = self.player.get("display", self.player.get("game_name", ""))
        riot_id = simpledialog.askstring(
            "Adicionar Conta Alternativa",
            f"Riot ID da smurf/alt de {name}:\n(formato: NomeIngame#TAG)",
            parent=self.root_window
        )
        if not riot_id or "#" not in riot_id:
            return
        game_name, tag = riot_id.split("#", 1)
        game_name = game_name.strip()
        tag       = tag.strip()
        if not game_name or not tag:
            return

        # Evita duplicata
        alts = self.player.setdefault("alt_accounts", [])
        for existing in alts:
            if existing["game_name"].lower() == game_name.lower() \
                    and existing["tag_line"].lower() == tag.lower():
                messagebox.showinfo("Já existe",
                                    f"{riot_id} já está na lista.",
                                    parent=self.root_window)
                return

        alts.append({"game_name": game_name, "tag_line": tag})
        self._on_save()
        self._rebuild_alts_row()
        # Re-fetch para incluir a nova conta
        self.stats = {"loading": False}
        self.start_fetch()

    def _on_remove_alt(self, alt: dict):
        """Remove uma conta alternativa."""
        rid = f"{alt['game_name']}#{alt['tag_line']}"
        ok  = messagebox.askyesno("Remover alt",
                                  f"Remover conta {rid}?",
                                  parent=self.root_window)
        if not ok:
            return
        self.player["alt_accounts"] = [
            a for a in self.player.get("alt_accounts", [])
            if not (a["game_name"] == alt["game_name"]
                    and a["tag_line"] == alt["tag_line"])
        ]
        self._on_save()
        self._rebuild_alts_row()
        # Re-fetch sem a conta removida
        self.stats = {"loading": False}
        self.start_fetch()

    # ─────────────────────────────────────────────────────────────────
    #  LAYOUT DO CARD
    # ─────────────────────────────────────────────────────────────────

    def _build(self):
        role  = self.player.get("role", "MID")
        color = ROLE_COLORS.get(role, ACCENT)

        # Barra lateral colorida por role
        bar = tk.Frame(self, bg=color, width=4)
        bar.pack(side=tk.LEFT, fill=tk.Y)

        # Container de duas linhas: principal + contas alternativas
        content = tk.Frame(self, bg=BG_DARK)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── LINHA PRINCIPAL ───────────────────────────────────────────
        inner = tk.Frame(content, bg=BG_DARK)
        inner.pack(fill=tk.X, padx=(6, 4), pady=(5, 3))

        # ROLE
        role_lbl = tk.Label(inner, text=role[:3], font=("Segoe UI", 8, "bold"),
                            bg=color, fg=BG_DARKEST, width=4, pady=1)
        role_lbl.pack(side=tk.LEFT, padx=(0, 8))

        # NOME
        name_frame = tk.Frame(inner, bg=BG_DARK, width=220)
        name_frame.pack(side=tk.LEFT, padx=(0, 8), fill=tk.Y)
        name_frame.pack_propagate(False)

        self._name_lbl = tk.Label(
            name_frame,
            text=self.player.get("display", self.player["game_name"]),
            font=("Segoe UI", 11, "bold"),
            bg=BG_DARK, fg=TEXT_BRIGHT, anchor="w"
        )
        self._name_lbl.pack(fill=tk.X)
        self._riot_id_lbl = tk.Label(
            name_frame,
            text=f"{self.player['game_name']}#{self.player['tag_line']}",
            font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM, anchor="w"
        )
        self._riot_id_lbl.pack(fill=tk.X)

        # TOP CAMPEÕES (3 ícones)
        self._champ_frame = tk.Frame(inner, bg=BG_DARK, width=160)
        self._champ_frame.pack(side=tk.LEFT, padx=(0, 8), fill=tk.Y)
        self._champ_frame.pack_propagate(False)

        self._champ_loading = tk.Label(
            self._champ_frame, text="…", font=("Segoe UI", 9),
            bg=BG_DARK, fg=TEXT_DIM
        )
        self._champ_loading.pack(side=tk.LEFT, pady=4)

        # ÚLTIMAS 10 PARTIDAS
        self._hist_frame = tk.Frame(inner, bg=BG_DARK, width=130)
        self._hist_frame.pack(side=tk.LEFT, padx=(0, 8))
        self._hist_frame.pack_propagate(False)

        self._hist_loading = tk.Label(
            self._hist_frame, text="…", font=("Segoe UI", 9),
            bg=BG_DARK, fg=TEXT_DIM
        )
        self._hist_loading.pack(side=tk.LEFT, pady=4)

        # WR%
        self._wr_lbl = tk.Label(
            inner, text="–%", font=("Segoe UI", 12, "bold"),
            bg=BG_DARK, fg=TEXT_DIM, width=5
        )
        self._wr_lbl.pack(side=tk.LEFT, padx=(0, 6))

        # KDA
        self._kda_lbl = tk.Label(
            inner, text="–.–", font=("Segoe UI", 10),
            bg=BG_DARK, fg=TEXT_DIM, width=6
        )
        self._kda_lbl.pack(side=tk.LEFT, padx=(0, 8))

        # LIVE BADGE
        self._live_badge = tk.Label(
            inner, text="", font=("Segoe UI", 8, "bold"),
            bg=BG_DARK, fg=DANGER, width=7
        )
        self._live_badge.pack(side=tk.LEFT, padx=(0, 6))

        # BOTÕES
        btn_area = tk.Frame(inner, bg=BG_DARK)
        btn_area.pack(side=tk.RIGHT, padx=4)

        b_dash = _hbtn(btn_area, "📊", self._open_dashboard, bg=BG_LIGHT, width=3)
        b_dash.pack(side=tk.LEFT, padx=2)
        _Tooltip(b_dash, "Dashboard de desempenho — gráficos e histórico detalhado")

        b_radar = _hbtn(btn_area, "🕸", self._open_radar, bg=BG_LIGHT, width=3)
        b_radar.pack(side=tk.LEFT, padx=2)
        _Tooltip(b_radar, "Radar de performance — KDA, CS/min, visão, gold, dano e kill participation")

        b_edit = _hbtn(btn_area, "✏", lambda: self._on_edit(self.player), bg=BG_LIGHT, width=3)
        b_edit.pack(side=tk.LEFT, padx=2)
        _Tooltip(b_edit, "Editar Riot ID ou nome do jogador")

        b_rem = _hbtn(btn_area, "✕", lambda: self._on_remove(self.player), bg="#3d1114", width=3)
        b_rem.pack(side=tk.LEFT, padx=2)
        _Tooltip(b_rem, "Remover jogador do roster")

        # ── LINHA DE CONTAS ALTERNATIVAS ──────────────────────────────
        self._alts_row = tk.Frame(content, bg=BG_MEDIUM)
        self._alts_row.pack(fill=tk.X, padx=(6, 4), pady=(0, 4))
        self._rebuild_alts_row()

        # Separador
        tk.Frame(content, bg=BORDER, height=1).pack(fill=tk.X)

    # ─────────────────────────────────────────────────────────────────
    #  FETCH DE DADOS (background thread)
    # ─────────────────────────────────────────────────────────────────

    def start_fetch(self):
        if self.stats.get("loading"):
            return
        self.stats = {"loading": True}
        # Libera referências a ícones anteriores para permitir GC dos PhotoImages
        self._icon_refs.clear()
        # Recria os indicadores de carregamento (podem ter sido destruídos pelo _update_ui)
        for w in self._champ_frame.winfo_children():
            w.destroy()
        self._champ_loading = tk.Label(
            self._champ_frame, text="carregando…", font=("Segoe UI", 9),
            bg=BG_DARK, fg=TEXT_DIM
        )
        self._champ_loading.pack(side=tk.LEFT, pady=4)
        for w in self._hist_frame.winfo_children():
            w.destroy()
        self._hist_loading = tk.Label(
            self._hist_frame, text="carregando…", font=("Segoe UI", 9),
            bg=BG_DARK, fg=TEXT_DIM
        )
        self._hist_loading.pack(side=tk.LEFT, pady=4)
        self._wr_lbl.config(text="–%", fg=TEXT_DIM)
        self._kda_lbl.config(text="–.–", fg=TEXT_DIM)
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        """Busca dados da conta principal + todas as alts e agrega as stats."""
        try:
            # Lista de todas as contas (main primeiro, depois alts)
            accounts = [
                {"game_name": self.player["game_name"],
                 "tag_line":  self.player["tag_line"]}
            ] + list(self.player.get("alt_accounts", []))

            primary_puuid = None
            all_summaries = []

            for i, acc in enumerate(accounts):
                puuid = self.match_api.get_puuid(acc["game_name"], acc["tag_line"])
                if not puuid:
                    continue
                if primary_puuid is None:
                    primary_puuid = puuid   # conta principal para o dashboard

                # Ranked primeiro, fallback sem filtro
                match_ids = self.match_api.get_match_ids(
                    puuid, count=HISTORY_N, queue=420
                )
                if not match_ids:
                    match_ids = self.match_api.get_match_ids(puuid, count=HISTORY_N)

                for mid in match_ids:
                    data = self.match_api.get_match_data(mid)
                    if data:
                        s = self.match_api.get_match_summary(data, puuid)
                        if s:
                            # Guarda apenas o resumo compacto; dados completos ficam no cache em disco
                            all_summaries.append((mid, s, None))

            if not primary_puuid:
                self._set_error("Riot ID não encontrado")
                return
            if not all_summaries:
                self._set_error("Sem partidas recentes")
                return

            self._process_summaries(primary_puuid, all_summaries)

        except Exception as e:
            self._set_error(str(e)[:30])

    def _process_summaries(self, puuid, summaries):
        wins  = sum(1 for _, s, _ in summaries if s.get("win"))
        total = len(summaries)
        wr    = int(wins / total * 100) if total else 0

        # KDA médio
        kills = deaths = assists = 0
        for _, s, _ in summaries:
            try:
                k, d, a = (int(x) for x in s.get("kda", "0/0/0").split("/"))
                kills += k; deaths += d; assists += a
            except ValueError:
                pass
        kda_v = (kills + assists) / max(deaths, 1)

        # Top 3 campeões
        champ_count: dict[str, int] = {}
        for _, s, _ in summaries:
            c = s.get("champion", "")
            if c:
                champ_count[c] = champ_count.get(c, 0) + 1
        top_champs = sorted(champ_count.items(), key=lambda x: x[1], reverse=True)[:3]

        # Histórico binário [True=win, False=loss]
        history = [s.get("win", False) for _, s, _ in summaries]

        self.stats = {
            "loading": False, "puuid": puuid,
            "games": total, "wins": wins, "wr": wr,
            "kda": kda_v, "top_champs": top_champs,
            "history": history,
            "summaries": summaries,
        }

        self.root_window.after(0, self._update_ui)

    def _set_error(self, msg: str):
        self.stats = {"loading": False, "error": msg}
        self.root_window.after(0, self._show_error, msg)

    # ─────────────────────────────────────────────────────────────────
    #  UPDATE DA UI (thread principal)
    # ─────────────────────────────────────────────────────────────────

    def _update_ui(self):
        if self._destroyed:
            return
        try:
            wr    = self.stats.get("wr", 0)
            kda_v = self.stats.get("kda", 0.0)

            # WR
            wr_col = SUCCESS if wr >= 50 else DANGER
            self._wr_lbl.config(text=f"{wr}%", fg=wr_col)

            # KDA
            kda_col = SUCCESS if kda_v >= 3.0 else (WARNING if kda_v >= 2.0 else TEXT_DIM)
            self._kda_lbl.config(text=f"{kda_v:.1f} KDA", fg=kda_col)

            # Top campeões (ícones)
            self._champ_loading.destroy()
            self._icon_refs.clear()
            for i, (champ, count) in enumerate(self.stats.get("top_champs", [])):
                threading.Thread(
                    target=self._load_champ_icon, args=(champ, count, i), daemon=True
                ).start()

            # Histórico (quadradinhos)
            self._hist_loading.destroy()
            for w in self._hist_frame.winfo_children():
                w.destroy()
            for win in self.stats.get("history", []):
                color  = SUCCESS if win else DANGER
                letter = "V" if win else "D"
                tk.Label(self._hist_frame, text=letter,
                         font=("Segoe UI", 8, "bold"),
                         bg=color, fg=BG_DARKEST, width=2
                         ).pack(side=tk.LEFT, padx=1)
        except tk.TclError:
            pass

    def _show_error(self, msg: str):
        if self._destroyed:
            return
        try:
            self._champ_loading.config(text=f"⚠ {msg}", fg=DANGER)
            self._hist_loading.config(text="", fg=TEXT_DIM)
        except tk.TclError:
            pass

    def _load_champ_icon(self, champ: str, count: int, idx: int):
        """Baixa ícone do campeão e atualiza no canvas principal."""
        try:
            img = self.map_viz._download_champion_icon(champ) if self.map_viz else None
            if img:
                img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                ph  = ImageTk.PhotoImage(img)
                self.root_window.after(0, self._place_champ_icon, ph, champ, count)
                return
        except Exception:
            pass
        # Fallback: exibe abreviação do nome do campeão
        self.root_window.after(0, self._place_champ_text, champ, count)

    def _place_champ_icon(self, ph, champ: str, count: int):
        if self._destroyed:
            return
        try:
            self._icon_refs.append(ph)   # evita gc
            f = tk.Frame(self._champ_frame, bg=BG_DARK)
            f.pack(side=tk.LEFT, padx=3)
            tk.Label(f, image=ph, bg=BG_DARK).pack()
            tk.Label(f, text=f"{count}j", font=("Segoe UI", 7),
                     bg=BG_DARK, fg=TEXT_DIM).pack()
        except tk.TclError:
            pass

    def _place_champ_text(self, champ: str, count: int):
        """Fallback quando o ícone do campeão não pôde ser baixado."""
        if self._destroyed:
            return
        try:
            role  = self.player.get("role", "MID")
            color = ROLE_COLORS.get(role, ACCENT)
            abbrev = champ[:4] if champ else "?"
            f = tk.Frame(self._champ_frame, bg=BG_DARK)
            f.pack(side=tk.LEFT, padx=3)
            tk.Label(f, text=abbrev,
                     font=("Segoe UI", 7, "bold"),
                     bg=color, fg=BG_DARKEST,
                     width=4, pady=3).pack()
            tk.Label(f, text=f"{count}j",
                     font=("Segoe UI", 7),
                     bg=BG_DARK, fg=TEXT_DIM).pack()
        except tk.TclError:
            pass

    # ─────────────────────────────────────────────────────────────────
    #  LIVE CHECK
    # ─────────────────────────────────────────────────────────────────

    def check_live(self):
        """Verifica se o jogador está ao vivo (background thread).
        Requer que o puuid já tenha sido obtido via start_fetch().
        """
        if self._destroyed:
            return
        puuid = self.stats.get("puuid")
        if not puuid:
            return
        threading.Thread(target=self._live_thread, args=(puuid,), daemon=True).start()

    def _live_thread(self, puuid: str):
        try:
            in_game = self.match_api.is_in_game(puuid)
            if not self._destroyed:
                self.root_window.after(0, self._set_live_badge, in_game)
        except Exception:
            pass

    def _set_live_badge(self, in_game: bool):
        if self._destroyed:
            return
        try:
            if in_game:
                self._live_badge.config(text="● LIVE", fg=DANGER)
            else:
                self._live_badge.config(text="", fg=DANGER)
        except tk.TclError:
            pass

    # ─────────────────────────────────────────────────────────────────
    #  AÇÕES
    # ─────────────────────────────────────────────────────────────────

    def _open_dashboard(self):
        if not self.stats.get("summaries"):
            messagebox.showinfo(
                "Aguarde", "Dados ainda sendo carregados.\nTente novamente em alguns segundos.",
                parent=self.root_window
            )
            return
        from riot_api.dashboard_viewer import DashboardViewer
        puuid     = self.stats["puuid"]
        summaries = [(mid, s) for mid, s, _ in self.stats["summaries"]]
        cache     = {mid: self.match_api.get_match_data(mid)
                     for mid, _, _ in self.stats["summaries"]}
        DashboardViewer(
            self.root_window, summaries, cache,
            self.map_viz, self.match_api, puuid
        )

    def _open_radar(self):
        if not self.stats.get("summaries"):
            messagebox.showinfo(
                "Aguarde", "Dados ainda sendo carregados.\nTente novamente em alguns segundos.",
                parent=self.root_window
            )
            return
        from riot_api.performance_radar import PlayerRadar
        puuid     = self.stats["puuid"]
        summaries = self.stats["summaries"]   # list[(mid, s, None)]
        cache     = {mid: self.match_api.get_match_data(mid)
                     for mid, _, _ in summaries}
        role      = self.player.get("role", "MID")
        PlayerRadar(
            self.root_window,
            player=self.player,
            summaries=summaries,
            match_data_cache=cache,
            puuid=puuid,
            role=role,
        )


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════

class _Tooltip:
    """Tooltip simples que aparece ao passar o mouse sobre um widget."""

    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 500):
        self._widget   = widget
        self._text     = text
        self._delay_ms = delay_ms
        self._tip_win  = None
        self._after_id = None
        widget.bind("<Enter>",       self._schedule, add="+")
        widget.bind("<Leave>",       self._hide,     add="+")
        widget.bind("<ButtonPress>", self._hide,     add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self._widget.after(self._delay_ms, self._show)

    def _cancel(self):
        if self._after_id:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self._tip_win or not self._widget.winfo_exists():
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2
        y = self._widget.winfo_rooty() - 30
        self._tip_win = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self._text,
            font=("Segoe UI", 8), bg=BG_HOVER, fg=TEXT_COLOR,
            relief=tk.SOLID, borderwidth=1, padx=7, pady=4
        ).pack()

    def _hide(self, _event=None):
        self._cancel()
        if self._tip_win:
            try:
                self._tip_win.destroy()
            except tk.TclError:
                pass
            self._tip_win = None


def _hbtn(parent, text, command, bg=BG_LIGHT, width=None) -> tk.Button:
    """Botão hover compacto para o header e cards."""
    kw = dict(text=text, command=command, bg=bg, fg=TEXT_COLOR,
              font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
              cursor="hand2", padx=8, pady=4)
    if width:
        kw["width"] = width
    btn = tk.Button(parent, **kw)
    hover = BG_HOVER if bg == BG_LIGHT else bg
    btn.bind("<Enter>", lambda e: btn.config(bg=hover))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _hcol(parent, text: str, weight: int):
    """Coluna do cabeçalho da tabela."""
    tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"),
             bg=BG_MEDIUM, fg=TEXT_DIM,
             width=weight, anchor="w", padx=6
             ).pack(side=tk.LEFT, pady=4)
