# -*- coding: utf-8 -*-
"""
VisionLOL Agent — captura automática de scrims via Live Client API.

Instale nas máquinas dos jogadores. Monitora localhost:2999 e envia
os dados da partida ao servidor VisionLOL do coach ao fim de cada jogo.

Não interage com o processo do LoL — apenas lê a API HTTP oficial
em localhost:2999. Compatível com Vanguard.
"""

import json
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

import requests
import urllib3

# Desabilita warnings de SSL (certificado self-signed do LoL em localhost)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Importa config relativo (funciona tanto como script quanto como exe)
if getattr(sys, "frozen", False):
    import os
    sys.path.insert(0, os.path.dirname(sys.executable))

import agent_config  # noqa: E402

# ── Constantes ────────────────────────────────────────────────────────
LIVE_BASE    = "https://127.0.0.1:2999"
POLL_SECONDS = 5
VERSION      = "1.0"

BG      = "#0d1117"
BG_DARK = "#161b22"
BG_MED  = "#21262d"
ACCENT  = "#58a6ff"
SUCCESS = "#3fb950"
DANGER  = "#f85149"
WARNING = "#d29922"
TEXT    = "#e6edf3"
DIM     = "#7d8590"


# ═══════════════════════════════════════════════════════════════════════
#  NÚCLEO DO AGENTE
# ═══════════════════════════════════════════════════════════════════════

