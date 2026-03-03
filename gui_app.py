# -*- coding: utf-8 -*-
"""
VisionLOL GUI - Interface Gráfica Principal
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os

# Adiciona o diretório .venv ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.venv'))

from game_detector import GameDetector


class VisionLOLApp:
    """Aplicação principal com interface gráfica"""

    def __init__(self, root):
        self.root = root
        self.root.title("VisionLOL - Player Monitor")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Estado da aplicação
        self.is_monitoring = False
        self.monitor_thread = None
        self.detector = GameDetector()
        self.player_monitor = None

        # Configurar estilo
        self.setup_style()

        # Criar interface
        self.create_widgets()

        # Iniciar verificação de status do jogo
        self.check_game_status()

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
        self.text = "#ffffff"

        # Configurar root
        self.root.configure(bg=self.bg_dark)

    def create_widgets(self):
        """Criar todos os widgets da interface"""

        # === HEADER ===
        header = tk.Frame(self.root, bg=self.bg_medium, height=80)
        header.pack(fill=tk.X, padx=10, pady=10)
        header.pack_propagate(False)

        title_label = tk.Label(
            header,
            text="🎮 VisionLOL",
            font=("Arial", 24, "bold"),
            bg=self.bg_medium,
            fg=self.accent
        )
        title_label.pack(side=tk.LEFT, padx=20)

        subtitle_label = tk.Label(
            header,
            text="Player Performance Monitor",
            font=("Arial", 12),
            bg=self.bg_medium,
            fg=self.text
        )
        subtitle_label.pack(side=tk.LEFT)

        # === GAME STATUS ===
        status_frame = tk.LabelFrame(
            self.root,
            text="Status do Jogo",
            bg=self.bg_medium,
            fg=self.text,
            font=("Arial", 12, "bold")
        )
        status_frame.pack(fill=tk.X, padx=10, pady=10)

        self.game_status_label = tk.Label(
            status_frame,
            text="⚪ Verificando...",
            font=("Arial", 14),
            bg=self.bg_medium,
            fg=self.text,
            anchor=tk.W,
            padx=20,
            pady=10
        )
        self.game_status_label.pack(fill=tk.X)

        # === CONTROLES ===
        controls_frame = tk.Frame(self.root, bg=self.bg_dark)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)

        # Botão Start/Stop
        self.start_stop_btn = tk.Button(
            controls_frame,
            text="▶️ INICIAR MONITORAMENTO",
            command=self.toggle_monitoring,
            font=("Arial", 14, "bold"),
            bg=self.success,
            fg=self.text,
            activebackground=self.accent,
            relief=tk.RAISED,
            bd=0,
            padx=20,
            pady=15,
            cursor="hand2"
        )
        self.start_stop_btn.pack(side=tk.LEFT, padx=10)

        # Modo automático
        self.auto_mode_var = tk.BooleanVar(value=False)
        auto_check = tk.Checkbutton(
            controls_frame,
            text="Modo Automático (iniciar com LoL)",
            variable=self.auto_mode_var,
            font=("Arial", 11),
            bg=self.bg_dark,
            fg=self.text,
            selectcolor=self.bg_medium,
            activebackground=self.bg_dark,
            activeforeground=self.text,
            command=self.toggle_auto_mode
        )
        auto_check.pack(side=tk.LEFT, padx=20)

        # === MÉTRICAS ===
        metrics_frame = tk.LabelFrame(
            self.root,
            text="Métricas em Tempo Real",
            bg=self.bg_medium,
            fg=self.text,
            font=("Arial", 12, "bold")
        )
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Grid de métricas
        metrics_grid = tk.Frame(metrics_frame, bg=self.bg_medium)
        metrics_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Configurar grid
        for i in range(2):
            metrics_grid.columnconfigure(i, weight=1)
        for i in range(3):
            metrics_grid.rowconfigure(i, weight=1)

        # Métricas individuais
        self.create_metric_card(metrics_grid, "Status", "⚪ Aguardando", 0, 0, "status")
        self.create_metric_card(metrics_grid, "Direção", "---", 0, 1, "direction")
        self.create_metric_card(metrics_grid, "Distrações", "0", 1, 0, "distractions")
        self.create_metric_card(metrics_grid, "APM", "0", 1, 1, "apm")
        self.create_metric_card(metrics_grid, "Tempo", "00:00", 2, 0, "time")
        self.create_metric_card(metrics_grid, "Confiança", "0%", 2, 1, "confidence")

        # === LOG/CONSOLE ===
        log_frame = tk.LabelFrame(
            self.root,
            text="Log de Eventos",
            bg=self.bg_medium,
            fg=self.text,
            font=("Arial", 11, "bold")
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollbar
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_frame,
            height=8,
            bg=self.bg_light,
            fg=self.text,
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.log_text.yview)

        # Log inicial
        self.log("Sistema iniciado")
        self.log("Aguardando comandos...")

    def create_metric_card(self, parent, title, value, row, col, metric_id):
        """Cria um card de métrica"""
        card = tk.Frame(parent, bg=self.bg_light, relief=tk.RAISED, bd=2)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        title_label = tk.Label(
            card,
            text=title,
            font=("Arial", 10),
            bg=self.bg_light,
            fg="#888888"
        )
        title_label.pack(pady=(10, 5))

        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 18, "bold"),
            bg=self.bg_light,
            fg=self.text
        )
        value_label.pack(pady=(0, 10))

        # Salvar referência
        setattr(self, f"metric_{metric_id}", value_label)

    def log(self, message):
        """Adiciona mensagem ao log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"• {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def check_game_status(self):
        """Verifica status do jogo periodicamente"""
        status = self.detector.get_status()

        if status['running']:
            if status['in_game']:
                self.game_status_label.config(
                    text="🟢 League of Legends - EM PARTIDA",
                    fg=self.success
                )

                # Se modo automático está ativo e não está monitorando
                if self.auto_mode_var.get() and not self.is_monitoring:
                    self.log("Partida detectada! Iniciando monitoramento automático...")
                    self.start_monitoring()
            else:
                self.game_status_label.config(
                    text="🟡 League of Legends - Menu/Lobby",
                    fg=self.warning
                )
        else:
            self.game_status_label.config(
                text="🔴 League of Legends não está rodando",
                fg=self.danger
            )

        # Verificar novamente em 2 segundos
        self.root.after(2000, self.check_game_status)

    def toggle_auto_mode(self):
        """Alterna modo automático"""
        if self.auto_mode_var.get():
            self.log("Modo automático ativado - monitoramento iniciará com LoL")
        else:
            self.log("Modo automático desativado")

    def toggle_monitoring(self):
        """Inicia ou para o monitoramento"""
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        """Inicia o monitoramento"""
        self.is_monitoring = True
        self.start_stop_btn.config(
            text="⏸️ PARAR MONITORAMENTO",
            bg=self.danger
        )
        self.log("Monitoramento iniciado!")
        self.metric_status.config(text="🟢 ATIVO", fg=self.success)

        # TODO: Integrar com PlayerMonitor real
        # Por enquanto, apenas simula
        self.log("NOTA: Integração com câmera será implementada")

    def stop_monitoring(self):
        """Para o monitoramento"""
        self.is_monitoring = False
        self.start_stop_btn.config(
            text="▶️ INICIAR MONITORAMENTO",
            bg=self.success
        )
        self.log("Monitoramento parado")
        self.metric_status.config(text="⚪ PARADO", fg="#888888")

    def update_metrics(self, data):
        """Atualiza as métricas na tela"""
        # Esta função será chamada pelo PlayerMonitor
        pass


def main():
    """Função principal"""
    root = tk.Tk()
    app = VisionLOLApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
