# -*- coding: utf-8 -*-
"""Tela de sessão ativa — 4 blocos estruturados."""

import tkinter as tk
from tkinter import messagebox
import threading
from datetime import datetime, date, timedelta

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


def _section(parent, title: str, color: str = ACCENT) -> tk.Frame:
    """Cria um bloco de seção com título."""
    f = tk.Frame(parent, bg=BG_DARK, bd=0, highlightthickness=1,
                 highlightbackground=BORDER)
    f.pack(fill=tk.X, padx=4, pady=4)
    tk.Label(f, text=title, bg=BG_DARK, fg=color,
             font=FONT_HEAD).pack(anchor="w", padx=10, pady=(8, 2))
    tk.Frame(f, bg=BORDER, height=1).pack(fill=tk.X, padx=10, pady=(0, 6))
    return f


def _label(parent, text, fg=DIM):
    tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg,
             font=FONT_SMALL).pack(anchor="w", padx=12)


def _textbox(parent, height=3) -> tk.Text:
    t = tk.Text(parent, height=height, bg=BG_MEDIUM, fg=TEXT,
                font=FONT_MONO, relief="flat", bd=0,
                insertbackground=ACCENT, wrap=tk.WORD,
                highlightthickness=1, highlightbackground=BORDER)
    t.pack(fill=tk.X, padx=12, pady=(2, 8))
    return t


def _entry(parent, placeholder="") -> tk.Entry:
    e = tk.Entry(parent, bg=BG_MEDIUM, fg=TEXT, font=FONT_MONO,
                 relief="flat", bd=0, insertbackground=ACCENT,
                 highlightthickness=1, highlightbackground=BORDER)
    e.pack(fill=tk.X, padx=12, pady=(2, 8), ipady=4)
    if placeholder:
        e.insert(0, placeholder)
        e.config(fg=DIM)
        def _on_focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, tk.END); e.config(fg=TEXT)
        def _on_focus_out(ev):
            if not e.get():
                e.insert(0, placeholder); e.config(fg=DIM)
        e.bind("<FocusIn>",  _on_focus_in)
        e.bind("<FocusOut>", _on_focus_out)
    return e


