# -*- coding: utf-8 -*-
"""
ScrimDashboard — Dashboard de scrimmages para análise de time vs adversário.

Permite:
  · Registrar sessões de scrim (match IDs + nome do adversário)
  · Calcular métricas de performance por jogador em cada scrim
  · Comparar nosso time vs adversário (lane por lane) se IDs fornecidos
  · Acompanhar evolução ao longo de múltiplas sessões
  · Exibir radar chart de cada jogador no contexto do scrim
"""

import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import json
import os
import re
import math
from datetime import datetime

from .performance_radar import (
    compute_player_metrics,
    normalize_metrics,
    METRICS_ORDER,
    METRICS_LABELS,
    METRICS_ICONS,
    ROLE_BENCHMARKS,
    ROLE_COLORS,
    _format_metric,
    _blend_color,
    _label_anchor,
    PlayerRadar,
)

# ═══════════════════════════════════════════════════════════════════════
#  PALETA
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

ROW_WIN     = "#0f2a14"
ROW_LOSS    = "#2a0f0f"
ROW_SEL     = "#1a3a5f"

PAIN_BLUE   = "#005bac"
PAIN_GOLD   = "#f5a623"

# ═══════════════════════════════════════════════════════════════════════
#  PERSISTÊNCIA
# ═══════════════════════════════════════════════════════════════════════
SCRIMS_FILE = os.path.join(os.path.dirname(__file__), "..", "scrims.json")

ROLE_ORDER = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]


class ScrimManager:
    """Carrega, salva e manipula sessões de scrim em scrims.json."""

    def __init__(self):
        self._sessions: list[dict] = []
        self._load()

    # ─────────────────────────────────────────────────────────────────

    def _load(self):
        try:
            with open(SCRIMS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._sessions = data.get("sessions", [])
        except (FileNotFoundError, json.JSONDecodeError):
            self._sessions = []

    def _save(self):
        try:
            with open(SCRIMS_FILE, "w", encoding="utf-8") as f:
                json.dump({"sessions": self._sessions}, f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ScrimManager] Erro ao salvar: {e}")

    # ─────────────────────────────────────────────────────────────────

    @property
    def sessions(self) -> list:
        return list(self._sessions)

    def add_session(self, opponent: str, match_ids: list[str],
                    notes: str = "", date: str = "") -> dict:
        sess_id = f"scrim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        session = {
            "id":        sess_id,
            "date":      date,
            "opponent":  opponent,
            "match_ids": [m.strip() for m in match_ids if m.strip()],
            "notes":     notes,
        }
        self._sessions.append(session)
        self._save()
        return session

    def remove_session(self, sess_id: str):
        self._sessions = [s for s in self._sessions if s["id"] != sess_id]
        self._save()

    def update_session(self, sess_id: str, **kwargs):
        for s in self._sessions:
            if s["id"] == sess_id:
                s.update(kwargs)
                break
        self._save()

    def get_opponents(self) -> list[str]:
        seen = []
        for s in self._sessions:
            opp = s.get("opponent", "")
            if opp and opp not in seen:
                seen.append(opp)
        return seen


# ═══════════════════════════════════════════════════════════════════════
#  JANELA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════

