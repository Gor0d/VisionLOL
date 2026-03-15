# -*- coding: utf-8 -*-
"""Tela de gerenciamento de metas SMART."""

import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta

from ..models.goal    import SmartGoal, METRIC_LABELS, STATUS_ACTIVE
from ..services.session_manager import save_player, load_player

BG_DARKEST = "#000000"
BG_DARK    = "#0A0A08"
BG_MEDIUM  = "#111110"
BG_LIGHT   = "#181816"
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

STATUS_COLOR = {
    "active":   ACCENT,
    "achieved": SUCCESS,
    "failed":   DANGER,
    "paused":   DIM,
}


class GoalsView:
    """Janela de metas SMART do jogador."""

    def __init__(self, root, player, current_metrics: dict | None = None, on_changed=None):
        self.root            = root
        self.player          = player
        self.current_metrics = current_metrics or {}
        self.on_changed      = on_changed

        self.win = tk.Toplevel(root)
        self.win.title(f"Metas — {player.display}")
        self.win.geometry("580x620")
        self.win.configure(bg=BG_DARKEST)
        self.win.resizable(True, True)

        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self.win, bg=BG_DARK, height=44)
        hdr.pack(fill=tk.X); hdr.pack_propagate(False)
        tk.Label(hdr, text=f"◈ METAS — {self.player.display.upper()}",
                 bg=BG_DARK, fg=CYAN, font=FONT_HEAD).pack(side=tk.LEFT, padx=16, pady=8)

        # Goals list
        tk.Label(self.win, text="// METAS ATIVAS", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(anchor="w", padx=12, pady=(10, 4))

        self._list_frame = tk.Frame(self.win, bg=BG_DARKEST)
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=8)
        self._refresh_list()

        # Separator
        tk.Frame(self.win, bg=BORDER, height=1).pack(fill=tk.X, padx=8, pady=8)

        # Add goal form
        tk.Label(self.win, text="// NOVA META", bg=BG_DARKEST, fg=DIM,
                 font=FONT_SMALL).pack(anchor="w", padx=12, pady=(0, 4))

        form = tk.Frame(self.win, bg=BG_DARK, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        form.pack(fill=tk.X, padx=8, pady=(0, 8))

        # Metric selector
        row = tk.Frame(form, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=6)
        tk.Label(row, text="Métrica:", bg=BG_DARK, fg=DIM, font=FONT_SMALL, width=12, anchor="w").pack(side=tk.LEFT)
        self._metric_var = tk.StringVar(value="cs_per_min")
        opts = list(METRIC_LABELS.keys())
        tk.OptionMenu(row, self._metric_var, *opts).configure(
            bg=BG_MEDIUM, fg=TEXT, font=FONT_SMALL,
            relief="flat", bd=0, highlightthickness=0, activebackground=BG_LIGHT
        )
        om = tk.OptionMenu(row, self._metric_var, *opts)
        om.config(bg=BG_MEDIUM, fg=TEXT, font=FONT_SMALL, relief="flat", bd=0,
                  activebackground=BG_LIGHT, highlightthickness=1, highlightbackground=BORDER)
        om.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Target + Deadline
        row2 = tk.Frame(form, bg=BG_DARK)
        row2.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(row2, text="Alvo:", bg=BG_DARK, fg=DIM, font=FONT_SMALL, width=12, anchor="w").pack(side=tk.LEFT)
        self._target_entry = tk.Entry(row2, bg=BG_MEDIUM, fg=TEXT, font=FONT_MONO,
                                      relief="flat", bd=0, insertbackground=ACCENT,
                                      highlightthickness=1, highlightbackground=BORDER, width=10)
        self._target_entry.pack(side=tk.LEFT, ipady=3, padx=(0, 16))

        tk.Label(row2, text="Prazo:", bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        self._deadline_entry = tk.Entry(row2, bg=BG_MEDIUM, fg=TEXT, font=FONT_MONO,
                                        relief="flat", bd=0, insertbackground=ACCENT,
                                        highlightthickness=1, highlightbackground=BORDER, width=12)
        self._deadline_entry.insert(0, (date.today() + timedelta(days=30)).isoformat())
        self._deadline_entry.pack(side=tk.LEFT, ipady=3)

        tk.Button(form, text="+ Adicionar meta",
                  bg=ACCENT, fg=BG_DARKEST, font=FONT_SMALL,
                  relief="flat", cursor="hand2",
                  command=self._add_goal).pack(fill=tk.X, padx=10, pady=8)

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        goals = [SmartGoal.from_dict(g) for g in self.player.goals]
        if not goals:
            tk.Label(self._list_frame, text="Nenhuma meta cadastrada.",
                     bg=BG_DARKEST, fg=DIM, font=FONT_SMALL).pack(pady=16)
            return

        for goal in goals:
            self._render_goal_row(goal)

    def _render_goal_row(self, goal: SmartGoal):
        curr = self.current_metrics.get(goal.metric, goal.current_value)
        prog = goal.check_progress(curr)

        row = tk.Frame(self._list_frame, bg=BG_DARK, bd=0,
                       highlightthickness=1, highlightbackground=BORDER)
        row.pack(fill=tk.X, pady=2)

        left = tk.Frame(row, bg=BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=6)

        # Title row
        title_f = tk.Frame(left, bg=BG_DARK)
        title_f.pack(fill=tk.X)
        color = STATUS_COLOR.get(goal.status, DIM)
        tk.Label(title_f, text=goal.metric_label, bg=BG_DARK, fg=color,
                 font=("Courier New", 10, "bold")).pack(side=tk.LEFT)
        days = goal.days_remaining()
        days_text = f"{days}d restantes" if days >= 0 else "EXPIRADA"
        days_color = DIM if days >= 7 else (WARNING if days >= 0 else DANGER)
        tk.Label(title_f, text=days_text, bg=BG_DARK, fg=days_color,
                 font=FONT_SMALL).pack(side=tk.RIGHT)

        # Progress
        info_f = tk.Frame(left, bg=BG_DARK)
        info_f.pack(fill=tk.X, pady=(4, 0))
        tk.Label(info_f, text=f"{goal.current_value:.2f} → {goal.target_value:.2f}",
                 bg=BG_DARK, fg=DIM, font=FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(info_f, text=f"atual: {curr:.2f}",
                 bg=BG_DARK, fg=TEXT, font=FONT_SMALL).pack(side=tk.LEFT, padx=8)

        # Progress bar
        bar_bg = tk.Frame(left, bg=BORDER, height=4)
        bar_bg.pack(fill=tk.X, pady=3)
        bar_bg.pack_propagate(False)
        pct = max(0, min(prog["pct"], 100))
        if pct > 0:
            bar_fill = tk.Frame(bar_bg, bg=SUCCESS if pct >= 100 else ACCENT, height=4)
            bar_fill.place(relwidth=pct / 100, relheight=1)

        # Delete button
        tk.Button(row, text="✕", bg=BG_DARK, fg=DANGER, font=FONT_SMALL,
                  relief="flat", cursor="hand2",
                  command=lambda gid=goal.id: self._delete_goal(gid)).pack(
            side=tk.RIGHT, padx=8, pady=6)

    def _add_goal(self):
        metric = self._metric_var.get()
        try:
            target = float(self._target_entry.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Alvo deve ser um número.", parent=self.win)
            return
        deadline = self._deadline_entry.get().strip()
        current  = self.current_metrics.get(metric, 0.0)

        goal = SmartGoal(
            player_id     = self.player.id,
            metric        = metric,
            current_value = current,
            target_value  = target,
            deadline      = deadline,
        )
        self.player.goals.append(goal.to_dict())
        save_player(self.player)
        self._target_entry.delete(0, tk.END)
        self._refresh_list()
        if self.on_changed:
            self.on_changed()

    def _delete_goal(self, goal_id: str):
        self.player.goals = [g for g in self.player.goals if g.get("id") != goal_id]
        save_player(self.player)
        self._refresh_list()
        if self.on_changed:
            self.on_changed()
