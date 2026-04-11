# -*- coding: utf-8 -*-
"""
Painel principal do módulo de coaching.
Integra-se ao notebook do VisionLOL como uma aba.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
from datetime import datetime

from ..models.player  import Player, ROLES
from ..services.session_manager import (
    load_players, save_player, delete_player,
    list_sessions, get_upcoming_sessions
)
from .session_view import SessionView
from .goals_view   import GoalsView
from .report_view  import ReportView

BG_DARKEST = "#000000"
BG_DARK    = "#0A0A08"
BG_MEDIUM  = "#111110"
BG_LIGHT   = "#181816"
BORDER     = "#2A2A28"
ACCENT     = "#FF9830"
SUCCESS    = "#50FF50"
DANGER     = "#FF4840"
WARNING    = "#FFCC50"
CYAN       = "#20F0FF"
TEXT       = "#E0E0D8"
DIM        = "#8A8A82"
FONT_MONO  = ("Courier New", 10)
FONT_HEAD  = ("Courier New", 11, "bold")
FONT_SMALL = ("Courier New", 9)
FONT_TITLE = ("Courier New", 13, "bold")

ROLE_COLOR = {
    "TOP":  "#b070ff", "JNG": SUCCESS,
    "MID":  ACCENT,    "ADC": "#ffcc50",
    "SUP":  CYAN,
}


class CoachingDashboard:
    """Painel de coaching — embutido como aba no VisionLOL."""

    def __init__(self, parent, http_client=None, match_api=None, app_root=None):
        self.parent     = parent
        self.http       = http_client
        self.match_api  = match_api
        self.root       = app_root or parent
        self._players:  list[Player] = []
        self._selected: Player | None = None
        self._alerts:   list[str] = []

        self._build()
        self._refresh_players()

    # ═══════════════════════════════════════════════════════════════
    #  LAYOUT
    # ═══════════════════════════════════════════════════════════════

    def _build(self):
        self.parent.configure(bg=BG_DARKEST)

        # ── Header ─────────────────────────────────────────────
        hdr = tk.Frame(self.parent, bg=BG_DARK, height=48)
        hdr.pack(fill=tk.X, padx=8, pady=(8, 0))
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◈ COACHING", bg=BG_DARK, fg=ACCENT,
                 font=FONT_TITLE).pack(side=tk.LEFT, padx=16, pady=8)
        tk.Label(hdr, text="VisionCoach v1.0", bg=BG_DARK, fg=DIM,
                 font=FONT_SMALL).pack(side=tk.RIGHT, padx=16)

        # ── Main split ─────────────────────────────────────────
        main = tk.Frame(self.parent, bg=BG_DARKEST)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Left: player list
        left = tk.Frame(main, bg=BG_DARKEST, width=220)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))
        left.pack_propagate(False)
        self._build_player_list(left)

        # Right: detail + alerts
        right = tk.Frame(main, bg=BG_DARKEST)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_right_panel(right)

    def _build_player_list(self, parent):
        # Label + add button
        row = tk.Frame(parent, bg=BG_DARKEST)
        row.pack(fill=tk.X, pady=(8, 4))
        tk.Label(row, text="// ALUNOS", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Button(row, text="+ Novo", bg=BG_MEDIUM, fg=ACCENT,
                  font=FONT_SMALL, relief="flat", cursor="hand2",
                  command=self._new_player).pack(side=tk.RIGHT)

        # Scrollable list
        canvas = tk.Canvas(parent, bg=BG_DARKEST, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        self._pl_frame = tk.Frame(canvas, bg=BG_DARKEST)
        canvas.create_window((0, 0), window=self._pl_frame, anchor="nw")
        self._pl_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def _build_right_panel(self, parent):
        # Upcoming sessions
        tk.Label(parent, text="// PRÓXIMAS SESSÕES", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(anchor="w", pady=(8, 4))
        self._upcoming_frame = tk.Frame(parent, bg=BG_DARKEST)
        self._upcoming_frame.pack(fill=tk.X)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        # Alerts
        tk.Label(parent, text="// ALERTAS DE PROGRESSO", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        self._alerts_frame = tk.Frame(parent, bg=BG_DARKEST)
        self._alerts_frame.pack(fill=tk.X)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=8)

        # Selected player detail
        tk.Label(parent, text="// JOGADOR SELECIONADO", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        self._detail_frame = tk.Frame(parent, bg=BG_DARKEST)
        self._detail_frame.pack(fill=tk.BOTH, expand=True)
        self._render_detail(None)

    # ═══════════════════════════════════════════════════════════════
    #  PLAYER LIST
    # ═══════════════════════════════════════════════════════════════

    def _refresh_players(self):
        for w in self._pl_frame.winfo_children():
            w.destroy()
        self._players = load_players()

        for p in self._players:
            self._render_player_card(p)

        self._refresh_upcoming()
        if self._selected:
            updated = next((x for x in self._players if x.id == self._selected.id), None)
            self._render_detail(updated)

    def _bind_click_recursive(self, widget, callback):
        """Vincula <Button-1> ao widget e a todos os seus filhos."""
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback)

    def _render_player_card(self, player: Player):
        is_sel = self._selected and self._selected.id == player.id
        bg = BG_MEDIUM if is_sel else BG_DARK

        card = tk.Frame(self._pl_frame, bg=bg, bd=0,
                        highlightthickness=1,
                        highlightbackground=ACCENT if is_sel else BORDER,
                        cursor="hand2")
        card.pack(fill=tk.X, pady=2, padx=2)

        top = tk.Frame(card, bg=bg)
        top.pack(fill=tk.X, padx=8, pady=(6, 2))

        role_color = ROLE_COLOR.get(player.role, DIM)
        tk.Label(top, text=player.role, bg=bg, fg=role_color,
                 font=("Courier New", 9, "bold"), width=4).pack(side=tk.LEFT)
        tk.Label(top, text=player.display, bg=bg, fg=TEXT,
                 font=FONT_MONO).pack(side=tk.LEFT, padx=4)

        bot = tk.Frame(card, bg=bg)
        bot.pack(fill=tk.X, padx=8, pady=(0, 6))
        sessions = list_sessions(player.id)
        last_str = sessions[0].date[:10] if sessions else "sem sessões"
        rank_str = player.rank or "—"
        tk.Label(bot, text=f"{rank_str} · {len(sessions)} sessão(ões)",
                 bg=bg, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(bot, text=last_str, bg=bg, fg=DIM, font=FONT_SMALL).pack(side=tk.RIGHT)

        # Vincula clique em todo o card (frames + labels filhos)
        self._bind_click_recursive(card, lambda e, p=player: self._select_player(p))

    # ═══════════════════════════════════════════════════════════════
    #  DETAIL PANEL
    # ═══════════════════════════════════════════════════════════════

    def _select_player(self, player: Player):
        self._selected = player
        self._refresh_players()
        self._render_detail(player)
        # Carrega alertas em background
        if self.match_api and player.riot_puuid:
            threading.Thread(target=self._load_alerts, args=(player,), daemon=True).start()

    def _render_detail(self, player: Player | None):
        for w in self._detail_frame.winfo_children():
            w.destroy()

        if not player:
            tk.Label(self._detail_frame,
                     text="Selecione um aluno para ver detalhes",
                     bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(pady=24)
            return

        # Info
        info = tk.Frame(self._detail_frame, bg=BG_DARK, bd=0,
                        highlightthickness=1, highlightbackground=BORDER)
        info.pack(fill=tk.X, pady=(0, 8))

        top = tk.Frame(info, bg=BG_DARK)
        top.pack(fill=tk.X, padx=12, pady=8)
        role_color = ROLE_COLOR.get(player.role, DIM)
        tk.Label(top, text=player.display, bg=BG_DARK, fg=TEXT,
                 font=FONT_HEAD).pack(side=tk.LEFT)
        tk.Label(top, text=player.role, bg=BG_DARK, fg=role_color,
                 font=("Courier New", 10, "bold")).pack(side=tk.LEFT, padx=8)
        tk.Label(top, text=player.riot_id, bg=BG_DARK, fg=DIM,
                 font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(top, text=player.rank or "Unranked", bg=BG_DARK, fg=ACCENT,
                 font=FONT_SMALL).pack(side=tk.RIGHT, padx=4)

        if player.notes:
            tk.Label(info, text=player.notes, bg=BG_DARK, fg=DIM,
                     font=FONT_SMALL, wraplength=400, justify="left").pack(
                anchor="w", padx=12, pady=(0, 8))

        # Goals summary
        active_goals = [g for g in player.goals if g.get("status") == "active"]
        achieved     = [g for g in player.goals if g.get("status") == "achieved"]
        if player.goals:
            tk.Label(info, text=f"Metas: {len(active_goals)} ativas · {len(achieved)} concluídas",
                     bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(anchor="w", padx=12, pady=(0, 8))

        # Action buttons
        btn_f = tk.Frame(self._detail_frame, bg=BG_DARKEST)
        btn_f.pack(fill=tk.X)

        def _btn(text, fg, cmd):
            tk.Button(btn_f, text=text, bg=BG_MEDIUM, fg=fg,
                      font=FONT_SMALL, relief="flat", cursor="hand2", pady=5,
                      command=cmd).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

        _btn("▶ Nova sessão",   ACCENT,   lambda: self._new_session(player))
        _btn("◎ Metas",        CYAN,     lambda: self._open_goals(player))
        _btn("▤ Relatório",    WARNING,  lambda: self._open_report(player))
        _btn("✎ Editar",       DIM,      lambda: self._edit_player(player))
        _btn("✕ Remover",      DANGER,   lambda: self._remove_player(player))

        # Recent sessions list
        sessions = list_sessions(player.id)
        if sessions:
            tk.Label(self._detail_frame, text="// SESSÕES RECENTES",
                     bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(anchor="w", pady=(12, 4))
            for s in sessions[:4]:
                self._render_session_row(s)

    def _render_session_row(self, session):
        row = tk.Frame(self._detail_frame, bg=BG_DARK, bd=0,
                       highlightthickness=1, highlightbackground=BORDER)
        row.pack(fill=tk.X, pady=1)
        left = tk.Frame(row, bg=BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        top = tk.Frame(left, bg=BG_DARK)
        top.pack(fill=tk.X)
        tk.Label(top, text=session.date[:10], bg=BG_DARK, fg=ACCENT,
                 font=("Courier New", 9, "bold")).pack(side=tk.LEFT)
        tk.Label(top, text=f"{session.duration_minutes}min",
                 bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT, padx=8)
        mood = "★" * session.checkin_mood + "☆" * (5 - session.checkin_mood)
        tk.Label(top, text=mood, bg=BG_DARK, fg="#aa7700",
                 font=FONT_SMALL).pack(side=tk.RIGHT)

        if session.key_mistakes:
            tk.Label(left, text=" · ".join(session.key_mistakes[:2]),
                     bg=BG_DARK, fg=DIM, font=FONT_SMALL,
                     wraplength=380, justify="left").pack(anchor="w")
        if session.homework:
            hw_text = "HW: " + " · ".join(session.homework[:2])
            tk.Label(left, text=hw_text, bg=BG_DARK, fg=SUCCESS,
                     font=FONT_SMALL, wraplength=380, justify="left").pack(anchor="w")

    # ═══════════════════════════════════════════════════════════════
    #  UPCOMING & ALERTS
    # ═══════════════════════════════════════════════════════════════

    def _refresh_upcoming(self):
        for w in self._upcoming_frame.winfo_children():
            w.destroy()
        upcoming = get_upcoming_sessions(days_ahead=7)
        if not upcoming:
            tk.Label(self._upcoming_frame, text="Nenhuma sessão nos próximos 7 dias",
                     bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(anchor="w")
        else:
            for item in upcoming[:4]:
                p, s = item["player"], item["session"]
                row = tk.Frame(self._upcoming_frame, bg=BG_DARK, bd=0,
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill=tk.X, pady=1)
                role_color = ROLE_COLOR.get(p.role, DIM)
                tk.Label(row, text=p.display, bg=BG_DARK, fg=TEXT,
                         font=FONT_SMALL, width=14).pack(side=tk.LEFT, padx=8, pady=5)
                tk.Label(row, text=item["date"], bg=BG_DARK, fg=ACCENT,
                         font=FONT_SMALL).pack(side=tk.LEFT)
                tk.Label(row, text=p.role, bg=BG_DARK, fg=role_color,
                         font=FONT_SMALL).pack(side=tk.RIGHT, padx=8)

    def _load_alerts(self, player: Player):
        """Carrega alertas semanais em background."""
        try:
            from ..services.progress_tracker import generate_weekly_alerts
            alerts = generate_weekly_alerts(self.match_api, player)
            self.root.after(0, lambda: self._show_alerts(alerts))
        except Exception:
            pass

    def _show_alerts(self, alerts: list[str]):
        for w in self._alerts_frame.winfo_children():
            w.destroy()
        if not alerts:
            tk.Label(self._alerts_frame, text="Sem alertas no momento",
                     bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(anchor="w")
        else:
            for msg in alerts[:5]:
                color = DANGER if "caiu" in msg or "❌" in msg else (
                    WARNING if "⏰" in msg else SUCCESS)
                tk.Label(self._alerts_frame, text=msg, bg=BG_DARKEST, fg=color,
                         font=FONT_SMALL, anchor="w", wraplength=480).pack(
                    fill=tk.X, pady=1)

    # ═══════════════════════════════════════════════════════════════
    #  ACTIONS
    # ═══════════════════════════════════════════════════════════════

    def _new_player(self):
        NewPlayerDialog(self.root, self.match_api, on_saved=self._refresh_players)

    def _new_session(self, player: Player):
        SessionView(self.root, player, match_api=self.match_api,
                    on_saved=self._refresh_players)

    def _open_goals(self, player: Player):
        GoalsView(self.root, player, on_changed=self._refresh_players)

    def _open_report(self, player: Player):
        ReportView(self.root, player, match_api=self.match_api)

    def _edit_player(self, player: Player):
        EditPlayerDialog(self.root, player, on_saved=self._refresh_players)

    def _remove_player(self, player: Player):
        if messagebox.askyesno("Remover", f"Remover {player.display}?", parent=self.root):
            delete_player(player.id)
            self._selected = None
            self._refresh_players()


# ═══════════════════════════════════════════════════════════════════
#  DIALOGS
# ═══════════════════════════════════════════════════════════════════

class NewPlayerDialog:
    """Diálogo de cadastro de novo aluno."""

    def __init__(self, root, match_api=None, on_saved=None):
        self.root      = root
        self.match_api = match_api
        self.on_saved  = on_saved

        self.win = tk.Toplevel(root)
        self.win.title("Novo Aluno")
        self.win.geometry("400x460")
        self.win.configure(bg=BG_DARKEST)
        self.win.resizable(False, False)
        self._build()

    def _build(self):
        tk.Label(self.win, text="◈ CADASTRAR ALUNO",
                 bg=BG_DARKEST, fg=ACCENT, font=FONT_HEAD).pack(padx=20, pady=(20, 16))

        def field(label, var_type=tk.StringVar, default=""):
            f = tk.Frame(self.win, bg=BG_DARKEST)
            f.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(f, text=label, bg=BG_DARKEST, fg=DIM, font=FONT_SMALL, width=14, anchor="w").pack(side=tk.LEFT)
            var = var_type()
            e = tk.Entry(f, textvariable=var, bg=BG_MEDIUM, fg=TEXT, font=FONT_MONO,
                         relief="flat", bd=0, insertbackground=ACCENT,
                         highlightthickness=1, highlightbackground=BORDER)
            e.insert(0, default)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
            return var

        self._name_var     = field("Nome de exibição")
        self._game_var     = field("Riot GameName")
        self._tag_var      = field("Tag", default="BR1")
        self._rank_var     = field("Rank", default="")

        # Role
        role_f = tk.Frame(self.win, bg=BG_DARKEST)
        role_f.pack(fill=tk.X, padx=20, pady=3)
        tk.Label(role_f, text="Role", bg=BG_DARKEST, fg=DIM, font=FONT_SMALL, width=14, anchor="w").pack(side=tk.LEFT)
        self._role_var = tk.StringVar(value="MID")
        for r in ROLES:
            tk.Radiobutton(role_f, text=r, variable=self._role_var, value=r,
                           bg=BG_DARKEST, fg=ROLE_COLOR.get(r, DIM),
                           selectcolor=BG_MEDIUM, font=FONT_SMALL,
                           activebackground=BG_DARKEST).pack(side=tk.LEFT, padx=4)

        # Notes
        tk.Label(self.win, text="Notas (opcional)", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(anchor="w", padx=20, pady=(8, 2))
        self._notes_text = tk.Text(self.win, height=3, bg=BG_MEDIUM, fg=TEXT,
                                   font=FONT_MONO, relief="flat", bd=0,
                                   insertbackground=ACCENT,
                                   highlightthickness=1, highlightbackground=BORDER)
        self._notes_text.pack(fill=tk.X, padx=20, pady=(0, 8))

        self._status = tk.Label(self.win, text="", bg=BG_DARKEST, fg=DIM, font=FONT_SMALL)
        self._status.pack()

        tk.Button(self.win, text="✓  CADASTRAR",
                  bg=ACCENT, fg=BG_DARKEST, font=FONT_HEAD,
                  relief="flat", cursor="hand2", pady=8,
                  command=self._save).pack(fill=tk.X, padx=20, pady=12)

    def _save(self):
        game_name = self._game_var.get().strip()
        tag_line  = self._tag_var.get().strip()
        name      = self._name_var.get().strip() or game_name

        if not game_name:
            messagebox.showerror("Erro", "GameName é obrigatório.", parent=self.win)
            return

        player = Player(
            summoner_name = name,
            game_name     = game_name,
            tag_line      = tag_line or "BR1",
            role          = self._role_var.get(),
            rank          = self._rank_var.get().strip(),
            notes         = self._notes_text.get("1.0", tk.END).strip(),
        )

        if self.match_api:
            self._status.config(text="Buscando PUUID…", fg=WARNING)
            def _fetch():
                try:
                    puuid = self.match_api.get_puuid(game_name, tag_line)
                    if puuid:
                        player.riot_puuid = puuid
                        # Baseline metrics
                        from ..services.diagnostic import generate_diagnostic
                        diag = generate_diagnostic(self.match_api, game_name, tag_line, player.role, count=20)
                        player.baseline_metrics = diag.get("metrics", {})
                        self.root.after(0, lambda: self._status.config(
                            text=f"PUUID obtido · {diag['games_analyzed']} partidas analisadas", fg=SUCCESS))
                    else:
                        self.root.after(0, lambda: self._status.config(
                            text="PUUID não encontrado — cadastrando sem dados Riot", fg=WARNING))
                except Exception as e:
                    self.root.after(0, lambda: self._status.config(text=str(e), fg=DANGER))
                finally:
                    from ..services.session_manager import save_player
                    save_player(player)
                    if self.on_saved:
                        self.root.after(0, self.on_saved)
                    self.root.after(100, self.win.destroy)
            threading.Thread(target=_fetch, daemon=True).start()
        else:
            from ..services.session_manager import save_player
            save_player(player)
            if self.on_saved:
                self.on_saved()
            self.win.destroy()


class EditPlayerDialog:
    """Diálogo de edição de aluno existente."""

    def __init__(self, root, player: Player, on_saved=None):
        self.root     = root
        self.player   = player
        self.on_saved = on_saved

        self.win = tk.Toplevel(root)
        self.win.title(f"Editar — {player.display}")
        self.win.geometry("380x320")
        self.win.configure(bg=BG_DARKEST)
        self.win.resizable(False, False)
        self._build()

    def _build(self):
        tk.Label(self.win, text="◈ EDITAR ALUNO",
                 bg=BG_DARKEST, fg=ACCENT, font=FONT_HEAD).pack(padx=20, pady=(20, 12))

        def field(label, default):
            f = tk.Frame(self.win, bg=BG_DARKEST)
            f.pack(fill=tk.X, padx=20, pady=3)
            tk.Label(f, text=label, bg=BG_DARKEST, fg=DIM, font=FONT_SMALL, width=14, anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar(value=default)
            tk.Entry(f, textvariable=var, bg=BG_MEDIUM, fg=TEXT, font=FONT_MONO,
                     relief="flat", bd=0, insertbackground=ACCENT,
                     highlightthickness=1, highlightbackground=BORDER).pack(
                side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
            return var

        self._name_var = field("Nome de exibição", self.player.summoner_name)
        self._rank_var = field("Rank",             self.player.rank)

        role_f = tk.Frame(self.win, bg=BG_DARKEST)
        role_f.pack(fill=tk.X, padx=20, pady=3)
        tk.Label(role_f, text="Role", bg=BG_DARKEST, fg=DIM, font=FONT_SMALL, width=14, anchor="w").pack(side=tk.LEFT)
        self._role_var = tk.StringVar(value=self.player.role)
        for r in ROLES:
            tk.Radiobutton(role_f, text=r, variable=self._role_var, value=r,
                           bg=BG_DARKEST, fg=ROLE_COLOR.get(r, DIM),
                           selectcolor=BG_MEDIUM, font=FONT_SMALL,
                           activebackground=BG_DARKEST).pack(side=tk.LEFT, padx=4)

        tk.Label(self.win, text="Notas", bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(anchor="w", padx=20, pady=(8,2))
        self._notes_text = tk.Text(self.win, height=3, bg=BG_MEDIUM, fg=TEXT,
                                   font=FONT_MONO, relief="flat", bd=0,
                                   insertbackground=ACCENT,
                                   highlightthickness=1, highlightbackground=BORDER)
        self._notes_text.insert("1.0", self.player.notes)
        self._notes_text.pack(fill=tk.X, padx=20, pady=(0, 8))

        tk.Button(self.win, text="✓  SALVAR",
                  bg=ACCENT, fg=BG_DARKEST, font=FONT_HEAD,
                  relief="flat", cursor="hand2", pady=8,
                  command=self._save).pack(fill=tk.X, padx=20, pady=4)

    def _save(self):
        from ..services.session_manager import save_player
        self.player.summoner_name = self._name_var.get().strip() or self.player.game_name
        self.player.rank          = self._rank_var.get().strip()
        self.player.role          = self._role_var.get()
        self.player.notes         = self._notes_text.get("1.0", tk.END).strip()
        save_player(self.player)
        if self.on_saved:
            self.on_saved()
        self.win.destroy()
