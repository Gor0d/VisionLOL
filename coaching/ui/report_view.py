# -*- coding: utf-8 -*-
"""Geração e abertura do relatório mensal HTML no browser."""

import tkinter as tk
from tkinter import messagebox
import webbrowser
import threading
from datetime import date

BG_DARKEST = "#000000"
BG_DARK    = "#0A0A08"
BG_MEDIUM  = "#111110"
BORDER     = "#2A2A28"
ACCENT     = "#FF9830"
SUCCESS    = "#50FF50"
DANGER     = "#FF4840"
CYAN       = "#20F0FF"
TEXT       = "#E0E0D8"
DIM        = "#8A8A82"
FONT_MONO  = ("Courier New", 10)
FONT_HEAD  = ("Courier New", 11, "bold")
FONT_SMALL = ("Courier New", 9)


class ReportView:
    """Diálogo para gerar e abrir relatório mensal."""

    def __init__(self, root, player, match_api=None):
        self.root      = root
        self.player    = player
        self.match_api = match_api

        self.win = tk.Toplevel(root)
        self.win.title(f"Relatório — {player.display}")
        self.win.geometry("380px" if False else "380x280")
        self.win.configure(bg=BG_DARKEST)
        self.win.resizable(False, False)

        self._build()

    def _build(self):
        tk.Label(self.win, text="◈ GERAR RELATÓRIO MENSAL",
                 bg=BG_DARKEST, fg=ACCENT, font=FONT_HEAD).pack(padx=20, pady=(20, 4))
        tk.Label(self.win, text=f"Jogador: {self.player.display} · {self.player.role}",
                 bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack()

        tk.Frame(self.win, bg=BORDER, height=1).pack(fill=tk.X, padx=20, pady=12)

        # Mês / Ano
        row = tk.Frame(self.win, bg=BG_DARKEST)
        row.pack(padx=20, pady=4)

        today = date.today()

        tk.Label(row, text="Mês:", bg=BG_DARKEST, fg=DIM, font=FONT_SMALL, width=6).pack(side=tk.LEFT)
        self._month_var = tk.IntVar(value=today.month)
        months = list(range(1, 13))
        om = tk.OptionMenu(row, self._month_var, *months)
        om.config(bg=BG_MEDIUM, fg=TEXT, font=FONT_SMALL, relief="flat", bd=0,
                  activebackground=BG_DARK, highlightthickness=1, highlightbackground=BORDER, width=4)
        om.pack(side=tk.LEFT)

        tk.Label(row, text="  Ano:", bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        self._year_var = tk.IntVar(value=today.year)
        years = [today.year - 1, today.year, today.year + 1]
        oy = tk.OptionMenu(row, self._year_var, *years)
        oy.config(bg=BG_MEDIUM, fg=TEXT, font=FONT_SMALL, relief="flat", bd=0,
                  activebackground=BG_DARK, highlightthickness=1, highlightbackground=BORDER, width=6)
        oy.pack(side=tk.LEFT)

        self._status_label = tk.Label(self.win, text="", bg=BG_DARKEST, fg=DIM,
                                      font=FONT_SMALL, wraplength=340)
        self._status_label.pack(pady=8)

        tk.Button(self.win, text="▶  GERAR E ABRIR NO BROWSER",
                  bg=ACCENT, fg=BG_DARKEST, font=FONT_HEAD,
                  relief="flat", cursor="hand2", pady=8,
                  command=self._generate).pack(fill=tk.X, padx=20, pady=8)

    def _generate(self):
        self._status_label.config(text="Gerando relatório…", fg=ACCENT)
        month = self._month_var.get()
        year  = self._year_var.get()

        def _run():
            from ..services.session_manager   import list_sessions
            from ..services.report_generator  import generate_monthly_report
            from ..services.progress_tracker  import fetch_recent_metrics

            sessions       = list_sessions(self.player.id)
            current_metrics = {}
            if self.match_api and self.player.riot_puuid:
                try:
                    current_metrics = fetch_recent_metrics(self.match_api, self.player, recent_count=10)
                except Exception:
                    pass

            try:
                path = generate_monthly_report(self.player, sessions, month, year, current_metrics)
                def _done():
                    self._status_label.config(text=f"Relatório salvo em:\n{path}", fg=SUCCESS)
                    webbrowser.open(f"file:///{path.replace(chr(92), '/')}")
            except Exception as e:
                def _done():
                    self._status_label.config(text=f"Erro: {e}", fg=DANGER)

            self.win.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()
