# -*- coding: utf-8 -*-
"""
Game Detector - Detecta quando o League of Legends está rodando
"""

import psutil
import time
import ctypes
from ctypes import wintypes

# Windows API para detectar janela ativa
user32 = ctypes.windll.user32


class GameDetector:
    """Detecta quando o League of Legends está em execução"""

    # Processos conhecidos do League of Legends
    LOL_PROCESSES = [
        "League of Legends.exe",
        "LeagueClient.exe",
        "LeagueClientUx.exe"
    ]

    # Títulos de janela para detectar se está em partida
    IN_GAME_TITLES = [
        "League of Legends (TM) Client",
        "League of Legends"
    ]

    def __init__(self):
        self.is_running = False
        self.is_in_game = False
        self.is_live_api_available = False
        self.lol_process = None

    def check_process_running(self):
        """Verifica se algum processo do LoL está rodando"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in self.LOL_PROCESSES:
                    self.lol_process = proc
                    self.is_running = True
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        self.is_running = False
        self.lol_process = None
        return False

    def get_active_window_title(self):
        """Pega o título da janela ativa no Windows"""
        try:
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception as e:
            return ""

    def check_in_game(self):
        """Verifica se está dentro de uma partida (não no menu)"""
        if not self.is_running:
            return False

        window_title = self.get_active_window_title()

        # Verifica se a janela ativa contém os títulos conhecidos
        for title in self.IN_GAME_TITLES:
            if title in window_title:
                self.is_in_game = True
                return True

        self.is_in_game = False
        return False

    def check_live_client_api(self):
        """Verifica se a Live Client API esta acessivel (jogo ativo)"""
        try:
            import requests
            resp = requests.get(
                "https://127.0.0.1:2999/liveclientdata/gamestats",
                verify=False, timeout=1
            )
            self.is_live_api_available = resp.status_code == 200
        except Exception:
            self.is_live_api_available = False
        return self.is_live_api_available

    def get_status(self):
        """Retorna status completo do jogo"""
        self.check_process_running()

        if not self.is_running:
            self.is_live_api_available = False
            return {
                'running': False,
                'in_game': False,
                'live_api': False,
                'status': 'LoL não está rodando'
            }

        self.check_in_game()

        # Verifica Live Client API se estiver em partida
        if self.is_in_game:
            self.check_live_client_api()
            status_text = 'EM PARTIDA'
        else:
            self.is_live_api_available = False
            status_text = 'No menu/lobby'

        return {
            'running': True,
            'in_game': self.is_in_game,
            'live_api': self.is_live_api_available,
            'status': status_text,
            'process': self.lol_process.name() if self.lol_process else None
        }

    def wait_for_game_start(self, check_interval=2.0):
        """
        Aguarda o jogo iniciar (modo bloqueante)

        Args:
            check_interval: Tempo em segundos entre verificações

        Returns:
            True quando o jogo iniciar
        """
        print("Aguardando League of Legends iniciar...")

        while True:
            status = self.get_status()

            if status['in_game']:
                print("Partida detectada! Iniciando monitoramento...")
                return True

            if status['running']:
                print(f"Status: {status['status']} - Aguardando entrar em partida...")
            else:
                print("LoL não está rodando. Aguardando...")

            time.sleep(check_interval)

    def monitor_game(self, on_game_start=None, on_game_end=None, check_interval=2.0):
        """
        Monitora o jogo continuamente e chama callbacks

        Args:
            on_game_start: Função chamada quando partida inicia
            on_game_end: Função chamada quando partida termina
            check_interval: Tempo entre verificações
        """
        was_in_game = False

        print("Monitoramento contínuo iniciado...")
        print("Pressione Ctrl+C para parar")

        try:
            while True:
                status = self.get_status()
                is_in_game = status['in_game']

                # Detecta transição: NÃO em jogo -> EM jogo
                if is_in_game and not was_in_game:
                    print("\n[EVENTO] Partida iniciada!")
                    if on_game_start:
                        on_game_start(status)

                # Detecta transição: EM jogo -> NÃO em jogo
                elif not is_in_game and was_in_game:
                    print("\n[EVENTO] Partida finalizada!")
                    if on_game_end:
                        on_game_end(status)

                was_in_game = is_in_game
                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\nMonitoramento interrompido pelo usuário.")


# Exemplo de uso
if __name__ == "__main__":
    detector = GameDetector()

    print("=== League of Legends Detector ===\n")

    # Teste 1: Verificação única
    print("1. Verificação única:")
    status = detector.get_status()
    print(f"   Running: {status['running']}")
    print(f"   In Game: {status['in_game']}")
    print(f"   Status: {status['status']}")
    print()

    # Teste 2: Monitoramento contínuo
    print("2. Iniciando monitoramento contínuo...")
    print("   (Pressione Ctrl+C para parar)\n")

    def on_start(status):
        print(">>> CALLBACK: Partida começou! Iniciar monitoramento aqui.")

    def on_end(status):
        print(">>> CALLBACK: Partida terminou! Parar monitoramento aqui.")

    detector.monitor_game(
        on_game_start=on_start,
        on_game_end=on_end,
        check_interval=3.0
    )
