# -*- coding: utf-8 -*-
"""
VisionLOL GUI v4.0 - Interface com abas: Monitor, Analytics, Pos-Jogo, Config
Integra PlayerMonitor (atencao) com Riot API (eventos do jogo)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import cv2
import time
import json
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_detector import GameDetector
from main import PlayerMonitor
from logger import get_logger

# Riot API modules
from riot_api.config import load_config, save_config
from riot_api.riot_http import RiotHTTPClient
from riot_api.live_client import LiveClientAPI
from riot_api.match_api import MatchAPI
from riot_api.proximity_tracker import ProximityTracker
from riot_api.reaction_analyzer import ReactionAnalyzer
from riot_api.data_correlator import DataCorrelator
from riot_api.map_visualizer import MapVisualizer
from riot_api.scrim_server import ScrimServer
from riot_api.pathing_visualizer import PathingVisualizer

# Inicializa logger
logger = get_logger("GUI")


class VisionLOLAppIntegrated:
    """Aplicacao principal com interface grafica integrada v4.0"""

    def __init__(self, root):
        logger.info("=" * 60)
        logger.info("Inicializando VisionLOL GUI v4.0")
        logger.info("=" * 60)

        self.root = root
        self.root.title("VisionLOL - Player Monitor v4.0")
        self.root.geometry("1100x750")
        self.root.resizable(True, True)

        # Estado da aplicacao
        self.is_monitoring = False
        self.monitor_thread = None
        self.detector = GameDetector()
        self.player_monitor = None
        self.current_frame = None
        self.session_start_time = None

        # Riot API state
        self.user_config = load_config()
        self.http_client = RiotHTTPClient(api_key=self.user_config.get("riot_api_key", ""))
        self.live_client = LiveClientAPI(self.http_client)
        self.match_api = MatchAPI(self.http_client)
        self.proximity_tracker = ProximityTracker(self.live_client, self.match_api)
        self.reaction_analyzer = ReactionAnalyzer(self.match_api)
        self.data_correlator = DataCorrelator()
        self.map_visualizer = MapVisualizer(self.match_api)
        self.pathing_visualizer = PathingVisualizer(self.map_visualizer)
        self.is_live_tracking = False
        self._cached_puuid = None

        # Servidor de scrims (opcional, ativado no Config)
        self.scrim_server = self._init_scrim_server()

        # Callback para eventos do jogo ao vivo
        self.proximity_tracker.on_event_detected = self._on_game_event

        logger.info("Estado inicial criado (com Riot API)")

        # Configurar estilo
        self.setup_style()

        # Criar interface
        self.create_widgets()

        # Iniciar loops
        self.check_game_status()
        self.update_camera_preview()

        # Configurar fechamento
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("GUI v4.0 inicializada com sucesso!")

    # ===================================================================
    #  ESTILO
    # ===================================================================

    def setup_style(self):
        """Configurar estilo visual"""
        style = ttk.Style()
        style.theme_use('clam')

        # Cores
        self.bg_dark = "#1e1e1e"
        self.bg_medium = "#2d2d2d"
        self.bg_light = "#3d3d3d"
        self.accent = "#00b4d8"
        self.success = "#06d6a0"
        self.danger = "#ef476f"
        self.warning = "#ffd60a"
        self.text = "#E0E0D8"
        self.text_dim = "#888888"

        # Configurar root
        self.root.configure(bg=self.bg_dark)

        # Estilo do Notebook (abas)
        style.configure("TNotebook", background=self.bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=self.bg_medium,
                        foreground=self.text,
                        padding=[15, 8],
                        font=("Arial", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", self.accent)],
                  foreground=[("selected", "#E0E0D8")])

    # ===================================================================
    #  WIDGETS PRINCIPAIS
    # ===================================================================

    def create_widgets(self):
        """Criar todos os widgets da interface"""

        # === HEADER ===
        header = tk.Frame(self.root, bg=self.bg_medium, height=60)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        header.pack_propagate(False)

        tk.Label(header, text="VisionLOL", font=("Arial", 22, "bold"),
                 bg=self.bg_medium, fg=self.accent).pack(side=tk.LEFT, padx=20)
        tk.Label(header, text="Player Performance Monitor v4.0", font=("Arial", 11),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT)

        # Status do jogo no header
        self.game_status_label = tk.Label(
            header, text="Verificando...", font=("Arial", 10, "bold"),
            bg=self.bg_medium, fg=self.warning
        )
        self.game_status_label.pack(side=tk.RIGHT, padx=20)

        # === NOTEBOOK (ABAS) ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: Monitor
        self.tab_monitor = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_monitor, text="  Monitor  ")
        self._create_monitor_tab()

        # Tab 2: Analytics (ao vivo)
        self.tab_analytics = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_analytics, text="  Analytics  ")
        self._create_analytics_tab()

        # Tab 3: Pos-Jogo
        self.tab_postgame = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_postgame, text="  Pos-Jogo  ")
        self._create_postgame_tab()

        # Tab 4: Config
        self.tab_config = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_config, text="  Config  ")
        self._create_config_tab()

        # Tab 5: Time (roster)
        self.tab_team = tk.Frame(self.notebook, bg="#000000")
        self.notebook.add(self.tab_team, text="  🎮 Time  ")
        self._create_team_tab()

        # Tab 6: Scouting First Stand 2025
        self.tab_scouting = tk.Frame(self.notebook, bg="#000000")
        self.notebook.add(self.tab_scouting, text="  🔍 Scouting  ")
        self._create_scouting_tab()

    def _create_scouting_tab(self):
        """Cria conteúdo da aba Scouting — First Stand 2025."""
        from riot_api.scout_viewer import ScoutingView
        ScoutingView(
            self.tab_scouting,
            http_client=self.http_client,
            match_api=self.match_api,
            app_root=self.root,
        )

    # ===================================================================
    #  TAB 1: MONITOR (funcionalidade existente)
    # ===================================================================

    def _create_monitor_tab(self):
        """Cria conteudo da aba Monitor (camera + metricas)"""
        main = tk.Frame(self.tab_monitor, bg=self.bg_dark)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left - Camera preview
        left = tk.Frame(main, bg=self.bg_medium)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(left, text="Preview da Camera", bg=self.bg_medium,
                 fg=self.text, font=("Arial", 12, "bold")).pack(pady=8)

        self.camera_canvas = tk.Canvas(left, bg=self.bg_light, width=480,
                                        height=360, highlightthickness=0)
        self.camera_canvas.pack(padx=10, pady=5)

        self.camera_status_label = tk.Label(
            left, text="Camera: Aguardando...", bg=self.bg_medium,
            fg=self.warning, font=("Arial", 10)
        )
        self.camera_status_label.pack(pady=5)

        # Right - Controls + Metrics
        right = tk.Frame(main, bg=self.bg_dark, width=320)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right.pack_propagate(False)

        # Controles
        ctrl_frame = tk.LabelFrame(right, text="Controles", bg=self.bg_medium,
                                    fg=self.text, font=("Arial", 11, "bold"))
        ctrl_frame.pack(fill=tk.X, pady=(0, 8))

        self.start_stop_btn = tk.Button(
            ctrl_frame, text="INICIAR", command=self.toggle_monitoring,
            font=("Arial", 12, "bold"), bg=self.success, fg=self.text,
            activebackground=self.accent, relief=tk.RAISED, bd=0,
            padx=20, pady=10, cursor="hand2"
        )
        self.start_stop_btn.pack(padx=12, pady=12, fill=tk.X)

        self.auto_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            ctrl_frame, text="Modo Automatico (inicia com LoL)",
            variable=self.auto_mode_var, font=("Arial", 10),
            bg=self.bg_medium, fg=self.text, selectcolor=self.bg_light,
            activebackground=self.bg_medium, activeforeground=self.text,
            command=self.toggle_auto_mode
        ).pack(padx=12, pady=(0, 12))

        # Metricas
        metrics_frame = tk.LabelFrame(right, text="Metricas em Tempo Real",
                                       bg=self.bg_medium, fg=self.text,
                                       font=("Arial", 11, "bold"))
        metrics_frame.pack(fill=tk.BOTH, expand=True)

        grid = tk.Frame(metrics_frame, bg=self.bg_medium)
        grid.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._create_metric_card(grid, "Status", "Aguardando", 0, 0, "status", self.warning)
        self._create_metric_card(grid, "Direcao", "---", 0, 1, "direction", self.text)
        self._create_metric_card(grid, "Distracoes", "0", 1, 0, "distractions", self.text)
        self._create_metric_card(grid, "APM", "0", 1, 1, "apm", self.text)
        self._create_metric_card(grid, "Tempo", "00:00", 2, 0, "time", self.text)
        self._create_metric_card(grid, "Confianca", "0%", 2, 1, "confidence", self.text)

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def _create_metric_card(self, parent, title, value, row, col, metric_id, color):
        """Cria um card de metrica"""
        card = tk.Frame(parent, bg=self.bg_light, relief=tk.FLAT, bd=1)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        tk.Label(card, text=title, font=("Arial", 9), bg=self.bg_light,
                 fg=self.text_dim).pack(pady=(6, 1))

        value_label = tk.Label(card, text=value, font=("Arial", 13, "bold"),
                                bg=self.bg_light, fg=color)
        value_label.pack(pady=(0, 6))

        setattr(self, f"metric_{metric_id}", value_label)

    # ===================================================================
    #  TAB 2: ANALYTICS (eventos ao vivo)
    # ===================================================================

    def _create_analytics_tab(self):
        """Cria conteudo da aba Analytics"""
        main = tk.Frame(self.tab_analytics, bg=self.bg_dark)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Barra de info do jogo
        info_bar = tk.Frame(main, bg=self.bg_medium, height=40)
        info_bar.pack(fill=tk.X, pady=(0, 5))
        info_bar.pack_propagate(False)

        self.analytics_status_label = tk.Label(
            info_bar, text="Aguardando partida...", font=("Arial", 11, "bold"),
            bg=self.bg_medium, fg=self.warning
        )
        self.analytics_status_label.pack(side=tk.LEFT, padx=15)

        self.analytics_time_label = tk.Label(
            info_bar, text="", font=("Arial", 10),
            bg=self.bg_medium, fg=self.text
        )
        self.analytics_time_label.pack(side=tk.RIGHT, padx=15)

        # Conteudo principal - 2 colunas
        content = tk.Frame(main, bg=self.bg_dark)
        content.pack(fill=tk.BOTH, expand=True)

        # Esquerda - Log de eventos
        left = tk.LabelFrame(content, text="Eventos ao Vivo", bg=self.bg_medium,
                              fg=self.text, font=("Arial", 11, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.events_text = tk.Text(
            left, bg=self.bg_light, fg=self.text, font=("Consolas", 10),
            wrap=tk.WORD, state=tk.DISABLED, highlightthickness=0,
            insertbackground=self.text
        )
        self.events_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tags de cores para tipos de evento
        self.events_text.tag_configure("KILL", foreground=self.success)
        self.events_text.tag_configure("DEATH", foreground=self.danger)
        self.events_text.tag_configure("ASSIST", foreground=self.accent)
        self.events_text.tag_configure("LEVEL_UP", foreground=self.warning)
        self.events_text.tag_configure("LIVE_EVENT", foreground="#b0b0b0")
        self.events_text.tag_configure("RESPAWN", foreground="#777777")
        self.events_text.tag_configure("INFO", foreground=self.text_dim)
        self.events_text.tag_configure("INSIGHT_WARN", foreground=self.danger, font=("Consolas", 10, "bold"))
        self.events_text.tag_configure("INSIGHT_OK", foreground=self.success, font=("Consolas", 10, "bold"))

        # Direita - Paineis de equipes + Insights
        right = tk.Frame(content, bg=self.bg_dark, width=300)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right.pack_propagate(False)

        # Equipe Aliada
        ally_frame = tk.LabelFrame(right, text="Equipe Aliada", bg=self.bg_medium,
                                    fg=self.success, font=("Arial", 10, "bold"))
        ally_frame.pack(fill=tk.X, pady=(0, 5))

        self.ally_labels = []
        for i in range(5):
            lbl = tk.Label(ally_frame, text="---", font=("Consolas", 9),
                           bg=self.bg_medium, fg=self.text, anchor=tk.W, padx=10)
            lbl.pack(fill=tk.X)
            self.ally_labels.append(lbl)

        # Equipe Inimiga
        enemy_frame = tk.LabelFrame(right, text="Equipe Inimiga", bg=self.bg_medium,
                                     fg=self.danger, font=("Arial", 10, "bold"))
        enemy_frame.pack(fill=tk.X, pady=(0, 5))

        self.enemy_labels = []
        for i in range(5):
            lbl = tk.Label(enemy_frame, text="---", font=("Consolas", 9),
                           bg=self.bg_medium, fg=self.text, anchor=tk.W, padx=10)
            lbl.pack(fill=tk.X)
            self.enemy_labels.append(lbl)

        # Insights de correlacao
        insight_frame = tk.LabelFrame(right, text="Insights", bg=self.bg_medium,
                                       fg=self.accent, font=("Arial", 10, "bold"))
        insight_frame.pack(fill=tk.BOTH, expand=True)

        self.insights_text = tk.Text(
            insight_frame, bg=self.bg_light, fg=self.text, font=("Consolas", 9),
            wrap=tk.WORD, state=tk.DISABLED, highlightthickness=0, height=6
        )
        self.insights_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.insights_text.tag_configure("WARN",  foreground=self.danger)
        self.insights_text.tag_configure("OK",   foreground=self.success)
        self.insights_text.tag_configure("INFO", foreground=self.accent)

    # ===================================================================
    #  TAB 3: POS-JOGO
    # ===================================================================

    def _create_postgame_tab(self):
        """Cria conteudo da aba Pos-Jogo"""
        main = tk.Frame(self.tab_postgame, bg=self.bg_dark)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Barra de busca
        search_frame = tk.Frame(main, bg=self.bg_medium)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(search_frame, text="Riot ID:", font=("Arial", 10),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT, padx=(15, 5), pady=10)

        self.game_name_entry = tk.Entry(search_frame, font=("Arial", 11),
                                         bg=self.bg_light, fg=self.text,
                                         insertbackground=self.text, width=18)
        self.game_name_entry.pack(side=tk.LEFT, padx=2, pady=10)
        self.game_name_entry.insert(0, self.user_config.get("game_name", ""))

        tk.Label(search_frame, text="#", font=("Arial", 11, "bold"),
                 bg=self.bg_medium, fg=self.text_dim).pack(side=tk.LEFT, padx=2)

        self.tag_entry = tk.Entry(search_frame, font=("Arial", 11),
                                   bg=self.bg_light, fg=self.text,
                                   insertbackground=self.text, width=6)
        self.tag_entry.pack(side=tk.LEFT, padx=2, pady=10)
        self.tag_entry.insert(0, self.user_config.get("tag_line", "BR1"))

        self.search_btn = tk.Button(
            search_frame, text="Buscar Partidas", command=self._search_matches,
            font=("Arial", 10, "bold"), bg=self.accent, fg=self.text,
            activebackground=self.success, cursor="hand2", bd=0, padx=15, pady=5
        )
        self.search_btn.pack(side=tk.LEFT, padx=15, pady=10)

        self.search_status_label = tk.Label(
            search_frame, text="", font=("Arial", 9),
            bg=self.bg_medium, fg=self.text_dim
        )
        self.search_status_label.pack(side=tk.LEFT, padx=5)

        # Conteudo - 2 colunas
        content = tk.Frame(main, bg=self.bg_dark)
        content.pack(fill=tk.BOTH, expand=True)

        # Esquerda - Lista de partidas
        left = tk.LabelFrame(content, text="Ultimas Partidas", bg=self.bg_medium,
                              fg=self.text, font=("Arial", 10, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5), pady=0)

        self.match_listbox = tk.Listbox(
            left, bg=self.bg_light, fg=self.text, font=("Consolas", 10),
            selectbackground=self.accent, selectforeground=self.text,
            highlightthickness=0, width=40, height=15
        )
        self.match_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Botoes de analise
        btn_frame = tk.Frame(left, bg=self.bg_medium)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.proximity_btn = tk.Button(
            btn_frame, text="Analisar Proximidade", command=self._analyze_proximity,
            font=("Arial", 10, "bold"), bg="#7b2cbf", fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=6
        )
        self.proximity_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.reaction_btn = tk.Button(
            btn_frame, text="Analisar Reacao", command=self._analyze_reaction,
            font=("Arial", 10, "bold"), bg="#e85d04", fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=6
        )
        self.reaction_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 4))

        self.map_btn = tk.Button(
            btn_frame, text="Mapa Lvl 1", command=self._show_map_lvl1,
            font=("Arial", 10, "bold"), bg="#2d6a4f", fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=6
        )
        self.map_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 4))

        self.pathing_btn = tk.Button(
            btn_frame, text="Pathing", command=self._show_pathing,
            font=("Arial", 10, "bold"), bg="#9b2226", fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=6
        )
        self.pathing_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # Segunda linha de botoes
        btn_frame2 = tk.Frame(left, bg=self.bg_medium)
        btn_frame2.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.replay_btn = tk.Button(
            btn_frame2, text="\u25b6 Replay da Partida", command=self._show_replay,
            font=("Arial", 10, "bold"), bg="#1a759f", fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=6
        )
        self.replay_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        self.dashboard_btn = tk.Button(
            btn_frame2, text="\U0001f4ca Dashboard", command=self._show_dashboard,
            font=("Arial", 10, "bold"), bg="#1a5f3f", fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=6
        )
        self.dashboard_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Direita - Resultados
        right = tk.LabelFrame(content, text="Resultados da Analise", bg=self.bg_medium,
                               fg=self.text, font=("Arial", 10, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.results_text = tk.Text(
            right, bg=self.bg_light, fg=self.text, font=("Consolas", 10),
            wrap=tk.WORD, state=tk.DISABLED, highlightthickness=0
        )
        scrollbar = tk.Scrollbar(right, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=8)
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)

        # Tags de cor para resultados
        self.results_text.tag_configure("HEADER", foreground=self.accent, font=("Consolas", 11, "bold"))
        self.results_text.tag_configure("GOOD", foreground=self.success)
        self.results_text.tag_configure("BAD", foreground=self.danger)
        self.results_text.tag_configure("WARN", foreground=self.warning)
        self.results_text.tag_configure("DIM", foreground=self.text_dim)

        # Armazena match IDs para selecao
        self._match_ids = []
        self._match_data_cache = {}

    # ===================================================================
    #  TAB 5: TIME (paiN Gaming roster)
    # ===================================================================

    def _create_team_tab(self):
        """Cria a aba de gerenciamento do roster (paiN Gaming)."""
        from riot_api.team_viewer import TeamViewer
        team_frame = TeamViewer(
            self.tab_team,
            match_api     = self.match_api,
            map_visualizer = self.map_visualizer,
            root          = self.root,
            scrim_server  = self.scrim_server,
        )
        team_frame.pack(fill=tk.BOTH, expand=True)

    # ===================================================================
    #  TAB 4: CONFIG
    # ===================================================================

    def _create_config_tab(self):
        """Cria conteudo da aba Config"""
        main = tk.Frame(self.tab_config, bg=self.bg_dark)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # API Key
        api_frame = tk.LabelFrame(main, text="Configuracao da API Riot",
                                   bg=self.bg_medium, fg=self.text,
                                   font=("Arial", 11, "bold"))
        api_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        row1 = tk.Frame(api_frame, bg=self.bg_medium)
        row1.pack(fill=tk.X, padx=15, pady=(10, 5))

        tk.Label(row1, text="API Key:", font=("Arial", 10), bg=self.bg_medium,
                 fg=self.text).pack(side=tk.LEFT)

        self.api_key_entry = tk.Entry(row1, font=("Arial", 10), bg=self.bg_light,
                                       fg=self.text, insertbackground=self.text,
                                       show="*", width=45)
        self.api_key_entry.pack(side=tk.LEFT, padx=10)
        self.api_key_entry.insert(0, self.user_config.get("riot_api_key", ""))

        self.test_api_btn = tk.Button(
            row1, text="Testar Conexao", command=self._test_api_connection,
            font=("Arial", 9, "bold"), bg=self.accent, fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=3
        )
        self.test_api_btn.pack(side=tk.LEFT, padx=5)

        self.api_status_label = tk.Label(
            api_frame, text="", font=("Arial", 9),
            bg=self.bg_medium, fg=self.text_dim
        )
        self.api_status_label.pack(padx=15, pady=(0, 10))

        # Conta do jogador
        account_frame = tk.LabelFrame(main, text="Conta do Jogador",
                                       bg=self.bg_medium, fg=self.text,
                                       font=("Arial", 11, "bold"))
        account_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        row2 = tk.Frame(account_frame, bg=self.bg_medium)
        row2.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(row2, text="Game Name:", font=("Arial", 10), bg=self.bg_medium,
                 fg=self.text).pack(side=tk.LEFT)
        self.cfg_game_name = tk.Entry(row2, font=("Arial", 10), bg=self.bg_light,
                                       fg=self.text, insertbackground=self.text, width=18)
        self.cfg_game_name.pack(side=tk.LEFT, padx=5)
        self.cfg_game_name.insert(0, self.user_config.get("game_name", ""))

        tk.Label(row2, text="#", font=("Arial", 10, "bold"), bg=self.bg_medium,
                 fg=self.text_dim).pack(side=tk.LEFT, padx=3)
        self.cfg_tag_line = tk.Entry(row2, font=("Arial", 10), bg=self.bg_light,
                                      fg=self.text, insertbackground=self.text, width=6)
        self.cfg_tag_line.pack(side=tk.LEFT, padx=5)
        self.cfg_tag_line.insert(0, self.user_config.get("tag_line", "BR1"))

        tk.Label(row2, text="Regiao: BR1", font=("Arial", 10), bg=self.bg_medium,
                 fg=self.text_dim).pack(side=tk.LEFT, padx=15)

        # Configuracoes de rastreamento
        tracking_frame = tk.LabelFrame(main, text="Configuracoes de Rastreamento",
                                        bg=self.bg_medium, fg=self.text,
                                        font=("Arial", 11, "bold"))
        tracking_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        row3 = tk.Frame(tracking_frame, bg=self.bg_medium)
        row3.pack(fill=tk.X, padx=15, pady=10)

        prox = self.user_config.get("proximity", {})

        tk.Label(row3, text="Distancia de Gank:", font=("Arial", 10),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT)
        self.cfg_gank_dist = tk.Entry(row3, font=("Arial", 10), bg=self.bg_light,
                                       fg=self.text, insertbackground=self.text, width=6)
        self.cfg_gank_dist.pack(side=tk.LEFT, padx=5)
        self.cfg_gank_dist.insert(0, str(prox.get("gank_distance", 2000)))
        tk.Label(row3, text="unidades", font=("Arial", 9), bg=self.bg_medium,
                 fg=self.text_dim).pack(side=tk.LEFT, padx=(2, 15))

        tk.Label(row3, text="Poll Interval:", font=("Arial", 10),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT)
        self.cfg_poll_interval = tk.Entry(row3, font=("Arial", 10), bg=self.bg_light,
                                           fg=self.text, insertbackground=self.text, width=5)
        self.cfg_poll_interval.pack(side=tk.LEFT, padx=5)
        self.cfg_poll_interval.insert(0, str(prox.get("poll_interval", 0.5)))
        tk.Label(row3, text="seg", font=("Arial", 9), bg=self.bg_medium,
                 fg=self.text_dim).pack(side=tk.LEFT, padx=2)

        # Auto-start riot tracking
        self.cfg_auto_riot = tk.BooleanVar(value=self.user_config.get("auto_start_riot_tracking", False))
        tk.Checkbutton(
            tracking_frame, text="Iniciar rastreamento Riot automaticamente com o jogo",
            variable=self.cfg_auto_riot, font=("Arial", 10),
            bg=self.bg_medium, fg=self.text, selectcolor=self.bg_light,
            activebackground=self.bg_medium, activeforeground=self.text
        ).pack(padx=15, pady=(0, 10))

        # ── Servidor de Scrims ───────────────────────────────────────────
        scrim_frame = tk.LabelFrame(main, text="Servidor de Scrims (VisionLOLAgent)",
                                    bg=self.bg_medium, fg=self.text,
                                    font=("Arial", 11, "bold"))
        scrim_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        scrim_cfg = self.user_config.get("scrim_server", {})

        row_srv1 = tk.Frame(scrim_frame, bg=self.bg_medium)
        row_srv1.pack(fill=tk.X, padx=15, pady=(10, 4))

        self.cfg_scrim_enabled = tk.BooleanVar(value=scrim_cfg.get("enabled", False))
        tk.Checkbutton(
            row_srv1,
            text="Ativar servidor embutido — permite receber capturas dos agentes",
            variable=self.cfg_scrim_enabled,
            font=("Arial", 10),
            bg=self.bg_medium, fg=self.text,
            selectcolor=self.bg_light,
            activebackground=self.bg_medium, activeforeground=self.text
        ).pack(side=tk.LEFT)

        tk.Label(row_srv1, text="  Porta:", font=("Arial", 10),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT, padx=(12, 0))
        self.cfg_scrim_port = tk.Entry(row_srv1, font=("Arial", 10),
                                       bg=self.bg_light, fg=self.text,
                                       insertbackground=self.text, width=6)
        self.cfg_scrim_port.pack(side=tk.LEFT, padx=4)
        self.cfg_scrim_port.insert(0, str(scrim_cfg.get("port", 7654)))

        row_srv2 = tk.Frame(scrim_frame, bg=self.bg_medium)
        row_srv2.pack(fill=tk.X, padx=15, pady=(0, 4))

        tk.Label(row_srv2, text="Token:", font=("Arial", 10),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT)
        self._scrim_token_var = tk.StringVar(value=scrim_cfg.get("token", ""))
        tk.Entry(row_srv2, textvariable=self._scrim_token_var,
                 font=("Arial", 9), bg=self.bg_light, fg=self.text_dim,
                 state="readonly", width=36,
                 readonlybackground=self.bg_light).pack(side=tk.LEFT, padx=5)

        tk.Button(
            row_srv2, text="Regenerar",
            command=self._regenerate_scrim_token,
            font=("Arial", 9), bg=self.bg_light, fg=self.text,
            cursor="hand2", bd=0, padx=8, pady=2
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            row_srv2, text="Copiar Config Agente",
            command=self._copy_agent_config_from_settings,
            font=("Arial", 9), bg=self.accent, fg=self.text,
            cursor="hand2", bd=0, padx=8, pady=2
        ).pack(side=tk.LEFT)

        import socket as _socket
        try:
            _ip = _socket.gethostbyname(_socket.gethostname())
        except Exception:
            _ip = "127.0.0.1"
        _port = scrim_cfg.get("port", 7654)
        self._scrim_url_lbl = tk.Label(
            scrim_frame,
            text=f"URL Local: http://{_ip}:{_port}",
            font=("Arial", 9), bg=self.bg_medium, fg=self.text_dim
        )
        self._scrim_url_lbl.pack(padx=15, pady=(0, 10), anchor="w")

        # ── Discord Webhook ──────────────────────────────────────────────
        discord_frame = tk.LabelFrame(main, text="Integracoes — Discord",
                                      bg=self.bg_medium, fg=self.text,
                                      font=("Arial", 11, "bold"))
        discord_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        row_dc1 = tk.Frame(discord_frame, bg=self.bg_medium)
        row_dc1.pack(fill=tk.X, padx=15, pady=(10, 4))

        tk.Label(row_dc1, text="Webhook URL:", font=("Arial", 10),
                 bg=self.bg_medium, fg=self.text).pack(side=tk.LEFT)

        self.cfg_discord_webhook = tk.Entry(row_dc1, font=("Arial", 9),
                                            bg=self.bg_light, fg=self.text,
                                            insertbackground=self.text, width=48)
        self.cfg_discord_webhook.pack(side=tk.LEFT, padx=8)
        self.cfg_discord_webhook.insert(0, self.user_config.get("discord_webhook", ""))

        tk.Button(
            row_dc1, text="Testar",
            command=self._test_discord_webhook,
            font=("Arial", 9), bg=self.accent, fg=self.text,
            cursor="hand2", bd=0, padx=10, pady=2
        ).pack(side=tk.LEFT)

        tk.Label(
            discord_frame,
            text="ℹ  Canal do Discord → Editar Canal → Integrações → Webhooks → Copiar URL",
            font=("Arial", 8), bg=self.bg_medium, fg=self.text_dim
        ).pack(padx=15, pady=(0, 10), anchor="w")

        # Botao salvar
        save_btn = tk.Button(
            main, text="Salvar Configuracoes", command=self._save_config,
            font=("Arial", 12, "bold"), bg=self.success, fg=self.text,
            cursor="hand2", bd=0, padx=20, pady=10
        )
        save_btn.pack(pady=15)

    # ===================================================================
    #  GAME STATUS CHECK (expandido com Live API)
    # ===================================================================

    def check_game_status(self):
        """Verifica status do jogo periodicamente"""
        status = self.detector.get_status()

        if status['running']:
            if status['in_game']:
                live_api = status.get('live_api', False)
                api_text = " | API Live: ON" if live_api else ""
                self.game_status_label.config(
                    text=f"LoL - EM PARTIDA{api_text}",
                    fg=self.success
                )

                # Auto-mode: inicia monitoramento de camera
                if self.auto_mode_var.get() and not self.is_monitoring:
                    self.start_monitoring()

                # Auto-mode Riot: inicia rastreamento de eventos
                if live_api and self.cfg_auto_riot.get() and not self.is_live_tracking:
                    self._start_live_tracking()

            else:
                self.game_status_label.config(text="LoL - Menu/Lobby", fg=self.warning)

                if self.auto_mode_var.get() and self.is_monitoring:
                    self.stop_monitoring()

                if self.is_live_tracking:
                    self._stop_live_tracking()
        else:
            self.game_status_label.config(text="LoL nao esta rodando", fg=self.danger)

            if self.is_live_tracking:
                self._stop_live_tracking()

        self.root.after(2000, self.check_game_status)

    # ===================================================================
    #  MONITORING (camera/atencao - funcionalidade existente)
    # ===================================================================

    def toggle_auto_mode(self):
        if self.auto_mode_var.get():
            status = self.detector.get_status()
            if status.get('running') and status.get('in_game') and not self.is_monitoring:
                self.start_monitoring()
        else:
            if self.is_monitoring:
                self.stop_monitoring()

    def toggle_monitoring(self):
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        """Inicia o monitoramento"""
        logger.info("=" * 60)
        logger.info("INICIANDO MONITORAMENTO")
        logger.info("=" * 60)

        if self.is_monitoring:
            return

        try:
            self.player_monitor = PlayerMonitor(auto_start_camera=True, show_debug=False)
            self.player_monitor.is_monitoring = True
            self.player_monitor.start_time = time.time()
            self.session_start_time = time.time()
            self.player_monitor.start_input_monitoring()

            # Reset correlator para nova sessao
            self.data_correlator.reset()

            self.is_monitoring = True
            self.start_stop_btn.config(text="PARAR", bg=self.danger)
            self.camera_status_label.config(text="Camera: ATIVA", fg=self.success)
            self.metric_status.config(text="ATIVO", fg=self.success)

            self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitor_thread.start()

            logger.info("MONITORAMENTO INICIADO COM SUCESSO!")

        except Exception as e:
            logger.exception(f"Erro ao iniciar monitoramento: {e}")
            messagebox.showerror("Erro", f"Erro ao iniciar monitoramento:\n{e}")
            self.stop_monitoring()

    def stop_monitoring(self):
        """Para o monitoramento"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False

        if self.player_monitor:
            self.player_monitor.is_monitoring = False
            self.player_monitor.close_camera()
            self.player_monitor = None

        self.start_stop_btn.config(text="INICIAR", bg=self.success)
        self.camera_status_label.config(text="Camera: PARADA", fg=self.warning)
        self.metric_status.config(text="Parado", fg=self.warning)
        self.session_start_time = None

    def monitoring_loop(self):
        """Loop principal de monitoramento (roda em thread separada)"""
        frame_count = 0
        error_count = 0

        while self.is_monitoring and self.player_monitor:
            try:
                ret, frame = self.player_monitor.cap.read()

                if not ret:
                    error_count += 1
                    if error_count > 30:
                        break
                    continue

                error_count = 0
                frame_count += 1

                attention_data, display_frame = self.player_monitor.analyze_attention(frame)
                input_data = self.player_monitor.analyze_inputs()

                self.current_frame = display_frame

                # Loga atencao no correlator (se rastreamento ao vivo ativo)
                if self.is_live_tracking:
                    summary = self.proximity_tracker.get_live_summary()
                    game_time = summary.get("game_time_raw", 0)
                    if game_time:
                        self.data_correlator.log_attention_state(game_time, attention_data)

                self.root.after(0, self.update_metrics, attention_data, input_data)

                time.sleep(0.03)

            except Exception as e:
                logger.error(f"Erro no loop de monitoramento (frame #{frame_count}): {e}")
                break

    def update_metrics(self, attention_data, input_data):
        """Atualiza as metricas na tela"""
        try:
            if attention_data['is_distracted']:
                if self.player_monitor and self.player_monitor.distraction_frames > 15:
                    self.metric_status.config(text="MUITO DISTRAIDO", fg=self.danger)
                else:
                    self.metric_status.config(text="DISTRAIDO", fg=self.warning)
            else:
                self.metric_status.config(text="FOCADO", fg=self.success)

            if attention_data['gaze_direction']:
                self.metric_direction.config(text=attention_data['gaze_direction'])

            if self.player_monitor:
                self.metric_distractions.config(text=str(len(self.player_monitor.distraction_events)))

            self.metric_apm.config(text=f"{input_data['apm']:.0f}")

            if self.session_start_time:
                elapsed = int(time.time() - self.session_start_time)
                self.metric_time.config(text=f"{elapsed // 60:02d}:{elapsed % 60:02d}")

            conf = int(attention_data['confidence'] * 100)
            self.metric_confidence.config(text=f"{conf}%")

        except Exception as e:
            logger.debug(f"update_metrics: {e}")

    def update_camera_preview(self):
        """Atualiza o preview da camera"""
        if self.current_frame is not None:
            try:
                frame = cv2.resize(self.current_frame, (480, 360))
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                self.camera_canvas.imgtk = imgtk
            except Exception as e:
                logger.debug(f"update_camera_preview: {e}")

        self.root.after(33, self.update_camera_preview)

    # ===================================================================
    #  LIVE TRACKING (Riot Live Client API)
    # ===================================================================

    def _start_live_tracking(self):
        """Inicia rastreamento de eventos do jogo ao vivo"""
        if self.is_live_tracking:
            return

        self.is_live_tracking = True
        active_name = self.live_client.get_active_player_name()
        self.proximity_tracker.start_live_tracking(active_name)

        self.analytics_status_label.config(text="RASTREANDO AO VIVO", fg=self.success)
        self._append_event_log("[SISTEMA] Rastreamento ao vivo iniciado\n", "INFO")

        # Inicia atualizacao periodica do painel de analytics
        self._update_analytics_panel()

        logger.info("Rastreamento ao vivo iniciado!")

    def _stop_live_tracking(self):
        """Para rastreamento ao vivo"""
        if not self.is_live_tracking:
            return

        self.is_live_tracking = False
        self.proximity_tracker.stop_live_tracking()

        self.analytics_status_label.config(text="Rastreamento parado", fg=self.warning)
        self._append_event_log("[SISTEMA] Rastreamento ao vivo parado\n", "INFO")

        # Gera insights finais
        correlations = self.data_correlator.correlate()
        insights = self.data_correlator.get_insights()
        self._display_insights(insights)

        logger.info("Rastreamento ao vivo parado")

    def _on_game_event(self, event):
        """Callback chamado pelo ProximityTracker quando detecta evento"""
        # Registra no correlator
        self.data_correlator.log_game_event(event)

        # Atualiza GUI na thread principal
        self.root.after(0, self._display_game_event, event)

    def _display_game_event(self, event):
        """Exibe evento do jogo no log de analytics"""
        event_type = event.get("type", "")
        game_time = event.get("game_time", 0)
        minutes = int(game_time) // 60
        seconds = int(game_time) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        if event_type == "KILL":
            msg = f"[{time_str}] KILL: {event['champion']} ({event['player']}) - {event.get('new_kills')} kills\n"
        elif event_type == "DEATH":
            msg = f"[{time_str}] MORTE: {event['champion']} ({event['player']}) morreu [{event.get('position', '')}]\n"
        elif event_type == "ASSIST":
            msg = f"[{time_str}] ASSIST: {event['champion']} ({event['player']})\n"
        elif event_type == "LEVEL_UP":
            lvl = event.get('level', 0)
            ult = " [ULT UPGRADE!]" if event.get('is_ult_upgrade') else ""
            msg = f"[{time_str}] LEVEL UP: {event['champion']} -> Lv{lvl}{ult}\n"
        elif event_type == "RESPAWN":
            msg = f"[{time_str}] RESPAWN: {event['champion']}\n"
        elif event_type == "LIVE_EVENT":
            event_name = event.get("event_name", "")
            details = event.get("details", {})
            if event_name == "ChampionKill":
                killer = details.get("KillerName", "?")
                victim = details.get("VictimName", "?")
                msg = f"[{time_str}] {killer} matou {victim}\n"
            elif event_name in ("GameStart", "MinionsSpawning"):
                msg = f"[{time_str}] {event_name}\n"
            else:
                msg = f"[{time_str}] {event_name}\n"
        else:
            msg = f"[{time_str}] {event_type}: {event.get('champion', '')}\n"

        tag = event_type if event_type in ("KILL", "DEATH", "ASSIST", "LEVEL_UP", "LIVE_EVENT", "RESPAWN") else "INFO"
        self._append_event_log(msg, tag)

    def _append_event_log(self, text, tag="INFO"):
        """Adiciona texto ao log de eventos"""
        self.events_text.config(state=tk.NORMAL)
        self.events_text.insert(tk.END, text, tag)
        self.events_text.see(tk.END)
        self.events_text.config(state=tk.DISABLED)

    def _update_analytics_panel(self):
        """Atualiza painel de analytics periodicamente"""
        if not self.is_live_tracking:
            return

        summary = self.proximity_tracker.get_live_summary()

        # Atualiza tempo do jogo
        self.analytics_time_label.config(text=f"Tempo: {summary.get('game_time', '00:00')}")

        # Atualiza paineis de equipe
        players = summary.get("players", [])
        ally_idx = 0
        enemy_idx = 0

        # Descobre time do jogador ativo
        active_team = self.live_client.get_active_player_team(
            [{"riotId": p["name"], "summonerName": p["name"], "team": p["team"]} for p in players]
        )

        for p in players:
            name_short = p["champion"][:12]
            kda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
            dead_str = " [MORTO]" if p["isDead"] else ""
            text = f"{name_short:12s} Lv{p['level']:2d} {kda:8s}{dead_str}"
            color = self.danger if p["isDead"] else self.text

            if p["team"] == active_team and ally_idx < 5:
                self.ally_labels[ally_idx].config(text=text, fg=color)
                ally_idx += 1
            elif p["team"] != active_team and enemy_idx < 5:
                self.enemy_labels[enemy_idx].config(text=text, fg=color)
                enemy_idx += 1

        # Atualiza insights em tempo real (a cada 30s para nao sobrecarregar)
        if not hasattr(self, "_last_insight_update"):
            self._last_insight_update = 0
        now = time.time()
        if now - self._last_insight_update >= 30:
            self._last_insight_update = now
            self.data_correlator.correlate()
            self._display_insights(self.data_correlator.get_insights())

        # Proximo update em 1 segundo
        self.root.after(1000, self._update_analytics_panel)

    def _display_insights(self, insights):
        """Exibe insights no painel"""
        self.insights_text.config(state=tk.NORMAL)
        self.insights_text.delete("1.0", tk.END)

        if not insights:
            self.insights_text.insert(tk.END, "Sem insights para esta sessao.\n", "OK")
        else:
            _ICONS = {"WARNING": "! ", "POSITIVE": "+ ", "INFO": "· "}
            _TAGS  = {"WARNING": "WARN", "POSITIVE": "OK", "INFO": "INFO"}
            for insight in insights:
                itype = insight.get("type", "INFO")
                tag   = _TAGS.get(itype, "INFO")
                icon  = _ICONS.get(itype, "· ")
                self.insights_text.insert(tk.END, f"{icon}{insight['text']}\n", tag)

        self.insights_text.config(state=tk.DISABLED)

    # ===================================================================
    #  POST-GAME ANALYSIS
    # ===================================================================

    def _search_matches(self):
        """Busca partidas do jogador"""
        game_name = self.game_name_entry.get().strip()
        tag_line = self.tag_entry.get().strip()

        if not game_name or not tag_line:
            messagebox.showwarning("Aviso", "Preencha o Riot ID (Nome e Tag)")
            return

        self.search_status_label.config(text="Buscando...", fg=self.warning)
        self.search_btn.config(state=tk.DISABLED)

        # Roda em thread separada
        threading.Thread(target=self._search_matches_thread,
                        args=(game_name, tag_line), daemon=True).start()

    def _search_matches_thread(self, game_name, tag_line):
        """Thread de busca de partidas"""
        try:
            # Obtem PUUID
            puuid = self.match_api.get_puuid(game_name, tag_line)
            if not puuid:
                self.root.after(0, self._search_error, "Riot ID nao encontrado!")
                return

            self._cached_puuid = puuid

            # Busca partidas
            match_ids = self.match_api.get_match_ids(puuid, count=10)
            if not match_ids:
                self.root.after(0, self._search_error, "Nenhuma partida encontrada")
                return

            # Busca resumo de cada partida
            summaries = []
            for mid in match_ids:
                data = self.match_api.get_match_data(mid)
                if data:
                    self._match_data_cache[mid] = data
                    summary = self.match_api.get_match_summary(data, puuid)
                    summaries.append((mid, summary))

            self.root.after(0, self._display_matches, match_ids, summaries)

        except Exception as e:
            self.root.after(0, self._search_error, f"Erro: {e}")

    def _display_matches(self, match_ids, summaries):
        """Exibe lista de partidas na GUI"""
        self._match_ids = match_ids
        self.match_listbox.delete(0, tk.END)

        for mid, summary in summaries:
            if summary:
                win = "V" if summary.get("win") else "D"
                champ = summary.get("champion", "?")
                kda = summary.get("kda", "0/0/0")
                dur = summary.get("duration", "?")
                pos = summary.get("position", "?")
                line = f"[{win}] {champ:12s} {kda:8s} {dur:5s} {pos}"
                self.match_listbox.insert(tk.END, line)

                # Cor baseada em vitoria/derrota
                idx = self.match_listbox.size() - 1
                if summary.get("win"):
                    self.match_listbox.itemconfig(idx, fg=self.success)
                else:
                    self.match_listbox.itemconfig(idx, fg=self.danger)
            else:
                self.match_listbox.insert(tk.END, mid)

        self.search_status_label.config(text=f"{len(summaries)} partidas encontradas", fg=self.success)
        self.search_btn.config(state=tk.NORMAL)

    def _search_error(self, msg):
        """Exibe erro de busca"""
        self.search_status_label.config(text=msg, fg=self.danger)
        self.search_btn.config(state=tk.NORMAL)

    def _get_selected_match_id(self):
        """Retorna o match ID selecionado na listbox"""
        selection = self.match_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione uma partida na lista!")
            return None
        idx = selection[0]
        if idx < len(self._match_ids):
            return self._match_ids[idx]
        return None

    def _analyze_proximity(self):
        """Inicia analise de proximidade da partida selecionada"""
        match_id = self._get_selected_match_id()
        if not match_id or not self._cached_puuid:
            return

        self._set_results("Analisando proximidade...\nIsso pode levar alguns segundos.\n")
        self.proximity_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._proximity_thread,
                        args=(match_id, self._cached_puuid), daemon=True).start()

    def _proximity_thread(self, match_id, puuid):
        """Thread de analise de proximidade"""
        try:
            report = self.proximity_tracker.analyze_match_proximity(match_id, puuid)
            if report:
                self.root.after(0, self._display_proximity_report, report)
            else:
                self.root.after(0, self._set_results, "Erro: nao foi possivel analisar esta partida.\n")
        except Exception as e:
            self.root.after(0, self._set_results, f"Erro na analise: {e}\n")
        finally:
            self.root.after(0, lambda: self.proximity_btn.config(state=tk.NORMAL))

    def _display_proximity_report(self, report):
        """Exibe relatorio de proximidade"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)

        # Header
        target = report["target"]
        self.results_text.insert(tk.END, "RELATORIO DE PROXIMIDADE\n", "HEADER")
        self.results_text.insert(tk.END, "=" * 45 + "\n\n")

        self.results_text.insert(tk.END, f"Jogador: {target['champion']} ({target['position']})\n")

        # Jungler inimigo
        ej = report.get("enemy_jungler")
        if ej:
            self.results_text.insert(tk.END, f"Jungler Inimigo: {ej['champion']}\n\n")
        else:
            self.results_text.insert(tk.END, "Jungler Inimigo: nao identificado\n\n")

        # Ganks detectados
        ganks = report.get("gank_events", [])
        self.results_text.insert(tk.END, f"Ganks Detectados: {len(ganks)}\n", "HEADER")
        self.results_text.insert(tk.END, "-" * 45 + "\n")

        if ganks:
            for g in ganks:
                kill_str = " -> KILL!" if g["resulted_in_kill"] else ""
                died_str = " [VOCE MORREU]" if g.get("target_died") else ""
                line = f"  Min {g['minute']:2d}: {g['jungler_champion']} proximo (dist: {g['distance']:.0f}){kill_str}{died_str}\n"

                tag = "BAD" if g.get("target_died") else ("WARN" if g["resulted_in_kill"] else None)
                self.results_text.insert(tk.END, line, tag)
        else:
            self.results_text.insert(tk.END, "  Nenhum gank detectado do jungler inimigo\n", "GOOD")

        # Resumo por lane
        self.results_text.insert(tk.END, f"\nPressao por Lane:\n", "HEADER")
        self.results_text.insert(tk.END, "-" * 45 + "\n")

        lane_summary = report.get("lane_summary", {})
        for pos, data in lane_summary.items():
            bar_len = int(data["pressure_pct"] / 5)
            bar = "#" * bar_len + "." * (20 - bar_len)
            line = f"  {pos:8s} ({data['champion']:12s}): [{bar}] {data['pressure_pct']}%\n"
            tag = "BAD" if data["pressure_pct"] > 30 else None
            self.results_text.insert(tk.END, line, tag)

        self.results_text.insert(tk.END, "\n" + "=" * 45 + "\n")
        self.results_text.config(state=tk.DISABLED)

    def _analyze_reaction(self):
        """Inicia analise de reacao da partida selecionada"""
        match_id = self._get_selected_match_id()
        if not match_id or not self._cached_puuid:
            return

        self._set_results("Analisando reacao...\nIsso pode levar alguns segundos.\n")
        self.reaction_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._reaction_thread,
                        args=(match_id, self._cached_puuid), daemon=True).start()

    def _reaction_thread(self, match_id, puuid):
        """Thread de analise de reacao"""
        try:
            report = self.reaction_analyzer.analyze_match_reactions(match_id, puuid)
            if report:
                formatted = self.reaction_analyzer.format_report(report)
                self.root.after(0, self._set_results, formatted)
            else:
                self.root.after(0, self._set_results, "Erro: nao foi possivel analisar esta partida.\n")
        except Exception as e:
            self.root.after(0, self._set_results, f"Erro na analise: {e}\n")
        finally:
            self.root.after(0, lambda: self.reaction_btn.config(state=tk.NORMAL))

    def _set_results(self, text):
        """Define texto na area de resultados"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.config(state=tk.DISABLED)

    # ===================================================================
    #  MAP VISUALIZATION
    # ===================================================================

    def _show_map_lvl1(self):
        """Renderiza mapa de posicionamento level 1 da partida selecionada"""
        match_id = self._get_selected_match_id()
        if not match_id or not self._cached_puuid:
            return

        self._set_results("Gerando mapa de posicionamento...\nBaixando assets do Data Dragon...\n")
        self.map_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._map_thread,
                        args=(match_id, self._cached_puuid), daemon=True).start()

    def _map_thread(self, match_id, puuid):
        """Thread de geracao do mapa"""
        try:
            img = self.map_visualizer.render_early_game(match_id, puuid)
            if img:
                self.root.after(0, self._display_map_window, img, "Posicionamento Level 1")
                self.root.after(0, self._set_results, "Mapa gerado! Aberto em nova janela.\n")
            else:
                self.root.after(0, self._set_results, "Erro: nao foi possivel gerar o mapa.\n")
        except Exception as e:
            self.root.after(0, self._set_results, f"Erro ao gerar mapa: {e}\n")
        finally:
            self.root.after(0, lambda: self.map_btn.config(state=tk.NORMAL))

    def _display_map_window(self, pil_image, title="Mapa"):
        """Abre nova janela com o mapa renderizado"""
        map_win = tk.Toplevel(self.root)
        map_win.title(f"VisionLOL - {title}")
        map_win.configure(bg=self.bg_dark)
        map_win.resizable(True, True)

        # Ajusta tamanho da janela ao mapa
        w, h = pil_image.size
        map_win.geometry(f"{w + 20}x{h + 70}")

        # Titulo
        tk.Label(map_win, text=title, font=("Arial", 14, "bold"),
                 bg=self.bg_dark, fg=self.accent).pack(pady=(10, 5))

        # Canvas para a imagem
        canvas = tk.Canvas(map_win, width=w, height=h, bg=self.bg_dark,
                          highlightthickness=0)
        canvas.pack(padx=10, pady=(0, 5))

        # Converte PIL -> ImageTk
        imgtk = ImageTk.PhotoImage(pil_image)
        canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        canvas.imgtk = imgtk  # Mantem referencia

        # Botao salvar
        def save_map():
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")],
                title="Salvar mapa",
                initialfile=f"mapa_lvl1_{title.replace(' ', '_')}.png"
            )
            if path:
                pil_image.save(path)
                messagebox.showinfo("Salvo", f"Mapa salvo em:\n{path}")

        tk.Button(map_win, text="Salvar Imagem", command=save_map,
                  font=("Arial", 10), bg=self.accent, fg=self.text,
                  cursor="hand2", bd=0, padx=15, pady=5).pack(pady=(0, 10))

    # ===================================================================
    #  PATHING VISUALIZATION (interativa com filtros)
    # ===================================================================

    def _show_pathing(self):
        """Inicia geracao do pathing da partida selecionada"""
        match_id = self._get_selected_match_id()
        if not match_id or not self._cached_puuid:
            return

        self._set_results("Gerando pathing...\nExtraindo dados da timeline...\n")
        self.pathing_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._pathing_thread,
                        args=(match_id, self._cached_puuid), daemon=True).start()

    def _pathing_thread(self, match_id, puuid):
        """Thread de extracao de dados de pathing"""
        try:
            match_data = self._match_data_cache.get(match_id)
            if not match_data:
                match_data = self.match_api.get_match_data(match_id)
            timeline = self.match_api.get_match_timeline(match_id)

            if not match_data or not timeline:
                self.root.after(0, self._set_results, "Erro: dados da partida indisponiveis.\n")
                return

            pathing_data = self.pathing_visualizer.extract_pathing_data(
                timeline, match_data, puuid
            )
            self.root.after(0, self._open_pathing_window, pathing_data)
            self.root.after(0, self._set_results, "Pathing aberto em nova janela!\n")

        except Exception as e:
            self.root.after(0, self._set_results, f"Erro no pathing: {e}\n")
        finally:
            self.root.after(0, lambda: self.pathing_btn.config(state=tk.NORMAL))

    def _open_pathing_window(self, pathing_data):
        """Abre janela interativa de pathing com filtros"""
        win = tk.Toplevel(self.root)
        win.title("VisionLOL - Pathing Analysis")
        win.configure(bg=self.bg_dark)
        win.geometry("1100x860")
        win.resizable(True, True)

        # Estado dos filtros
        filter_vars = {
            "my_path": tk.BooleanVar(value=True),
            "enemy_path": tk.BooleanVar(value=True),
            "my_wards": tk.BooleanVar(value=True),
            "enemy_wards": tk.BooleanVar(value=True),
            "my_kills": tk.BooleanVar(value=True),
            "my_deaths": tk.BooleanVar(value=True),
            "objectives": tk.BooleanVar(value=True),
            "buildings": tk.BooleanVar(value=False),
        }
        time_var = tk.IntVar(value=pathing_data.game_duration_min)

        # Referencia para a imagem atual (para salvar)
        current_image = [None]

        # Layout principal
        main = tk.Frame(win, bg=self.bg_dark)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Esquerda - Canvas do mapa
        canvas = tk.Canvas(main, width=800, height=800, bg=self.bg_light,
                          highlightthickness=0)
        canvas.pack(side=tk.LEFT, padx=(5, 10), pady=5)

        # Direita - Painel de controle
        panel = tk.Frame(main, bg=self.bg_dark, width=260)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)
        panel.pack_propagate(False)

        # --- FILTROS ---
        filter_frame = tk.LabelFrame(panel, text="Filtros", bg=self.bg_medium,
                                      fg=self.text, font=("Arial", 11, "bold"))
        filter_frame.pack(fill=tk.X, pady=(0, 8))

        filter_labels = {
            "my_path": "Meu Pathing",
            "enemy_path": "JG Inimigo",
            "my_wards": "Minhas Wards",
            "enemy_wards": "Wards Inimigas",
            "my_kills": "Minhas Kills",
            "my_deaths": "Minhas Mortes",
            "objectives": "Objetivos (Dragon/Baron)",
            "buildings": "Torres",
        }

        filter_colors = {
            "my_path": "#00b4d8",
            "enemy_path": "#ef476f",
            "my_wards": "#ffd60a",
            "enemy_wards": "#b43232",
            "my_kills": "#06d6a0",
            "my_deaths": "#ef476f",
            "objectives": "#a050dc",
            "buildings": "#e69632",
        }

        for key, label in filter_labels.items():
            row = tk.Frame(filter_frame, bg=self.bg_medium)
            row.pack(fill=tk.X, padx=10, pady=2)

            # Indicador de cor
            color_ind = tk.Canvas(row, width=12, height=12, bg=self.bg_medium,
                                  highlightthickness=0)
            color_ind.pack(side=tk.LEFT, padx=(0, 5))
            color_ind.create_oval(1, 1, 11, 11, fill=filter_colors[key], outline="")

            tk.Checkbutton(
                row, text=label, variable=filter_vars[key],
                font=("Arial", 10), bg=self.bg_medium, fg=self.text,
                selectcolor=self.bg_light, activebackground=self.bg_medium,
                activeforeground=self.text,
                command=lambda: self._render_pathing(
                    pathing_data, filter_vars, time_var, canvas, current_image
                )
            ).pack(side=tk.LEFT)

        # --- TEMPO ---
        time_frame = tk.LabelFrame(panel, text="Tempo", bg=self.bg_medium,
                                    fg=self.text, font=("Arial", 11, "bold"))
        time_frame.pack(fill=tk.X, pady=(0, 8))

        time_label = tk.Label(
            time_frame, text=f"Ate minuto: {pathing_data.game_duration_min}",
            font=("Arial", 10), bg=self.bg_medium, fg=self.text
        )
        time_label.pack(padx=10, pady=(8, 2))

        def on_slider_change(val):
            v = int(float(val))
            time_label.config(text=f"Ate minuto: {v}")
            self._render_pathing(pathing_data, filter_vars, time_var, canvas, current_image)

        time_slider = tk.Scale(
            time_frame, from_=1, to=pathing_data.game_duration_min,
            orient=tk.HORIZONTAL, variable=time_var,
            bg=self.bg_medium, fg=self.text, troughcolor=self.bg_light,
            highlightthickness=0, font=("Arial", 9),
            command=on_slider_change
        )
        time_slider.pack(fill=tk.X, padx=10, pady=(0, 10))

        # --- INFO ---
        info_frame = tk.LabelFrame(panel, text="Info", bg=self.bg_medium,
                                    fg=self.text, font=("Arial", 11, "bold"))
        info_frame.pack(fill=tk.X, pady=(0, 8))

        target = pathing_data.pid_map.get(pathing_data.target_pid, {})
        enemy = pathing_data.pid_map.get(pathing_data.enemy_jungler_pid, {}) if pathing_data.enemy_jungler_pid else {}

        info_lines = [
            f"Voce: {target.get('champion', '?')} ({target.get('position', '?')})",
            f"JG Inimigo: {enemy.get('champion', '?')}",
            f"Duracao: {pathing_data.game_duration_min} min",
            f"Kills totais: {len(pathing_data.kills)}",
            f"Wards colocadas: {len(pathing_data.wards_placed)}",
            f"Objetivos: {len(pathing_data.objectives)}",
        ]

        for line in info_lines:
            tk.Label(info_frame, text=line, font=("Consolas", 9),
                     bg=self.bg_medium, fg=self.text, anchor=tk.W,
                     padx=10).pack(fill=tk.X)

        tk.Label(info_frame, text="", bg=self.bg_medium).pack(pady=3)

        # --- SALVAR ---
        def save_pathing():
            from tkinter import filedialog
            if current_image[0]:
                path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")],
                    title="Salvar pathing",
                    initialfile="pathing_analysis.png"
                )
                if path:
                    current_image[0].save(path)
                    messagebox.showinfo("Salvo", f"Imagem salva em:\n{path}")

        tk.Button(panel, text="Salvar Imagem", command=save_pathing,
                  font=("Arial", 11, "bold"), bg=self.accent, fg=self.text,
                  cursor="hand2", bd=0, padx=15, pady=8).pack(fill=tk.X, padx=10, pady=10)

        # Renderiza imagem inicial
        self._render_pathing(pathing_data, filter_vars, time_var, canvas, current_image)

    def _render_pathing(self, pathing_data, filter_vars, time_var, canvas, current_image):
        """Re-renderiza o pathing com filtros atuais"""
        filters = {k: v.get() for k, v in filter_vars.items()}
        max_minute = time_var.get()

        img = self.pathing_visualizer.render(pathing_data, filters, max_minute)
        if img:
            current_image[0] = img
            imgtk = ImageTk.PhotoImage(img)
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            canvas.imgtk = imgtk

    # ===================================================================
    #  MATCH REPLAY
    # ===================================================================

    def _show_replay(self):
        """Abre o replay animado da partida selecionada"""
        match_id = self._get_selected_match_id()
        if not match_id or not self._cached_puuid:
            return

        self._set_results("Preparando replay...\nBaixando timeline e assets...\n")
        self.replay_btn.config(state=tk.DISABLED)

        threading.Thread(target=self._replay_thread,
                        args=(match_id, self._cached_puuid), daemon=True).start()

    def _replay_thread(self, match_id, puuid):
        """Thread que busca dados e abre o replay viewer"""
        try:
            match_data = self._match_data_cache.get(match_id)
            if not match_data:
                match_data = self.match_api.get_match_data(match_id)
            timeline = self.match_api.get_match_timeline(match_id)

            if not match_data or not timeline:
                self.root.after(0, self._set_results, "Erro: dados da partida indisponiveis.\n")
                return

            from riot_api.replay_engine import ReplayEngine
            engine = ReplayEngine(timeline, match_data, puuid)

            self.root.after(0, self._open_replay_viewer, engine)
            self.root.after(0, self._set_results, "Replay aberto em nova janela!\n")

        except Exception as e:
            self.root.after(0, self._set_results, f"Erro no replay: {e}\n")
        finally:
            self.root.after(0, lambda: self.replay_btn.config(state=tk.NORMAL))

    def _open_replay_viewer(self, engine):
        """Abre a janela do ReplayViewer"""
        from riot_api.replay_viewer import ReplayViewer
        ReplayViewer(self.root, engine, self.map_visualizer)

    # ===================================================================
    #  DASHBOARD
    # ===================================================================

    def _show_dashboard(self):
        """Abre o dashboard de perfil do jogador."""
        if not self._cached_puuid or not self._match_ids:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Busque um jogador antes de abrir o Dashboard!")
            return

        # Reconstrói summaries a partir do cache
        summaries = []
        for mid in self._match_ids:
            data = self._match_data_cache.get(mid)
            if data:
                s = self.match_api.get_match_summary(data, self._cached_puuid)
                summaries.append((mid, s))

        if not summaries:
            return

        from riot_api.dashboard_viewer import DashboardViewer
        DashboardViewer(
            self.root, summaries, self._match_data_cache,
            self.map_visualizer, self.match_api, self._cached_puuid
        )

    # ===================================================================
    #  CONFIG
    # ===================================================================

    def _test_api_connection(self):
        """Testa conexao com a API da Riot"""
        key = self.api_key_entry.get().strip()
        if not key:
            self.api_status_label.config(text="Insira uma API key!", fg=self.danger)
            return

        self.api_status_label.config(text="Testando...", fg=self.warning)
        self.http_client.api_key = key

        def _test():
            ok, msg = self.http_client.test_connection()
            color = self.success if ok else self.danger
            self.root.after(0, lambda: self.api_status_label.config(text=msg, fg=color))

        threading.Thread(target=_test, daemon=True).start()

    def _save_config(self):
        """Salva configuracoes"""
        self.user_config["riot_api_key"] = self.api_key_entry.get().strip()
        self.user_config["game_name"] = self.cfg_game_name.get().strip()
        self.user_config["tag_line"] = self.cfg_tag_line.get().strip()
        self.user_config["auto_start_riot_tracking"] = self.cfg_auto_riot.get()

        try:
            self.user_config["proximity"]["gank_distance"] = int(self.cfg_gank_dist.get().strip())
            self.user_config["proximity"]["poll_interval"] = float(self.cfg_poll_interval.get().strip())
        except ValueError:
            messagebox.showwarning("Aviso", "Gank distance deve ser inteiro e Poll interval deve ser decimal.\nValores anteriores mantidos.")

        # Servidor de scrims
        self.user_config.setdefault("scrim_server", {})
        self.user_config["scrim_server"]["enabled"] = self.cfg_scrim_enabled.get()
        try:
            self.user_config["scrim_server"]["port"] = int(self.cfg_scrim_port.get().strip())
        except ValueError:
            self.user_config["scrim_server"]["port"] = 7654
        self.user_config["scrim_server"]["token"] = self._scrim_token_var.get()

        # Discord webhook
        self.user_config["discord_webhook"] = self.cfg_discord_webhook.get().strip()

        save_config(self.user_config)

        # Atualiza http client com nova key
        self.http_client.api_key = self.user_config["riot_api_key"]

        # Sincroniza com campos do tab pos-jogo
        self.game_name_entry.delete(0, tk.END)
        self.game_name_entry.insert(0, self.user_config["game_name"])
        self.tag_entry.delete(0, tk.END)
        self.tag_entry.insert(0, self.user_config["tag_line"])

        # Propaga mudança do servidor de scrims para a instância em execução
        if hasattr(self, "scrim_server") and self.scrim_server:
            new_enabled = self.user_config["scrim_server"]["enabled"]
            new_token   = self.user_config["scrim_server"]["token"]
            if new_enabled and not self.scrim_server.is_running:
                self.scrim_server.token = new_token
                try:
                    self.scrim_server.start()
                except Exception as e:
                    logger.warning(f"Não foi possível iniciar servidor: {e}")
            elif not new_enabled and self.scrim_server.is_running:
                self.scrim_server.stop()

        # Atualiza label de URL local
        import socket as _socket
        try:
            _ip = _socket.gethostbyname(_socket.gethostname())
        except Exception:
            _ip = "127.0.0.1"
        _port = self.user_config["scrim_server"]["port"]
        if hasattr(self, "_scrim_url_lbl") and self._scrim_url_lbl.winfo_exists():
            self._scrim_url_lbl.config(text=f"URL Local: http://{_ip}:{_port}")

        messagebox.showinfo("Sucesso", "Configuracoes salvas com sucesso!")

    # ===================================================================
    #  CLEANUP
    # ===================================================================

    def _regenerate_scrim_token(self):
        """Gera um novo token UUID para o servidor de scrims."""
        import uuid
        self._scrim_token_var.set(str(uuid.uuid4()))

    def _copy_agent_config_from_settings(self):
        """Copia o JSON de configuração do agente para o clipboard."""
        import socket as _socket, json as _json
        try:
            ip = _socket.gethostbyname(_socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
        try:
            port = int(self.cfg_scrim_port.get().strip())
        except ValueError:
            port = 7654
        token = self._scrim_token_var.get()
        cfg = {
            "server_url": f"http://{ip}:{port}",
            "auth_token": token,
            "player_riot_id": ""
        }
        text = _json.dumps(cfg, indent=2, ensure_ascii=False)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copiado",
                            "Config do agente copiada!\nCole no VisionLOLAgent ao configurar.")

    def _test_discord_webhook(self):
        """Envia um embed de exemplo de resultado de scrim para o webhook Discord."""
        url = self.cfg_discord_webhook.get().strip()
        if not url:
            messagebox.showwarning("Aviso", "Cole a URL do webhook primeiro.")
            return
        import requests as _requests
        from datetime import datetime, timezone as _tz
        def _run():
            try:
                payload = {
                    "embeds": [{
                        "title": "⚔  Scrim vs Team Alpha  *(exemplo)*",
                        "color": 0x58a6ff,
                        "fields": [
                            {"name": "📅 Data",       "value": "2026-03-03",  "inline": True},
                            {"name": "🎮 Partidas",   "value": "3",           "inline": True},
                            {"name": "📊 Resultado",  "value": "**2V / 1D**", "inline": True},
                            {"name": "Kami  [MID]",   "value": "Azir · KDA 4.2 · 67% WR",   "inline": True},
                            {"name": "Kuri88  [ADC]", "value": "Jinx · KDA 6.1 · 100% WR",  "inline": True},
                            {"name": "CarioK  [JG]",  "value": "Vi · KDA 3.8 · 67% WR",     "inline": True},
                            {"name": "Snow  [TOP]",   "value": "Renekton · KDA 2.9 · 33% WR","inline": True},
                            {"name": "Surr  [SUP]",   "value": "Nautilus · KDA 5.0 · 67% WR","inline": True},
                        ],
                        "footer": {"text": "VisionLOL · Este é um resultado de exemplo"},
                        "timestamp": datetime.now(_tz.utc).isoformat(),
                    }]
                }
                r = _requests.post(url, json=payload, timeout=6)
                if r.status_code in (200, 204):
                    self.root.after(0, messagebox.showinfo, "Discord",
                                    "✓ Embed de exemplo enviado!\nVerifique o canal do Discord.")
                else:
                    self.root.after(0, messagebox.showwarning, "Discord",
                                    f"Discord respondeu {r.status_code}.")
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Erro", str(e))
        threading.Thread(target=_run, daemon=True).start()

    def _init_scrim_server(self) -> "ScrimServer | None":
        """Cria e (opcionalmente) inicia o servidor de scrims."""
        import uuid
        cfg = self.user_config.get("scrim_server", {})
        token = cfg.get("token", "")
        if not token:
            token = str(uuid.uuid4())
            self.user_config.setdefault("scrim_server", {})["token"] = token
            save_config(self.user_config)

        server = ScrimServer(
            port=cfg.get("port", 7654),
            token=token,
        )
        if cfg.get("enabled", False):
            try:
                server.start()
            except Exception as e:
                logger.warning(f"Servidor de scrims não iniciado: {e}")
        return server

    def on_closing(self):
        """Chamado ao fechar a janela"""
        self._stop_live_tracking()
        self.stop_monitoring()
        if self.scrim_server and self.scrim_server.is_running:
            self.scrim_server.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = VisionLOLAppIntegrated(root)
    root.mainloop()


if __name__ == "__main__":
    main()
