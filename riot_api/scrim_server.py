# -*- coding: utf-8 -*-
"""
ScrimServer — servidor HTTP embutido no VisionLOL para receber capturas
ao vivo dos agentes instalados nas máquinas dos jogadores.

Roda como thread daemon dentro do processo do VisionLOL.
Agentes fazem POST /capture com allgamedata do Live Client API.
"""

import json
import os
import socket
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Pasta onde as capturas são salvas
CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scrim_captures")

_flask_imported = False
try:
    from flask import Flask, request, jsonify
    _flask_imported = True
except ImportError:
    logger.warning("Flask não encontrado — servidor de scrims indisponível.")


class ScrimServer:
    """
    Servidor HTTP leve que recebe capturas de partidas dos agentes.

    Uso:
        server = ScrimServer(port=7654, token="meu-token")
        server.start()
        server.stop()
        captures = server.get_captures(since=timestamp)
    """

    VERSION = "1.0"

    def __init__(self, port: int = 7654, token: str = ""):
        self.port  = port
        self.token = token
        self._thread: threading.Thread | None = None
        self._server = None   # werkzeug server instance
        self._lock   = threading.Lock()
        os.makedirs(CAPTURES_DIR, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        """Inicia o servidor Flask em uma thread daemon."""
        if not _flask_imported:
            raise RuntimeError("Flask não instalado. Execute: pip install flask")
        if self.is_running:
            return

        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="ScrimServer")
        self._thread.start()
        # Aguarda até 3s para confirmar que subiu
        for _ in range(30):
            time.sleep(0.1)
            if self.is_running:
                break
        logger.info(f"ScrimServer iniciado na porta {self.port}")

    def stop(self):
        """Para o servidor (encerra o processo werkzeug via sinal interno)."""
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
        self._thread = None
        logger.info("ScrimServer parado")

    def get_local_ip(self) -> str:
        """Retorna o IP local da máquina (para exibir ao coach)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_url(self) -> str:
        return f"http://{self.get_local_ip()}:{self.port}"

    def get_captures(self, since: float = 0.0) -> list[dict]:
        """
        Retorna lista de capturas com timestamp >= since.
        Cada captura é um dict com os campos salvos pelo agente.
        """
        captures = []
        with self._lock:
            try:
                for fname in sorted(os.listdir(CAPTURES_DIR)):
                    if not fname.endswith(".json"):
                        continue
                    fpath = os.path.join(CAPTURES_DIR, fname)
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            data = json.load(f)
                        ts = data.get("timestamp", 0)
                        if ts >= since:
                            captures.append(data)
                    except Exception:
                        pass
            except Exception:
                pass
        return captures

    def get_capture_count(self) -> int:
        """Retorna o número total de capturas salvas."""
        try:
            return sum(1 for f in os.listdir(CAPTURES_DIR) if f.endswith(".json"))
        except Exception:
            return 0

    # ── Internals ─────────────────────────────────────────────────────

    def _run(self):
        """Cria e inicia o app Flask."""
        app = self._build_app()

        # Silencia o logger do werkzeug
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        from werkzeug.serving import make_server
        try:
            self._server = make_server("0.0.0.0", self.port, app)
            self._server.serve_forever()
        except OSError as e:
            logger.error(f"ScrimServer: porta {self.port} em uso ou erro: {e}")
        except Exception as e:
            logger.error(f"ScrimServer: erro inesperado: {e}")
        finally:
            self._server = None

    def _build_app(self) -> "Flask":
        app = Flask("ScrimServer")
        token = self.token
        lock  = self._lock

        def _check_auth() -> bool:
            auth = request.headers.get("Authorization", "")
            return auth == f"Bearer {token}"

        @app.get("/health")
        def health():
            return jsonify({
                "status":   "ok",
                "version":  ScrimServer.VERSION,
                "captures": self.get_capture_count(),
            })

        @app.post("/capture")
        def capture():
            if not _check_auth():
                return jsonify({"error": "Unauthorized"}), 401

            payload = request.get_json(silent=True)
            if not payload:
                return jsonify({"error": "Invalid JSON"}), 400

            required = {"player_riot_id", "allgamedata"}
            if not required.issubset(payload.keys()):
                return jsonify({"error": f"Missing fields: {required - payload.keys()}"}), 400

            ts = payload.get("timestamp") or time.time()
            player_id = payload["player_riot_id"].replace("#", "_").replace(" ", "_")
            dt_str    = datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S")
            fname     = f"capture_{dt_str}_{player_id}.json"
            fpath     = os.path.join(CAPTURES_DIR, fname)

            capture_data = {
                "capture_id":     f"LIVE_{dt_str}",
                "timestamp":      ts,
                "player_riot_id": payload["player_riot_id"],
                "allgamedata":    payload["allgamedata"],
                "received_at":    time.time(),
            }

            with lock:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(capture_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Captura recebida de {payload['player_riot_id']} → {fname}")
            return jsonify({"status": "ok", "capture_id": capture_data["capture_id"]}), 201

        @app.get("/captures")
        def captures():
            if not _check_auth():
                return jsonify({"error": "Unauthorized"}), 401

            since = float(request.args.get("since", 0))
            data  = self.get_captures(since=since)
            return jsonify({"captures": data, "count": len(data)})

        @app.post("/live_update")
        def live_update():
            """
            Recebe snapshot ao vivo do agente e repassa ao web dashboard.
            O repasse é feito em background para não bloquear o agente.
            """
            if not _check_auth():
                return jsonify({"error": "Unauthorized"}), 401

            payload = request.get_json(silent=True)
            if not payload:
                return jsonify({"error": "Invalid JSON"}), 400

            # Repassa ao web dashboard em thread separada (best-effort)
            threading.Thread(
                target=self._forward_live,
                args=(payload,),
                daemon=True,
            ).start()

            return jsonify({"status": "ok"}), 200

        return app

    def _forward_live(self, payload: dict):
        """Envia o snapshot ao /api/live/update do web dashboard."""
        try:
            from .config import load_config
        except ImportError:
            try:
                from riot_api.config import load_config
            except ImportError:
                return

        cfg       = load_config()
        dash_url  = cfg.get("web_dashboard_url", "").rstrip("/")
        api_token = cfg.get("web_api_token", "")

        if not dash_url or not api_token:
            return  # web dashboard não configurado — silencia

        try:
            import requests as _req
            _req.post(
                f"{dash_url}/api/live/update",
                json=payload,
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=8,
            )
        except Exception as e:
            logger.debug(f"[live_forward] {e}")