class SessionView:
    """Janela de registro de sessão de coaching."""

    def __init__(self, root: tk.Tk, player, match_api=None, on_saved=None):
        self.root      = root
        self.player    = player
        self.match_api = match_api
        self.on_saved  = on_saved  # callback após salvar

        self.win = tk.Toplevel(root)
        self.win.title(f"Sessão — {player.display}")
        self.win.geometry("640x800")
        self.win.configure(bg=BG_DARKEST)
        self.win.resizable(True, True)

        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self.win, bg=BG_DARK, height=48)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text=f"◈ SESSÃO — {self.player.display.upper()}",
                 bg=BG_DARK, fg=ACCENT, font=("Courier New", 13, "bold")).pack(side=tk.LEFT, padx=16, pady=8)
        tk.Label(hdr, text=datetime.now().strftime("%d/%m/%Y"),
                 bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.RIGHT, padx=16)

        # Scrollable canvas
        canvas = tk.Canvas(self.win, bg=BG_DARKEST, highlightthickness=0)
        sb     = tk.Scrollbar(self.win, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        self._frame = tk.Frame(canvas, bg=BG_DARKEST)
        canvas.create_window((0, 0), window=self._frame, anchor="nw")
        self._frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self._build_checkin()
        self._build_replay()
        self._build_drill()
        self._build_debrief()
        self._build_save()

    # ── Bloco 1: Check-in ─────────────────────────────────────────
    def _build_checkin(self):
        sec = _section(self._frame, "// 1 · CHECK-IN", CYAN)
        _label(sec, "Como está o mental? Como foi a semana?")
        self._checkin_text = _textbox(sec, height=3)

        mood_f = tk.Frame(sec, bg=BG_DARK)
        mood_f.pack(fill=tk.X, padx=12, pady=(0, 8))
        tk.Label(mood_f, text="Humor:", bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        self._mood_var = tk.IntVar(value=3)
        for i in range(1, 6):
            tk.Radiobutton(mood_f, text=str(i), variable=self._mood_var, value=i,
                           bg=BG_DARK, fg=ACCENT, selectcolor=BG_MEDIUM,
                           font=FONT_SMALL, activebackground=BG_DARK).pack(side=tk.LEFT, padx=4)

    # ── Bloco 2: Replay ───────────────────────────────────────────
    def _build_replay(self):
        sec = _section(self._frame, "// 2 · ANÁLISE DE REPLAY", WARNING)
        _label(sec, "Game ID da partida (opcional)")
        self._game_id_entry = _entry(sec, "EX: BR1_3216565241")

        if self.match_api:
            btn = tk.Button(sec, text="Carregar partida", bg=BG_MEDIUM, fg=WARNING,
                            font=FONT_SMALL, relief="flat", cursor="hand2",
                            command=self._load_replay)
            btn.pack(anchor="w", padx=12, pady=(0, 4))
            self._replay_info = tk.Label(sec, text="", bg=BG_DARK, fg=DIM, font=FONT_SMALL)
            self._replay_info.pack(anchor="w", padx=12)

        _label(sec, "Notas do replay / VOD review")
        self._replay_text = _textbox(sec, height=3)

        _label(sec, "Erros identificados (máx 3)")
        self._mistake_entries = []
        for i in range(3):
            e = _entry(sec, f"Erro {i+1}")
            self._mistake_entries.append(e)

    def _load_replay(self):
        gid = self._game_id_entry.get().strip()
        if not gid or gid == "EX: BR1_3216565241":
            return
        self._replay_info.config(text="Carregando…", fg=WARNING)
        def _fetch():
            md = self.match_api.get_match_data(gid)
            def _done():
                if not md:
                    self._replay_info.config(text="Partida não encontrada.", fg=DANGER)
                    return
                info   = md.get("info", {})
                dur    = info.get("gameDuration", 0) // 60
                mode   = info.get("gameMode", "?")
                p      = self.match_api.get_participant_by_puuid(md, self.player.riot_puuid) or {}
                win    = "✓ Vitória" if p.get("win") else "✗ Derrota"
                champ  = p.get("championName", "?")
                kda    = f'{p.get("kills",0)}/{p.get("deaths",0)}/{p.get("assists",0)}'
                self._replay_info.config(
                    text=f"{win} · {champ} · {kda} · {dur}min · {mode}", fg=SUCCESS
                )
            self.win.after(0, _done)
        threading.Thread(target=_fetch, daemon=True).start()

    # ── Bloco 3: Drill ────────────────────────────────────────────
    def _build_drill(self):
        sec = _section(self._frame, "// 3 · PRÁTICA GUIADA", SUCCESS)
        _label(sec, "Exercício realizado na sessão")
        self._drill_text = _textbox(sec, height=2)

    # ── Bloco 4: Debrief + Homework ───────────────────────────────
    def _build_debrief(self):
        sec = _section(self._frame, "// 4 · DEBRIEF + HOMEWORK", ACCENT)
        _label(sec, "Tarefas até a próxima sessão (máx 5)")
        self._hw_entries = []
        for i in range(5):
            e = _entry(sec, f"Tarefa {i+1}")
            self._hw_entries.append(e)

        # Próxima sessão
        date_f = tk.Frame(sec, bg=BG_DARK)
        date_f.pack(fill=tk.X, padx=12, pady=(4, 4))
        tk.Label(date_f, text="Próxima sessão:", bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        self._next_date = _entry(date_f, (date.today() + timedelta(days=7)).isoformat())
        self._next_date.pack_forget()  # já foi empacotado, re-empacota inline
        self._next_date = tk.Entry(date_f, bg=BG_MEDIUM, fg=TEXT, font=FONT_MONO,
                                   relief="flat", bd=0, insertbackground=ACCENT,
                                   highlightthickness=1, highlightbackground=BORDER, width=14)
        self._next_date.insert(0, (date.today() + timedelta(days=7)).isoformat())
        self._next_date.pack(side=tk.LEFT, padx=8, ipady=4)

        # Rating da sessão
        rating_f = tk.Frame(sec, bg=BG_DARK)
        rating_f.pack(fill=tk.X, padx=12, pady=(4, 8))
        tk.Label(rating_f, text="Rating (coach):", bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        self._rating_var = tk.IntVar(value=3)
        for i in range(1, 6):
            tk.Radiobutton(rating_f, text="★" * i, variable=self._rating_var, value=i,
                           bg=BG_DARK, fg=WARNING, selectcolor=BG_MEDIUM,
                           font=FONT_SMALL, activebackground=BG_DARK).pack(side=tk.LEFT, padx=2)

    # ── Salvar ────────────────────────────────────────────────────
    def _build_save(self):
        f = tk.Frame(self._frame, bg=BG_DARKEST)
        f.pack(fill=tk.X, padx=8, pady=12)
        tk.Button(f, text="✓  SALVAR SESSÃO",
                  bg=ACCENT, fg=BG_DARKEST, font=FONT_HEAD,
                  relief="flat", cursor="hand2", pady=8,
                  command=self._save).pack(fill=tk.X)

    def _save(self):
        from ..models.session import CoachingSession
        from ..services.session_manager import save_session

        checkin  = self._checkin_text.get("1.0", tk.END).strip()
        replay_n = self._replay_text.get("1.0", tk.END).strip()
        drill    = self._drill_text.get("1.0", tk.END).strip()

        def _clean(e, placeholder):
            v = e.get().strip()
            return v if v != placeholder else ""

        mistakes = [_clean(e, f"Erro {i+1}") for i, e in enumerate(self._mistake_entries)
                    if _clean(e, f"Erro {i+1}")]
        homework = [_clean(e, f"Tarefa {i+1}") for i, e in enumerate(self._hw_entries)
                    if _clean(e, f"Tarefa {i+1}")]

        gid_raw  = self._game_id_entry.get().strip()
        game_id  = gid_raw if gid_raw != "EX: BR1_3216565241" else ""

        sess = CoachingSession(
            player_id        = self.player.id,
            checkin_notes    = checkin,
            checkin_mood     = self._mood_var.get(),
            replay_game_id   = game_id,
            replay_notes     = replay_n,
            key_mistakes     = mistakes,
            drill_performed  = drill,
            homework         = homework,
            coach_rating     = self._rating_var.get(),
            next_session_date= self._next_date.get().strip(),
        )
        save_session(sess)
        messagebox.showinfo("Salvo", "Sessão registrada com sucesso!", parent=self.win)
        if self.on_saved:
            self.on_saved()
        self.win.destroy()
