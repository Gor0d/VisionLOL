# -*- coding: utf-8 -*-
"""
ScoutingView — aba de scouting do First Stand 2025.

Permite analisar champion pools, pontos fracos e draft patterns
dos times adversários, com comparação direta vs LOUD.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
import json

from riot_api.first_stand_data import (
    FIRST_STAND_TEAMS, HOME_TEAM,
    ROUTING_MAP, ROUTING_BASE,
    load_roster, save_roster,
)

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
CYAN        = "#20F0FF"

TEXT_BRIGHT = "#E0E0D8"
TEXT_COLOR  = "#C8C8C0"
TEXT_DIM    = "#8A8A82"

ROLE_ORDER  = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"]
ROLE_SHORT  = {"TOP": "TOP", "JUNGLE": "JGL", "MIDDLE": "MID",
               "BOTTOM": "ADC", "SUPPORT": "SUP"}
ROLE_COLORS = {
    "TOP":     "#e5534b",
    "JUNGLE":  "#50FF50",
    "MIDDLE":  "#FF9830",
    "BOTTOM":  "#FFCC50",
    "SUPPORT": "#20F0FF",
}

MATCH_COUNT = 20   # partidas recentes por jogador


# ═══════════════════════════════════════════════════════════════════════
#  SCOUT VIEWER (widget embutido em Frame)
# ═══════════════════════════════════════════════════════════════════════

class ScoutingView(tk.Frame):
    """
    Frame completo de scouting — pode ser embutido em qualquer Notebook tab.

    Parâmetros
    ----------
    parent      : tk widget (tab frame)
    http_client : RiotHTTPClient — para chamadas de API
    match_api   : MatchAPI — reutiliza cache existente
    app_root    : tk.Tk — root do app (para Toplevel/after)
    """

    def __init__(self, parent, http_client, match_api, app_root):
        super().__init__(parent, bg=BG_DARKEST)
        self.http    = http_client
        self.api     = match_api
        self.root    = app_root

        self._teams  = load_roster()                  # {name: team_dict}
        self._order  = list(self._teams.keys())       # ordem de exibição
        self._sel    = HOME_TEAM                      # time selecionado
        self._closed = False

        # Cache de dados carregados: {team_name: {role: [champ_stats]}}
        self._pool_cache: dict[str, dict] = {}
        self._loading:    set[str]        = set()     # times em loading

        # Widgets
        self._team_btns:   dict[str, tk.Button] = {}
        self._status_lbls: dict[str, tk.Label]  = {}

        self._build()
        self.pack(fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────────────────────────────
    #  BUILD UI
    # ─────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ──────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG_DARK, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🔍  SCOUTING — First Stand 2025",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT, padx=14, pady=12)

        btn_frame = tk.Frame(hdr, bg=BG_DARK)
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=8)
        tk.Button(btn_frame, text="🔄 Atualizar Tudo",
                  font=("Segoe UI", 9), bg=BG_LIGHT, fg=ACCENT,
                  relief=tk.FLAT, cursor="hand2", padx=10, pady=4,
                  command=self._refresh_all).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_frame, text="+ Adicionar Time",
                  font=("Segoe UI", 9), bg=BG_LIGHT, fg=SUCCESS,
                  relief=tk.FLAT, cursor="hand2", padx=10, pady=4,
                  command=self._add_team).pack(side=tk.LEFT, padx=4)

        # ── Body ────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG_DARKEST)
        body.pack(fill=tk.BOTH, expand=True)

        # Painel esquerdo: lista de times
        left = tk.Frame(body, bg=BG_DARK, width=170)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text="TIMES", font=("Segoe UI", 8, "bold"),
                 bg=BG_DARK, fg=TEXT_DIM).pack(anchor="w", padx=10, pady=(8, 4))

        self._teams_frame = tk.Frame(left, bg=BG_DARK)
        self._teams_frame.pack(fill=tk.Y, expand=True)

        self._build_team_list()

        # Separador
        tk.Frame(body, bg=BORDER, width=1).pack(side=tk.LEFT, fill=tk.Y)

        # Painel direito: detalhe do time
        self._right = tk.Frame(body, bg=BG_DARKEST)
        self._right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_team_detail()

    def _build_team_list(self):
        """Reconstrói a lista de botões de times."""
        for w in self._teams_frame.winfo_children():
            w.destroy()
        self._team_btns.clear()
        self._status_lbls.clear()

        for name in self._order:
            team = self._teams[name]
            color  = team.get("color", ACCENT)
            is_home = team.get("is_home", False)

            row = tk.Frame(self._teams_frame, bg=BG_DARK)
            row.pack(fill=tk.X, pady=1)

            # Barra colorida à esquerda
            tk.Frame(row, bg=color, width=4).pack(side=tk.LEFT, fill=tk.Y)

            btn = tk.Button(row, text=team.get("display", name),
                            font=("Segoe UI", 9, "bold" if is_home else "normal"),
                            bg=BG_MEDIUM if name == self._sel else BG_DARK,
                            fg=color, relief=tk.FLAT, cursor="hand2",
                            anchor="w", padx=8, pady=6,
                            command=lambda n=name: self._select_team(n))
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._team_btns[name] = btn

            # Badge região
            region = team.get("region", "")
            tk.Label(row, text=region[:3], font=("Segoe UI", 7),
                     bg=BG_DARK, fg=TEXT_DIM, width=4).pack(side=tk.LEFT)

            # Status de loading
            status = tk.Label(row, text="○", font=("Segoe UI", 9),
                               bg=BG_DARK, fg=TEXT_DIM)
            status.pack(side=tk.RIGHT, padx=4)
            self._status_lbls[name] = status

    # ─────────────────────────────────────────────────────────────────
    #  DETALHE DO TIME
    # ─────────────────────────────────────────────────────────────────

    def _select_team(self, name: str):
        # Atualiza seleção visual
        for n, btn in self._team_btns.items():
            btn.config(bg=BG_MEDIUM if n == name else BG_DARK)
        self._sel = name
        self._build_team_detail()

        # Carrega dados se ainda não carregou
        if name not in self._pool_cache and name not in self._loading:
            self._fetch_team(name)

    def _build_team_detail(self):
        """Reconstrói o painel direito para o time selecionado."""
        for w in self._right.winfo_children():
            w.destroy()

        team = self._teams.get(self._sel)
        if not team:
            return

        color   = team.get("color", ACCENT)
        cn_only = team.get("cn_only", False)

        # ── Header do time ────────────────────────────────────────
        thdr = tk.Frame(self._right, bg=BG_DARK, height=56)
        thdr.pack(fill=tk.X)
        thdr.pack_propagate(False)

        name_lbl = tk.Label(thdr, text=team.get("display", self._sel),
                            font=("Segoe UI", 14, "bold"),
                            bg=BG_DARK, fg=color)
        name_lbl.pack(side=tk.LEFT, padx=14, pady=10)

        tk.Label(thdr, text=f"{team.get('region','')}  ·  {team.get('server','').upper()}",
                 font=("Segoe UI", 9), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.LEFT, pady=10)

        # Botões de ação no header
        act = tk.Frame(thdr, bg=BG_DARK)
        act.pack(side=tk.RIGHT, padx=10, pady=10)
        tk.Button(act, text="✏ Editar Roster",
                  font=("Segoe UI", 8), bg=BG_LIGHT, fg=ACCENT,
                  relief=tk.FLAT, cursor="hand2", padx=8, pady=3,
                  command=lambda: self._edit_roster(self._sel)
                  ).pack(side=tk.LEFT, padx=2)
        tk.Button(act, text="🔄 Atualizar",
                  font=("Segoe UI", 8), bg=BG_LIGHT, fg=TEXT_DIM,
                  relief=tk.FLAT, cursor="hand2", padx=8, pady=3,
                  command=lambda: self._fetch_team(self._sel, force=True)
                  ).pack(side=tk.LEFT, padx=2)

        # Aviso para times CN
        if cn_only:
            warn = tk.Frame(self._right, bg="#2a1500")
            warn.pack(fill=tk.X, padx=8, pady=4)
            tk.Label(warn,
                     text="⚠  Riot API não cobre o servidor CN (Tencent). "
                          "Cadastre stats manualmente via 'Editar Roster'.",
                     font=("Segoe UI", 9), bg="#2a1500", fg=WARNING,
                     wraplength=600, justify="left"
                     ).pack(anchor="w", padx=10, pady=6)

        # ── Tabs internas: Pool | Draft | Pontos Fracos ───────────
        nb = ttk.Notebook(self._right)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        tab_pool   = tk.Frame(nb, bg=BG_DARKEST)
        tab_draft  = tk.Frame(nb, bg=BG_DARKEST)
        tab_weak   = tk.Frame(nb, bg=BG_DARKEST)

        nb.add(tab_pool,  text="  🏆 Champion Pool  ")
        nb.add(tab_draft, text="  📋 Draft Patterns  ")
        nb.add(tab_weak,  text="  ⚠ Pontos Fracos  ")

        self._tab_pool  = tab_pool
        self._tab_draft = tab_draft
        self._tab_weak  = tab_weak

        pool = self._pool_cache.get(self._sel)
        if name := self._sel:
            if name in self._loading:
                self._render_loading(tab_pool)
                self._render_loading(tab_draft)
                self._render_loading(tab_weak)
            elif pool:
                self._render_pool(tab_pool, pool)
                self._render_draft(tab_draft, pool)
                self._render_weak(tab_weak, pool)
            else:
                self._render_empty(tab_pool)
                self._render_empty(tab_draft)
                self._render_empty(tab_weak)

    # ─────────────────────────────────────────────────────────────────
    #  RENDERIZAÇÃO: CHAMPION POOL
    # ─────────────────────────────────────────────────────────────────

    def _render_loading(self, parent: tk.Frame):
        tk.Label(parent, text="⏳  Buscando dados…",
                 font=("Segoe UI", 11), bg=BG_DARKEST, fg=ACCENT
                 ).pack(pady=30)

    def _render_empty(self, parent: tk.Frame):
        tk.Label(parent,
                 text="Clique em 🔄 Atualizar ou configure os accounts na opção ✏ Editar Roster",
                 font=("Segoe UI", 10), bg=BG_DARKEST, fg=TEXT_DIM,
                 wraplength=500, justify="center"
                 ).pack(pady=40)

    def _render_pool(self, parent: tk.Frame, pool: dict):
        """Exibe champion pool por role."""
        team   = self._teams.get(self._sel, {})
        is_home = team.get("is_home", False)

        # Canvas scrollável
        canvas = tk.Canvas(parent, bg=BG_DARKEST, highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        inner = tk.Frame(canvas, bg=BG_DARKEST)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        for role in ROLE_ORDER:
            champs = pool.get(role, [])
            color  = ROLE_COLORS.get(role, ACCENT)
            short  = ROLE_SHORT.get(role, role[:3])

            # Header da role
            rrow = tk.Frame(inner, bg=BG_DARK)
            rrow.pack(fill=tk.X, pady=(8, 2), padx=4)
            tk.Label(rrow, text=f" {short} ", font=("Segoe UI", 9, "bold"),
                     bg=color, fg=BG_DARKEST).pack(side=tk.LEFT, padx=(6, 8), pady=4)

            # Jogador desse role
            player = next(
                (p for p in team.get("players", []) if p.get("role") == role), {}
            )
            pname = player.get("game_name", "") or "—"
            tk.Label(rrow, text=pname, font=("Segoe UI", 9),
                     bg=BG_DARK, fg=TEXT_COLOR).pack(side=tk.LEFT)

            # Botão Radar vs LOUD (apenas para adversários)
            if not is_home:
                tk.Button(rrow, text=f"⚔ vs LOUD",
                          font=("Segoe UI", 8), bg=BG_LIGHT, fg=CYAN,
                          relief=tk.FLAT, cursor="hand2", padx=6, pady=2,
                          command=lambda r=role: self._open_radar(r)
                          ).pack(side=tk.RIGHT, padx=6)

            # Campeões
            if not champs:
                tk.Label(inner, text="  Sem dados", font=("Segoe UI", 8),
                         bg=BG_DARKEST, fg=TEXT_DIM).pack(anchor="w", padx=16, pady=2)
                continue

            for rank, cs in enumerate(champs[:5], 1):
                wr_fg   = SUCCESS if cs["wr"] >= 50 else (WARNING if cs["wr"] >= 40 else DANGER)
                champ_n = cs["champ"]
                games   = cs["games"]
                wr      = cs["wr"]
                kda     = cs.get("kda", 0.0)

                crow = tk.Frame(inner, bg=BG_MEDIUM if rank % 2 == 0 else BG_DARKEST)
                crow.pack(fill=tk.X, padx=16, pady=1)

                # Rank
                tk.Label(crow, text=f"#{rank}", font=("Segoe UI", 8),
                         bg=crow["bg"], fg=TEXT_DIM, width=3).pack(side=tk.LEFT, padx=(6, 2))

                # Nome do campeão
                tk.Label(crow, text=champ_n, font=("Segoe UI", 9, "bold"),
                         bg=crow["bg"], fg=TEXT_BRIGHT, width=16, anchor="w"
                         ).pack(side=tk.LEFT)

                # Jogos
                tk.Label(crow, text=f"{games}j", font=("Segoe UI", 8),
                         bg=crow["bg"], fg=TEXT_DIM, width=4).pack(side=tk.LEFT)

                # WR%
                tk.Label(crow, text=f"{wr}%", font=("Segoe UI", 9, "bold"),
                         bg=crow["bg"], fg=wr_fg, width=5).pack(side=tk.LEFT)

                # KDA
                kda_fg = SUCCESS if kda >= 3.0 else (WARNING if kda >= 2.0 else DANGER)
                tk.Label(crow, text=f"KDA {kda:.1f}", font=("Segoe UI", 8),
                         bg=crow["bg"], fg=kda_fg).pack(side=tk.LEFT, padx=6)

                # Barra de WR
                bar_bg = tk.Frame(crow, bg=BG_LIGHT, width=80, height=6)
                bar_bg.pack(side=tk.RIGHT, padx=(0, 10))
                bar_bg.pack_propagate(False)
                tk.Frame(bar_bg, bg=wr_fg, width=int(80 * wr / 100), height=6
                         ).place(x=0, y=0)

    # ─────────────────────────────────────────────────────────────────
    #  RENDERIZAÇÃO: DRAFT PATTERNS
    # ─────────────────────────────────────────────────────────────────

    def _render_draft(self, parent: tk.Frame, pool: dict):
        """Mostra as composições de time mais frequentes."""
        combos = self._compute_combos(pool)

        tk.Label(parent, text="Composições mais frequentes (por jogo analisado)",
                 font=("Segoe UI", 9, "bold"), bg=BG_DARKEST, fg=TEXT_DIM
                 ).pack(anchor="w", padx=12, pady=(10, 4))

        if not combos:
            tk.Label(parent, text="Dados insuficientes para análise de draft.",
                     font=("Segoe UI", 10), bg=BG_DARKEST, fg=TEXT_DIM
                     ).pack(pady=20)
            return

        for i, (picks, count, wr) in enumerate(combos[:8]):
            bg = BG_MEDIUM if i % 2 == 0 else BG_DARKEST
            row = tk.Frame(parent, bg=bg)
            row.pack(fill=tk.X, padx=8, pady=1)

            # Picks por role
            pick_str = "  ·  ".join(
                f"{ROLE_SHORT.get(r,'?')}: {picks.get(r, '?')}"
                for r in ROLE_ORDER if r in picks
            )
            tk.Label(row, text=pick_str, font=("Segoe UI", 8),
                     bg=bg, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=10, pady=5)

            wr_fg = SUCCESS if wr >= 50 else DANGER
            tk.Label(row, text=f"{count}x  ·  {wr}% WR",
                     font=("Segoe UI", 8, "bold"), bg=bg, fg=wr_fg
                     ).pack(side=tk.RIGHT, padx=10)

    def _compute_combos(self, pool: dict) -> list:
        """
        Agrega combinações de picks por role.
        Retorna lista de (picks_dict, count, wr%) ordenada por frequência.
        """
        combo_stats: dict[str, dict] = {}

        # Usa o top-1 de cada role como "combo principal"
        top_picks = {}
        for role in ROLE_ORDER:
            champs = pool.get(role, [])
            if champs:
                top_picks[role] = champs[0]["champ"]

        if len(top_picks) < 3:
            return []

        key = " | ".join(f"{r}:{c}" for r, c in sorted(top_picks.items()))
        total_games = sum(pool.get(r, [{}])[0].get("games", 0) if pool.get(r) else 0
                          for r in ROLE_ORDER)
        avg_wr = int(
            sum(pool.get(r, [{}])[0].get("wr", 50) if pool.get(r) else 50
                for r in ROLE_ORDER) / len(ROLE_ORDER)
        )
        return [(top_picks, total_games // max(len(ROLE_ORDER), 1), avg_wr)]

    # ─────────────────────────────────────────────────────────────────
    #  RENDERIZAÇÃO: PONTOS FRACOS
    # ─────────────────────────────────────────────────────────────────

    def _render_weak(self, parent: tk.Frame, pool: dict):
        """Destaca campeões com WR abaixo de 40%, gaps de CS, etc."""
        tk.Label(parent, text="Vulnerabilidades identificadas",
                 font=("Segoe UI", 9, "bold"), bg=BG_DARKEST, fg=TEXT_DIM
                 ).pack(anchor="w", padx=12, pady=(10, 4))

        found = False
        for role in ROLE_ORDER:
            champs = pool.get(role, [])
            for cs in champs:
                if cs["wr"] < 45 and cs["games"] >= 3:
                    found = True
                    color = ROLE_COLORS.get(role, ACCENT)
                    short = ROLE_SHORT.get(role, role[:3])
                    row   = tk.Frame(parent, bg=BG_MEDIUM)
                    row.pack(fill=tk.X, padx=8, pady=2)

                    tk.Label(row, text=f" {short} ", font=("Segoe UI", 8, "bold"),
                             bg=color, fg=BG_DARKEST).pack(side=tk.LEFT, padx=(8, 6), pady=4)
                    tk.Label(row, text=cs["champ"], font=("Segoe UI", 9, "bold"),
                             bg=BG_MEDIUM, fg=TEXT_BRIGHT, width=16, anchor="w"
                             ).pack(side=tk.LEFT)
                    tk.Label(row, text=f"{cs['games']}j",
                             font=("Segoe UI", 8), bg=BG_MEDIUM, fg=TEXT_DIM
                             ).pack(side=tk.LEFT)
                    tk.Label(row, text=f"WR {cs['wr']}%  ← FRACO",
                             font=("Segoe UI", 9, "bold"), bg=BG_MEDIUM, fg=DANGER
                             ).pack(side=tk.LEFT, padx=8)

        if not found:
            tk.Label(parent,
                     text="Nenhum ponto fraco significativo identificado\n"
                          "(WR < 45% com ≥ 3 partidas).",
                     font=("Segoe UI", 10), bg=BG_DARKEST, fg=TEXT_DIM,
                     justify="center"
                     ).pack(pady=30)

    # ─────────────────────────────────────────────────────────────────
    #  RADAR VS LOUD
    # ─────────────────────────────────────────────────────────────────

    def _open_radar(self, role: str):
        """Abre PlayerComparisonView entre o adversário e o jogador da LOUD na mesma role."""
        from riot_api.performance_radar import compute_player_metrics, normalize_metrics, ROLE_BENCHMARKS, DEFAULT_BENCHMARK
        from riot_api.player_comparison import PlayerComparisonView

        opp_team   = self._teams.get(self._sel, {})
        home_team  = self._teams.get(HOME_TEAM, {})

        opp_player  = next((p for p in opp_team.get("players", [])  if p.get("role") == role), None)
        home_player = next((p for p in home_team.get("players", []) if p.get("role") == role), None)

        if not opp_player or not home_player:
            messagebox.showwarning("Radar", "Configure os accounts de ambos os jogadores primeiro.", parent=self)
            return

        # Busca PUUIDs e stats
        opp_puuid  = self.api.get_puuid(opp_player["game_name"],  opp_player["tag"])
        home_puuid = self.api.get_puuid(home_player["game_name"], home_player["tag"])

        if not opp_puuid or not home_puuid:
            messagebox.showwarning("Radar", "Não foi possível obter PUUID de um dos jogadores.", parent=self)
            return

        def _build(puuid, player_info):
            summaries = []
            ids = self.api.get_match_ids(puuid, count=20)
            for mid in (ids or []):
                data = self.api.get_match_data(mid)
                if data:
                    s = self.api.get_match_summary(data, puuid)
                    if s:
                        summaries.append(s)
            raw  = compute_player_metrics(summaries)
            bench = ROLE_BENCHMARKS.get(role, DEFAULT_BENCHMARK)
            norm = normalize_metrics(raw, bench)
            return {"player": player_info, "raw": raw, "norm": norm, "n_games": len(summaries)}

        def _run():
            try:
                pd_opp  = _build(opp_puuid,  dict(opp_player,  display=opp_player.get("game_name"),  role=role))
                pd_home = _build(home_puuid, dict(home_player, display=home_player.get("game_name"), role=role))
                self.root.after(0, lambda: PlayerComparisonView(self.root, [pd_home, pd_opp]))
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Erro", str(e))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────
    #  FETCH DE DADOS
    # ─────────────────────────────────────────────────────────────────

    def _fetch_team(self, name: str, force: bool = False):
        """Busca champion pool do time em background."""
        if name in self._loading:
            return
        if not force and name in self._pool_cache:
            return

        team = self._teams.get(name, {})
        if team.get("cn_only"):
            return

        players = team.get("players", [])
        if not any(p.get("game_name") for p in players):
            return

        self._loading.add(name)
        self._set_status(name, "⟳", WARNING)

        # Atualiza loading nos tabs se for o time selecionado
        if name == self._sel:
            self._build_team_detail()

        threading.Thread(
            target=self._fetch_worker, args=(name, players), daemon=True
        ).start()

    def _fetch_worker(self, team_name: str, players: list):
        pool: dict[str, list] = {}
        try:
            for player in players:
                gn   = player.get("game_name", "").strip()
                tag  = player.get("tag", "").strip()
                role = player.get("role", "")
                if not gn or not role:
                    continue

                puuid = self.api.get_puuid(gn, tag)
                if not puuid:
                    continue

                ids = self.api.get_match_ids(puuid, count=MATCH_COUNT, queue=420)
                if not ids:
                    ids = self.api.get_match_ids(puuid, count=MATCH_COUNT)
                if not ids:
                    continue

                champ_stats: dict[str, dict] = {}
                for mid in ids:
                    if self._closed:
                        return
                    data = self.api.get_match_data(mid)
                    if not data:
                        continue
                    p = self.api.get_participant_by_puuid(data, puuid)
                    if not p:
                        continue
                    dur = data.get("info", {}).get("gameDuration", 0)
                    if dur < 60:
                        continue

                    champ = p.get("championName", "")
                    if not champ:
                        continue

                    if champ not in champ_stats:
                        champ_stats[champ] = {"games": 0, "wins": 0,
                                              "kills": 0, "deaths": 0, "assists": 0}
                    s = champ_stats[champ]
                    s["games"]   += 1
                    if p.get("win"):
                        s["wins"] += 1
                    s["kills"]   += p.get("kills", 0)
                    s["deaths"]  += p.get("deaths", 0)
                    s["assists"] += p.get("assists", 0)

                ranked = []
                for champ, s in sorted(champ_stats.items(),
                                       key=lambda x: x[1]["games"], reverse=True):
                    g  = s["games"]
                    wr = round(s["wins"] / g * 100) if g else 0
                    kda = (s["kills"] + s["assists"]) / max(s["deaths"], 1)
                    ranked.append({"champ": champ, "games": g, "wr": wr, "kda": round(kda, 2)})
                pool[role] = ranked

        except Exception:
            pass
        finally:
            self._loading.discard(team_name)
            if pool:
                self._pool_cache[team_name] = pool
                self.root.after(0, self._on_fetch_done, team_name)
            else:
                self.root.after(0, self._set_status, team_name, "✗", DANGER)

    def _on_fetch_done(self, team_name: str):
        self._set_status(team_name, "●", SUCCESS)
        if team_name == self._sel:
            self._build_team_detail()

    def _set_status(self, team_name: str, text: str, color: str):
        lbl = self._status_lbls.get(team_name)
        if lbl:
            try:
                lbl.config(text=text, fg=color)
            except tk.TclError:
                pass

    # ─────────────────────────────────────────────────────────────────
    #  EDIÇÃO DE ROSTER
    # ─────────────────────────────────────────────────────────────────

    def _edit_roster(self, team_name: str):
        """Abre dialog para editar accounts dos jogadores do time."""
        team = self._teams.get(team_name)
        if not team:
            return

        win = tk.Toplevel(self.root)
        win.title(f"Editar Roster — {team.get('display', team_name)}")
        win.configure(bg=BG_DARKEST)
        win.resizable(False, False)

        tk.Label(win, text=f"Contas do {team.get('display', team_name)}",
                 font=("Segoe UI", 11, "bold"),
                 bg=BG_DARKEST, fg=TEXT_BRIGHT).pack(padx=20, pady=(14, 6))

        entries: list[tuple] = []
        for player in team.get("players", []):
            role = player.get("role", "")
            color = ROLE_COLORS.get(role, ACCENT)
            short = ROLE_SHORT.get(role, role[:3])

            row = tk.Frame(win, bg=BG_DARK)
            row.pack(fill=tk.X, padx=10, pady=3)

            tk.Label(row, text=f" {short} ", font=("Segoe UI", 8, "bold"),
                     bg=color, fg=BG_DARKEST, width=4).pack(side=tk.LEFT, padx=(8, 6), pady=6)

            gn_var = tk.StringVar(value=player.get("game_name", ""))
            tag_var = tk.StringVar(value=player.get("tag", ""))
            reg_var = tk.StringVar(value=player.get("region", "br1"))

            tk.Entry(row, textvariable=gn_var, font=("Segoe UI", 9),
                     bg=BG_LIGHT, fg=TEXT_BRIGHT, insertbackground=ACCENT,
                     width=20, relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
            tk.Label(row, text="#", bg=BG_DARK, fg=TEXT_DIM,
                     font=("Segoe UI", 9)).pack(side=tk.LEFT)
            tk.Entry(row, textvariable=tag_var, font=("Segoe UI", 9),
                     bg=BG_LIGHT, fg=TEXT_BRIGHT, insertbackground=ACCENT,
                     width=6, relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

            # Região
            regions = ["br1", "kr", "na1", "euw1", "eune1", "sg2", "vn2", "la1", "la2"]
            cb = ttk.Combobox(row, textvariable=reg_var, values=regions,
                              width=6, state="readonly", font=("Segoe UI", 8))
            cb.pack(side=tk.LEFT, padx=6)

            entries.append((player, gn_var, tag_var, reg_var))

        def _save():
            for player, gn_v, tag_v, reg_v in entries:
                player["game_name"] = gn_v.get().strip()
                player["tag"]       = tag_v.get().strip()
                player["region"]    = reg_v.get().strip()
            save_roster(self._teams)
            # Invalida cache do time editado
            self._pool_cache.pop(team_name, None)
            win.destroy()
            self._build_team_detail()

        tk.Button(win, text="💾 Salvar", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg=BG_DARKEST, relief=tk.FLAT, cursor="hand2",
                  padx=20, pady=6, command=_save
                  ).pack(pady=(10, 14))

    def _add_team(self):
        """Adiciona um time customizado."""
        name = simpledialog.askstring("Novo Time", "Nome do time:", parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self._teams:
            messagebox.showwarning("Aviso", f"Time '{name}' já existe.", parent=self)
            return

        self._teams[name] = {
            "display": name, "region": "Custom", "server": "br1",
            "color": ACCENT, "is_home": False,
            "players": [
                {"role": r, "game_name": "", "tag": "", "region": "br1"}
                for r in ROLE_ORDER
            ]
        }
        self._order.append(name)
        save_roster(self._teams)
        self._build_team_list()
        self._select_team(name)

    def _refresh_all(self):
        """Força atualização de todos os times."""
        self._pool_cache.clear()
        for name in self._order:
            self._fetch_team(name, force=True)
        self._build_team_detail()

    def destroy(self):
        self._closed = True
        super().destroy()