class Agent:
    """Monitora o Live Client e envia dados ao servidor."""

    def __init__(self, on_status):
        self._on_status  = on_status   # callback(msg: str, color: str)
        self._stop       = threading.Event()
        self._thread     = None
        self._last_game  = None        # evita re-enviar o mesmo jogo
        self._cfg        = agent_config.load()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="AgentLoop")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def reload_config(self):
        self._cfg = agent_config.load()

    # ── Loop principal ─────────────────────────────────────────────────

    def _loop(self):
        self._status("Aguardando LoL iniciar…", DIM)
        in_game = False

        while not self._stop.is_set():
            allgame = self._get_allgamedata()

            if allgame is None:
                if in_game:
                    # Jogo encerrou abruptamente (cliente fechado antes do GameEnd)
                    in_game = False
                    self._status("Jogo encerrado.", DIM)
                else:
                    self._status("Aguardando LoL iniciar…", DIM)
                time.sleep(POLL_SECONDS)
                continue

            if not in_game:
                in_game = True
                self._status("Jogo detectado! Monitorando…", ACCENT)

            # Verifica evento GameEnd
            events = allgame.get("events", {}).get("Events", [])
            end_ev = next((e for e in events if e.get("EventName") == "GameEnd"), None)

            if end_ev:
                game_time = allgame.get("gameData", {}).get("gameTime", 0)
                game_key  = f"{int(game_time)}"   # identificador único aproximado

                if game_key != self._last_game:
                    self._last_game = game_key
                    in_game = False
                    self._status("Jogo finalizado! Enviando dados…", WARNING)
                    self._send(allgame)

            time.sleep(POLL_SECONDS)

    def _get_allgamedata(self) -> dict | None:
        try:
            r = requests.get(f"{LIVE_BASE}/liveclientdata/allgamedata",
                             verify=False, timeout=2)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def _send(self, allgame: dict):
        cfg = self._cfg
        url   = cfg.get("server_url", "").rstrip("/")
        token = cfg.get("auth_token", "")
        pid   = cfg.get("player_riot_id", "")

        if not url or not token:
            self._status("⚠  Configure o servidor e o token primeiro.", DANGER)
            return
        if not pid:
            self._status("⚠  Configure seu Riot ID (Nome#TAG).", DANGER)
            return

        payload = {
            "player_riot_id": pid,
            "timestamp":      time.time(),
            "allgamedata":    allgame,
        }

        try:
            r = requests.post(
                f"{url}/capture",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if r.status_code == 201:
                cap_id = r.json().get("capture_id", "?")
                self._status(f"✓ Enviado com sucesso  ({cap_id})", SUCCESS)
            elif r.status_code == 401:
                self._status("⚠  Token inválido — verifique a configuração.", DANGER)
            else:
                self._status(f"⚠  Servidor respondeu {r.status_code}", WARNING)
        except requests.exceptions.ConnectionError:
            self._status("⚠  Servidor não alcançado. Verifique a URL.", DANGER)
        except Exception as e:
            self._status(f"Erro ao enviar: {e}", DANGER)

    def test_connection(self) -> tuple[bool, str]:
        """Testa conexão com o servidor. Retorna (ok, mensagem)."""
        cfg   = self._cfg
        url   = cfg.get("server_url", "").rstrip("/")
        token = cfg.get("auth_token", "")
        if not url:
            return False, "URL não configurada."
        try:
            r = requests.get(
                f"{url}/health",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            if r.status_code == 200:
                data = r.json()
                return True, (f"Conectado!  Versão: {data.get('version', '?')}  "
                              f"Capturas: {data.get('captures', '?')}")
            return False, f"Servidor respondeu {r.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Conexão recusada. Servidor offline ou URL incorreta."
        except Exception as e:
            return False, str(e)

    def _status(self, msg: str, color: str = TEXT):
        self._on_status(msg, color)


# ═══════════════════════════════════════════════════════════════════════
#  INTERFACE GRÁFICA
# ═══════════════════════════════════════════════════════════════════════

class AgentApp:
    """Janela principal do VisionLOL Agent."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"VisionLOL Agent  v{VERSION}")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._cfg = agent_config.load()
        self._agent = Agent(on_status=self._on_status)
        self._build()
        self._agent.start()

    # ── Layout ────────────────────────────────────────────────────────

    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg="#1a3a5f", height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚔  VisionLOL Agent",
                 font=("Segoe UI", 14, "bold"),
                 bg="#1a3a5f", fg=TEXT).pack(side=tk.LEFT, padx=14, pady=10)
        tk.Label(hdr, text=f"v{VERSION}",
                 font=("Segoe UI", 9),
                 bg="#1a3a5f", fg=DIM).pack(side=tk.RIGHT, padx=14)

        # Status
        status_frame = tk.Frame(self.root, bg=BG_DARK, height=52)
        status_frame.pack(fill=tk.X, padx=10, pady=(8, 4))
        status_frame.pack_propagate(False)
        self._status_dot = tk.Label(status_frame, text="●",
                                    font=("Segoe UI", 14),
                                    bg=BG_DARK, fg=DIM)
        self._status_dot.pack(side=tk.LEFT, padx=(12, 4), pady=12)
        self._status_lbl = tk.Label(status_frame, text="Iniciando…",
                                    font=("Segoe UI", 10),
                                    bg=BG_DARK, fg=TEXT, anchor="w",
                                    wraplength=340)
        self._status_lbl.pack(side=tk.LEFT, pady=12, fill=tk.X, expand=True)

        # Configurações
        cfg_frame = tk.LabelFrame(self.root, text="  Configuração  ",
                                  font=("Segoe UI", 9, "bold"),
                                  bg=BG, fg=DIM,
                                  relief=tk.FLAT, bd=1,
                                  highlightbackground="#30363d",
                                  highlightthickness=1)
        cfg_frame.pack(fill=tk.X, padx=10, pady=4)

        self._url_var = tk.StringVar(value=self._cfg.get("server_url", ""))
        self._tok_var = tk.StringVar(value=self._cfg.get("auth_token", ""))
        self._pid_var = tk.StringVar(value=self._cfg.get("player_riot_id", ""))

        for label, var, ph in [
            ("URL do Servidor", self._url_var, "http://192.168.1.10:7654"),
            ("Token",           self._tok_var, "Cole o token do VisionLOL"),
            ("Seu Riot ID",     self._pid_var, "Nome#TAG (ex: paiN Kami#BR1)"),
        ]:
            row = tk.Frame(cfg_frame, bg=BG)
            row.pack(fill=tk.X, padx=8, pady=3)
            tk.Label(row, text=label, font=("Segoe UI", 9), bg=BG, fg=DIM,
                     width=16, anchor="w").pack(side=tk.LEFT)
            entry = tk.Entry(row, textvariable=var,
                             font=("Segoe UI", 9),
                             bg=BG_MED, fg=TEXT,
                             insertbackground=TEXT,
                             relief=tk.FLAT, bd=3, width=36)
            entry.pack(side=tk.LEFT, padx=(4, 0), pady=2)
            if not var.get():
                entry.insert(0, ph)
                entry.config(fg=DIM)
                def _clear(e, en=entry, fv=var, p=ph):
                    if en.get() == p:
                        en.delete(0, tk.END)
                        en.config(fg=TEXT)
                def _restore(e, en=entry, fv=var, p=ph):
                    if not en.get():
                        en.insert(0, p)
                        en.config(fg=DIM)
                entry.bind("<FocusIn>", _clear)
                entry.bind("<FocusOut>", _restore)

        # Botões
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(fill=tk.X, padx=10, pady=(4, 10))

        tk.Button(btn_frame, text="Salvar",
                  font=("Segoe UI", 9, "bold"),
                  bg="#1a5f3f", fg=TEXT,
                  relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._save).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(btn_frame, text="Testar Conexão",
                  font=("Segoe UI", 9),
                  bg=BG_MED, fg=ACCENT,
                  relief=tk.FLAT, cursor="hand2", padx=14, pady=6,
                  command=self._test).pack(side=tk.LEFT)

        tk.Button(btn_frame, text="?",
                  font=("Segoe UI", 9),
                  bg=BG_MED, fg=DIM,
                  relief=tk.FLAT, cursor="hand2", padx=10, pady=6,
                  command=self._help).pack(side=tk.RIGHT)

        # Ajusta tamanho da janela
        self.root.update_idletasks()
        self.root.geometry(f"480x{self.root.winfo_reqheight()}")

    # ── Callbacks ─────────────────────────────────────────────────────

    def _on_status(self, msg: str, color: str = TEXT):
        """Callback seguro (pode vir de thread)."""
        def _update():
            self._status_lbl.config(text=msg, fg=color)
            self._status_dot.config(fg=color)
        try:
            self.root.after(0, _update)
        except Exception:
            pass

    def _save(self):
        url = self._url_var.get().strip()
        tok = self._tok_var.get().strip()
        pid = self._pid_var.get().strip()

        # Remove placeholders
        PLACEHOLDERS = {"http://192.168.1.10:7654",
                        "Cole o token do VisionLOL",
                        "Nome#TAG (ex: paiN Kami#BR1)"}
        if url in PLACEHOLDERS: url = ""
        if tok in PLACEHOLDERS: tok = ""
        if pid in PLACEHOLDERS: pid = ""

        cfg = {"server_url": url, "auth_token": tok, "player_riot_id": pid}
        agent_config.save(cfg)
        self._agent._cfg = cfg
        messagebox.showinfo("Salvo", "Configuração salva com sucesso!", parent=self.root)

    def _test(self):
        self._on_status("Testando conexão…", ACCENT)
        self._save()

        def _run():
            ok, msg = self._agent.test_connection()
            self._on_status(msg, SUCCESS if ok else DANGER)

        threading.Thread(target=_run, daemon=True).start()

    def _help(self):
        messagebox.showinfo(
            "Como usar o VisionLOL Agent",
            "1. No VisionLOL do coach, vá em Scrims e clique 'Iniciar Servidor'.\n"
            "2. Clique 'Copiar config para jogadores' e envie para o time.\n"
            "3. Cada jogador cola a URL e o Token aqui.\n"
            "4. Configure seu Riot ID (exatamente como aparece no LoL).\n"
            "5. Clique Salvar e deixe o Agent aberto ao jogar.\n\n"
            "O Agent detecta automaticamente o fim de cada partida e envia\n"
            "os dados para o VisionLOL do coach.\n\n"
            "Compatível com Vanguard — usa apenas a API oficial do LoL.",
            parent=self.root
        )

    def _on_close(self):
        self._agent.stop()
        self.root.destroy()


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    AgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