class ScrimDashboard(tk.Toplevel):
    """
    Dashboard de scrims com:
    · Lista de sessões (esquerda)
    · Detalhes + métricas por jogador (direita)
    """

    def __init__(self, root, match_api, roster: list, map_visualizer=None):
        """
        match_api      : instância de MatchAPI
        roster         : lista de dicts {game_name, tag_line, role, display}
        map_visualizer : MapVisualizer (para ícones de campeão, opcional)
        """
        super().__init__(root)
        self.title("VisionLOL — Scrims Dashboard")
        self.configure(bg=BG_DARKEST)
        self.geometry("1120x700")
        self.resizable(True, True)
        self.lift()

        self.match_api  = match_api
        self.roster     = roster
        self.map_viz    = map_visualizer
        self.scrim_mgr  = ScrimManager()

        # Cache local de match data {match_id: data}
        self._match_cache: dict = {}
        # PUUIDs resolvidos {game_name#tag: puuid}
        self._puuids: dict      = {}
        # Sessão selecionada
        self._selected_id: str | None = None
        # Widgets de linha de sessão {sess_id: (container, row)}
        self._sess_rows: dict   = {}
        # Estado de loading
        self._loading = False

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._closed = False

        self._build()

        # Pré-carrega PUUIDs do roster em background
        threading.Thread(target=self._preload_puuids, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────────────

    def _build(self):
        self._build_header()

        body = tk.Frame(self, bg=BG_DARKEST)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # Painel esquerdo: lista de sessões
        left = tk.Frame(body, bg=BG_DARKEST, width=320)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        # Painel direito: detalhes
        right = tk.Frame(body, bg=BG_DARKEST)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self._build_session_panel(left)
        self._build_detail_panel(right)

    def _build_header(self):
        hdr = tk.Frame(self, bg=PAIN_BLUE, height=56)
        hdr.pack(fill=tk.X, padx=10, pady=(8, 6))
        hdr.pack_propagate(False)

        left_h = tk.Frame(hdr, bg=PAIN_BLUE)
        left_h.pack(side=tk.LEFT, padx=14, pady=8)

        tk.Label(left_h, text="⚔",
                 font=("Segoe UI", 18),
                 bg=PAIN_BLUE, fg=PAIN_GOLD).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(left_h, text="Scrims",
                 font=("Segoe UI", 16, "bold"),
                 bg=PAIN_BLUE, fg=PAIN_GOLD).pack(side=tk.LEFT)
        tk.Label(left_h, text=" Dashboard",
                 font=("Segoe UI", 16, "bold"),
                 bg=PAIN_BLUE, fg=TEXT_BRIGHT).pack(side=tk.LEFT)

        # Stats rápidas no header
        self._hdr_stats = tk.Label(hdr, text="",
                                   font=("Segoe UI", 10),
                                   bg=PAIN_BLUE, fg="#a8c4e0")
        self._hdr_stats.pack(side=tk.RIGHT, padx=14)

        # Botão adicionar scrim
        btn_add = tk.Button(hdr,
                            text="＋ Nova Sessão",
                            font=("Segoe UI", 9, "bold"),
                            bg="#1a5f3f", fg=TEXT_COLOR,
                            relief=tk.FLAT, cursor="hand2",
                            padx=10, pady=4,
                            command=self._add_session)
        btn_add.pack(side=tk.RIGHT, padx=(0, 8), pady=12)

        self._update_header_stats()

    def _build_session_panel(self, parent):
        _sec_label(parent, "SESSÕES DE SCRIM")

        # Container scrollável
        outer = tk.Frame(parent, bg=BG_DARKEST)
        outer.pack(fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(outer, orient="vertical")
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._sess_canvas = tk.Canvas(
            outer, bg=BG_DARKEST, highlightthickness=0,
            yscrollcommand=sb.set
        )
        self._sess_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self._sess_canvas.yview)

        self._sess_frame = tk.Frame(self._sess_canvas, bg=BG_DARKEST)
        self._sess_win_id = self._sess_canvas.create_window(
            (0, 0), window=self._sess_frame, anchor="nw"
        )

        self._sess_frame.bind("<Configure>",
            lambda e: self._sess_canvas.configure(
                scrollregion=self._sess_canvas.bbox("all")))
        self._sess_canvas.bind("<Configure>",
            lambda e: self._sess_canvas.itemconfig(self._sess_win_id, width=e.width))
        self._sess_canvas.bind("<MouseWheel>",
            lambda e: self._sess_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._render_session_list()

    def _build_detail_panel(self, parent):
        self._detail_frame = tk.Frame(parent, bg=BG_DARKEST)
        self._detail_frame.pack(fill=tk.BOTH, expand=True)
        self._show_empty_detail()

    # ─────────────────────────────────────────────────────────────────
    #  LISTA DE SESSÕES
    # ─────────────────────────────────────────────────────────────────

    def _render_session_list(self):
        for w in self._sess_frame.winfo_children():
            w.destroy()
        self._sess_rows.clear()

        sessions = self.scrim_mgr.sessions
        if not sessions:
            tk.Label(self._sess_frame,
                     text="Nenhuma sessão registrada.\n\nClique em  ＋ Nova Sessão\npara começar.",
                     font=("Segoe UI", 10), bg=BG_DARKEST, fg=TEXT_DIM,
                     justify="center").pack(pady=40)
            return

        # Ordena da mais recente para a mais antiga
        sessions_sorted = sorted(sessions,
                                 key=lambda s: s.get("date", ""), reverse=True)

        for sess in sessions_sorted:
            self._add_session_row(sess)

    def _add_session_row(self, sess: dict):
        sid = sess["id"]

        container = tk.Frame(self._sess_frame, bg=BG_DARKEST, pady=0)
        container.pack(fill=tk.X, pady=1)

        row = tk.Frame(container, bg=BG_MEDIUM, pady=0)
        row.pack(fill=tk.X, padx=1)

        # Data
        date_str = sess.get("date", "")[:10]
        tk.Label(row, text=date_str,
                 font=("Segoe UI", 8), bg=BG_MEDIUM, fg=TEXT_DIM,
                 width=10, anchor="w").pack(side=tk.LEFT, padx=(6, 0), pady=6)

        # Adversário
        tk.Label(row, text=f"vs  {sess.get('opponent', '?')}",
                 font=("Segoe UI", 10, "bold"), bg=BG_MEDIUM, fg=DANGER,
                 anchor="w").pack(side=tk.LEFT, padx=6)

        # Número de partidas
        n_m = len(sess.get("match_ids", []))
        tk.Label(row, text=f"{n_m} jogo{'s' if n_m != 1 else ''}",
                 font=("Segoe UI", 8), bg=BG_MEDIUM, fg=TEXT_DIM
                 ).pack(side=tk.LEFT, padx=(0, 4))

        # Notas (truncadas)
        notes = sess.get("notes", "")
        if notes:
            tk.Label(row, text=f"· {notes[:28]}{'…' if len(notes) > 28 else ''}",
                     font=("Segoe UI", 8, "italic"), bg=BG_MEDIUM, fg=TEXT_DIM
                     ).pack(side=tk.LEFT, padx=4)

        # Botão remover
        del_btn = tk.Button(row, text="✕",
                            font=("Segoe UI", 8),
                            bg=BG_MEDIUM, fg=TEXT_DIM,
                            relief=tk.FLAT, cursor="hand2",
                            command=lambda s=sess: self._remove_session(s["id"]))
        del_btn.pack(side=tk.RIGHT, padx=4)

        # Clique para selecionar
        click_cb = lambda e, s=sess: self._select_session(s["id"])
        for w in [container, row] + list(row.winfo_children()):
            try:
                w.bind("<Button-1>", click_cb)
                w.config(cursor="hand2")
            except Exception:
                pass

        self._sess_rows[sid] = (container, row)

    # ─────────────────────────────────────────────────────────────────
    #  SELEÇÃO DE SESSÃO
    # ─────────────────────────────────────────────────────────────────

    def _select_session(self, sess_id: str):
        # Alterna seleção
        new_sel = None if self._selected_id == sess_id else sess_id
        self._selected_id = new_sel

        # Atualiza highlight
        for sid, (cont, row) in self._sess_rows.items():
            if sid == new_sel:
                cont.config(bg=ACCENT)
                row.config(bg=ROW_SEL)
                for w in row.winfo_children():
                    try: w.config(bg=ROW_SEL)
                    except Exception: pass
            else:
                cont.config(bg=BG_DARKEST)
                row.config(bg=BG_MEDIUM)
                for w in row.winfo_children():
                    try: w.config(bg=BG_MEDIUM)
                    except Exception: pass

        if new_sel:
            sess = next((s for s in self.scrim_mgr.sessions if s["id"] == new_sel), None)
            if sess:
                self._load_session_detail(sess)
        else:
            self._show_empty_detail()

    # ─────────────────────────────────────────────────────────────────
    #  PAINEL DE DETALHES
    # ─────────────────────────────────────────────────────────────────

    def _show_empty_detail(self):
        for w in self._detail_frame.winfo_children():
            w.destroy()
        tk.Label(self._detail_frame,
                 text="Selecione uma sessão de scrim para ver os detalhes.",
                 font=("Segoe UI", 11), bg=BG_DARKEST, fg=TEXT_DIM
                 ).pack(expand=True)

    def _load_session_detail(self, sess: dict):
        for w in self._detail_frame.winfo_children():
            w.destroy()

        # Header da sessão
        sh = tk.Frame(self._detail_frame, bg=BG_DARK, height=48)
        sh.pack(fill=tk.X, pady=(0, 6))
        sh.pack_propagate(False)

        tk.Label(sh, text=f"⚔  vs {sess.get('opponent', '?')}",
                 font=("Segoe UI", 13, "bold"),
                 bg=BG_DARK, fg=DANGER).pack(side=tk.LEFT, padx=14, pady=10)
        tk.Label(sh, text=sess.get("date", "")[:10],
                 font=("Segoe UI", 10), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.LEFT, padx=4)

        notes = sess.get("notes", "")
        if notes:
            tk.Label(sh, text=f"· {notes}",
                     font=("Segoe UI", 9, "italic"), bg=BG_DARK, fg=TEXT_DIM
                     ).pack(side=tk.LEFT, padx=8)

        n_m = len(sess.get("match_ids", []))
        tk.Label(sh, text=f"{n_m} partida{'s' if n_m != 1 else ''}",
                 font=("Segoe UI", 10), bg=BG_DARK, fg=ACCENT
                 ).pack(side=tk.RIGHT, padx=14)

        # Status de carregamento
        self._detail_status = tk.Label(
            self._detail_frame,
            text="Carregando dados das partidas…",
            font=("Segoe UI", 10), bg=BG_DARKEST, fg=ACCENT
        )
        self._detail_status.pack(pady=20)

        # Lança thread para carregar dados
        match_ids = sess.get("match_ids", [])
        threading.Thread(
            target=self._fetch_session_data,
            args=(sess, match_ids),
            daemon=True
        ).start()

    def _fetch_session_data(self, sess: dict, match_ids: list):
        """Busca match data de todas as partidas da sessão."""
        fetched = {}
        total   = len(match_ids)
        for i, mid in enumerate(match_ids):
            if self._closed:
                return
            self.after(0, self._set_status,
                       f"Carregando partida {i + 1}/{total}  ({mid})…")
            if mid in self._match_cache:
                fetched[mid] = self._match_cache[mid]
                continue
            try:
                data = self.match_api.get_match_data(mid)
                if data:
                    fetched[mid] = data
                    self._match_cache[mid] = data
            except Exception as e:
                print(f"[ScrimDashboard] Erro ao buscar {mid}: {e}")

        if not self._closed:
            self.after(0, self._render_session_detail, sess, fetched)

    def _render_session_detail(self, sess: dict, match_cache: dict):
        """Renderiza métricas por jogador para a sessão carregada."""
        if self._closed:
            return

        # Remove spinner
        if self._detail_status and self._detail_status.winfo_exists():
            self._detail_status.destroy()

        if not match_cache:
            tk.Label(self._detail_frame,
                     text="⚠ Nenhum dado encontrado para as partidas desta sessão.\n"
                          "Verifique se os Match IDs estão corretos.",
                     font=("Segoe UI", 10), bg=BG_DARKEST, fg=DANGER,
                     justify="center").pack(pady=30)
            return

        # Verifica se temos PUUIDs
        missing = [p for p in self.roster if
                   f"{p['game_name']}#{p['tag_line']}" not in self._puuids]
        if missing:
            self._set_status("Resolvendo PUUIDs…")
            for p in missing:
                key  = f"{p['game_name']}#{p['tag_line']}"
                puuid = self.match_api.get_puuid(p["game_name"], p["tag_line"])
                if puuid:
                    self._puuids[key] = puuid

        # ─ Tabela de partidas ────────────────────────────────────────
        _sec_label(self._detail_frame, "PARTIDAS DA SESSÃO")
        self._build_matches_table(match_cache)

        # ─ Métricas por jogador ──────────────────────────────────────
        tk.Frame(self._detail_frame, bg=BORDER, height=1).pack(fill=tk.X, pady=6)
        _sec_label(self._detail_frame, "PERFORMANCE POR JOGADOR — NESTA SESSÃO")

        # Container scrollável para os cards de jogador
        outer = tk.Frame(self._detail_frame, bg=BG_DARKEST)
        outer.pack(fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(outer, orient="vertical")
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        canvas = tk.Canvas(outer, bg=BG_DARKEST, highlightthickness=0,
                           yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=canvas.yview)

        inner = tk.Frame(canvas, bg=BG_DARKEST)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        for player in self.roster:
            key   = f"{player['game_name']}#{player['tag_line']}"
            puuid = self._puuids.get(key)
            if not puuid:
                continue

            # Constrói summaries no formato esperado por compute_player_metrics
            summaries = [
                (mid, {"win": False}, md)
                for mid, md in match_cache.items()
            ]

            raw  = compute_player_metrics(summaries, {}, puuid)
            norm = normalize_metrics(raw, player.get("role", "MID"))

            n_games = sum(
                1 for _, md in match_cache.items()
                for p in md.get("info", {}).get("participants", [])
                if p.get("puuid") == puuid
            )

            self._build_player_scrim_card(
                inner, player, puuid, raw, norm, n_games,
                sess, match_cache
            )

    def _build_matches_table(self, match_cache: dict):
        """Tabela compacta de partidas (resultado, duração, campeões)."""
        tbl = tk.Frame(self._detail_frame, bg=BG_DARKEST)
        tbl.pack(fill=tk.X, pady=(0, 4))

        # Cabeçalho
        hdr = tk.Frame(tbl, bg=BG_MEDIUM)
        hdr.pack(fill=tk.X, pady=(0, 2))
        for txt, w in [("Partida", 18), ("Duração", 8), ("Resultado", 10),
                       ("Campeões (Nosso Time)", 40)]:
            tk.Label(hdr, text=txt, font=("Segoe UI", 8, "bold"),
                     bg=BG_MEDIUM, fg=TEXT_DIM, width=w, anchor="w",
                     padx=4).pack(side=tk.LEFT, pady=3)

        for mid, md in match_cache.items():
            if not md:
                continue
            info     = md.get("info", {})
            dur_s    = info.get("gameDuration", 0)
            dur_str  = f"{dur_s // 60}:{dur_s % 60:02d}"

            # Identifica nosso time pelas PUUIDs do roster
            our_puuids = set(self._puuids.values())
            our_team_id = None
            for p in info.get("participants", []):
                if p.get("puuid") in our_puuids:
                    our_team_id = p.get("teamId")
                    break

            our_won = False
            our_champs = []
            if our_team_id:
                for p in info.get("participants", []):
                    if p.get("teamId") == our_team_id:
                        our_won = p.get("win", False)
                        champ   = p.get("championName", "?")
                        role    = p.get("teamPosition", "")
                        our_champs.append(f"{champ}({role[:3] or '?'})")

            row_bg = ROW_WIN if our_won else ROW_LOSS
            row = tk.Frame(tbl, bg=row_bg)
            row.pack(fill=tk.X, pady=1)

            mid_short = mid[-10:] if len(mid) > 10 else mid
            tk.Label(row, text=f"…{mid_short}",
                     font=("Segoe UI", 8), bg=row_bg, fg=TEXT_DIM,
                     width=18, anchor="w", padx=4).pack(side=tk.LEFT, pady=3)
            tk.Label(row, text=dur_str,
                     font=("Segoe UI", 8), bg=row_bg, fg=TEXT_COLOR,
                     width=8, anchor="w").pack(side=tk.LEFT)

            result_fg = SUCCESS if our_won else DANGER
            result_tx = "✓ Vitória" if our_won else "✕ Derrota"
            tk.Label(row, text=result_tx,
                     font=("Segoe UI", 8, "bold"), bg=row_bg, fg=result_fg,
                     width=10, anchor="w").pack(side=tk.LEFT)

            champs_str = "  ".join(our_champs[:5])
            tk.Label(row, text=champs_str,
                     font=("Segoe UI", 8), bg=row_bg, fg=TEXT_COLOR,
                     anchor="w").pack(side=tk.LEFT, padx=4)

    def _build_player_scrim_card(self, parent, player: dict, puuid: str,
                                  raw: dict, norm: dict, n_games: int,
                                  sess: dict, match_cache: dict):
        """Card de jogador com mini-radar + métricas + botão de radar completo."""
        role  = player.get("role", "MID").upper()
        color = ROLE_COLORS.get(role, ACCENT)
        name  = player.get("display", player.get("game_name", "?"))

        card = tk.Frame(parent, bg=BG_DARK, pady=0)
        card.pack(fill=tk.X, pady=2)

        # Barra lateral por role
        tk.Frame(card, bg=color, width=4).pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(card, bg=BG_DARK)
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        # ─ Mini-cabeçalho ─────────────────────────────────────────────
        head = tk.Frame(inner, bg=BG_DARK)
        head.pack(fill=tk.X)

        tk.Label(head, text=f" {role[:3]} ",
                 font=("Segoe UI", 8, "bold"),
                 bg=color, fg=BG_DARKEST).pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(head, text=name,
                 font=("Segoe UI", 11, "bold"),
                 bg=BG_DARK, fg=TEXT_BRIGHT).pack(side=tk.LEFT)
        tk.Label(head, text=f"  {n_games} partida{'s' if n_games != 1 else ''}",
                 font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM
                 ).pack(side=tk.LEFT)

        # Botão abrir radar completo
        btn_radar = tk.Button(
            head, text="🕸 Ver Radar",
            font=("Segoe UI", 8, "bold"),
            bg=BG_LIGHT, fg=ACCENT,
            relief=tk.FLAT, cursor="hand2", padx=6, pady=2,
            command=lambda p=player, pu=puuid, mc=match_cache: self._open_radar(
                p, pu, mc
            )
        )
        btn_radar.pack(side=tk.RIGHT, padx=4)

        # ─ Corpo: mini-radar + barras de métricas ─────────────────────
        body = tk.Frame(inner, bg=BG_DARK)
        body.pack(fill=tk.X, pady=(4, 0))

        # Mini-radar (140x140)
        mini_size = 148
        mini_canvas = tk.Canvas(body,
                                width=mini_size, height=mini_size,
                                bg=BG_DARK, highlightthickness=0)
        mini_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self._draw_mini_radar(mini_canvas, mini_size, norm, color)

        # Barras de métricas
        bars = tk.Frame(body, bg=BG_DARK)
        bars.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        bench = ROLE_BENCHMARKS.get(role, ROLE_BENCHMARKS["MID"])
        for metric in METRICS_ORDER:
            r_val = raw.get(metric, 0.0)
            n_val = norm.get(metric, 0.0)
            ref   = bench.get(metric, 1.0)
            val_s, ref_s = _format_metric(metric, r_val, ref)
            pct_c = min(max(n_val, 0.0), 1.0)
            bar_c = SUCCESS if n_val >= 0.85 else (WARNING if n_val >= 0.60 else DANGER)

            mrow = tk.Frame(bars, bg=BG_DARK)
            mrow.pack(fill=tk.X, pady=1)

            tk.Label(mrow,
                     text=f"{METRICS_ICONS[metric]} {METRICS_LABELS[metric]}",
                     font=("Segoe UI", 8), bg=BG_DARK, fg=TEXT_DIM,
                     width=14, anchor="w").pack(side=tk.LEFT)
            tk.Label(mrow, text=val_s,
                     font=("Segoe UI", 8, "bold"), bg=BG_DARK, fg=bar_c,
                     width=7, anchor="e").pack(side=tk.LEFT)

            bg_bar = tk.Frame(mrow, bg=BG_LIGHT, height=7, width=180)
            bg_bar.pack(side=tk.LEFT, padx=(4, 0))
            bg_bar.pack_propagate(False)
            if pct_c > 0:
                tk.Frame(bg_bar, bg=bar_c, height=7).place(
                    relwidth=pct_c, relheight=1.0, x=0, y=0
                )
            tk.Label(mrow, text=f"ref {ref_s}",
                     font=("Segoe UI", 7), bg=BG_DARK, fg=TEXT_DIM,
                     width=7).pack(side=tk.LEFT, padx=4)

    def _draw_mini_radar(self, canvas, size: int, norm: dict, color: str):
        """Mini-radar para o card de jogador."""
        cx  = size // 2
        cy  = size // 2
        R   = size // 2 - 20
        n   = len(METRICS_ORDER)
        ang = [-math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        # Grid
        for level in [0.5, 1.0]:
            pts = []
            for a in ang:
                pts.extend([cx + R * level * math.cos(a),
                             cy + R * level * math.sin(a)])
            canvas.create_polygon(pts, outline=BORDER if level == 1 else "#1e2630",
                                  fill="", width=1 if level < 1 else 2)
        for a in ang:
            canvas.create_line(cx, cy,
                               cx + R * math.cos(a), cy + R * math.sin(a),
                               fill="#1e2630", width=1)

        # Polígono
        pts = []
        for i, metric in enumerate(METRICS_ORDER):
            v = norm.get(metric, 0.0)
            pts.extend([cx + R * v * math.cos(ang[i]),
                        cy + R * v * math.sin(ang[i])])

        fill_c = _blend_color(color, BG_DARK, 0.28)
        canvas.create_polygon(pts, fill=fill_c, outline=color, width=2)

        # Pontos
        for i, metric in enumerate(METRICS_ORDER):
            v  = norm.get(metric, 0.0)
            px = cx + R * v * math.cos(ang[i])
            py = cy + R * v * math.sin(ang[i])
            canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                               fill=color, outline=BG_DARK, width=1)

        # Rótulos compactos
        pad = 13
        for i, metric in enumerate(METRICS_ORDER):
            a  = ang[i]
            lx = cx + (R + pad) * math.cos(a)
            ly = cy + (R + pad) * math.sin(a)
            canvas.create_text(lx, ly,
                               text=METRICS_LABELS[metric][:4],
                               font=("Segoe UI", 6), fill=TEXT_DIM,
                               anchor=_label_anchor(a))

    # ─────────────────────────────────────────────────────────────────
    #  AÇÕES
    # ─────────────────────────────────────────────────────────────────

    def _add_session(self):
        """Diálogo passo-a-passo para adicionar sessão de scrim."""
        opponent = simpledialog.askstring(
            "Nova Sessão de Scrim",
            "Nome do time adversário:\n(ex: LOUD, RED Canids, Flamengo)",
            parent=self
        )
        if not opponent or not opponent.strip():
            return

        ids_raw = simpledialog.askstring(
            "IDs das Partidas",
            "Cole os Match IDs das partidas (separados por vírgula ou nova linha):\n"
            "Exemplo: BR1_3212841836, BR1_3212818739",
            parent=self
        )
        if not ids_raw or not ids_raw.strip():
            return

        # Separa IDs por vírgula, espaço, ou nova linha
        match_ids = [m.strip() for m in re.split(r"[,\s\n]+", ids_raw) if m.strip()]
        if not match_ids:
            messagebox.showwarning("Atenção", "Nenhum Match ID válido informado.",
                                   parent=self)
            return

        notes = simpledialog.askstring(
            "Observações (opcional)",
            "Observações sobre esta sessão:\n(ex: BO3 treino pré-CBLOL, fase de grupos)",
            parent=self
        ) or ""

        date_str = simpledialog.askstring(
            "Data (opcional)",
            f"Data da sessão (YYYY-MM-DD).\nDeixe em branco para usar hoje:",
            parent=self
        ) or ""

        sess = self.scrim_mgr.add_session(
            opponent=opponent.strip(),
            match_ids=match_ids,
            notes=notes.strip(),
            date=date_str.strip()
        )

        self._render_session_list()
        self._update_header_stats()
        self._select_session(sess["id"])

    def _remove_session(self, sess_id: str):
        ok = messagebox.askyesno(
            "Remover Sessão",
            "Remover esta sessão de scrim?",
            parent=self
        )
        if not ok:
            return
        self.scrim_mgr.remove_session(sess_id)
        if self._selected_id == sess_id:
            self._selected_id = None
            self._show_empty_detail()
        self._render_session_list()
        self._update_header_stats()

    def _open_radar(self, player: dict, puuid: str, match_cache: dict):
        """Abre o radar completo do jogador para as partidas da sessão."""
        summaries = [(mid, {}, md) for mid, md in match_cache.items()]
        PlayerRadar(
            self,
            player=player,
            summaries=summaries,
            match_data_cache={},
            puuid=puuid,
            role=player.get("role", "MID"),
        )

    # ─────────────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────────────

    def _set_status(self, text: str):
        if not self._closed and self._detail_status.winfo_exists():
            try:
                self._detail_status.config(text=text)
            except Exception:
                pass

    def _update_header_stats(self):
        sessions = self.scrim_mgr.sessions
        n_sess   = len(sessions)
        n_games  = sum(len(s.get("match_ids", [])) for s in sessions)
        opponents = len(self.scrim_mgr.get_opponents())
        self._hdr_stats.config(
            text=f"{n_sess} sessões  ·  {n_games} jogos  ·  {opponents} adversários"
        )

    def _preload_puuids(self):
        """Resolve PUUIDs do roster em background."""
        for player in self.roster:
            if self._closed:
                return
            key = f"{player['game_name']}#{player['tag_line']}"
            if key not in self._puuids:
                try:
                    puuid = self.match_api.get_puuid(
                        player["game_name"], player["tag_line"]
                    )
                    if puuid:
                        self._puuids[key] = puuid
                except Exception:
                    pass

    def after(self, ms, func=None, *args):
        """Wrapper seguro para after() — ignora se janela foi fechada."""
        if self._closed:
            return
        try:
            super().after(ms, func, *args)
        except Exception:
            pass

    def _on_close(self):
        self._closed = True
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════
#  HELPERS DE UI
# ═══════════════════════════════════════════════════════════════════════

def _sec_label(parent, text: str):
    tk.Label(parent, text=text,
             font=("Segoe UI", 9, "bold"),
             bg=BG_DARKEST, fg=TEXT_DIM).pack(anchor="w", padx=4, pady=(6, 2))
