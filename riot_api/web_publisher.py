# -*- coding: utf-8 -*-
"""
WebPublisher — envia dados de scrim para o dashboard Next.js hospedado no Veloz.

Uso:
    pub = WebPublisher(base_url="https://visionlol.veloz.app", token="Bearer TOKEN")
    ok, msg = pub.publish_session(session_dict, players_list, pool_list)
"""

import json
import urllib.request
import urllib.error
from typing import Any


class WebPublisher:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token    = token

    # ── Verificar conectividade ────────────────────────────────────────────────
    def health_check(self) -> tuple[bool, str]:
        """Retorna (ok, mensagem)."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
                return True, data.get("status", "ok")
        except Exception as e:
            return False, str(e)

    # ── Publicar sessão ───────────────────────────────────────────────────────
    def publish_session(
        self,
        session: dict[str, Any],
        players: list[dict[str, Any]],
        champion_pool: list[dict[str, Any]] | None = None,
    ) -> tuple[bool, str]:
        """
        Envia dados para POST /api/publish.

        Args:
            session:       dict com id, date, opponent, notes, wins, losses, metadata
            players:       lista de dicts por jogador com stats
            champion_pool: lista de entradas {player_key, role, champ, games, wins, kda}

        Returns:
            (ok: bool, mensagem: str)
        """
        payload = {
            "session":      session,
            "players":      players,
            "champion_pool": champion_pool or [],
        }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req  = urllib.request.Request(
            f"{self.base_url}/api/publish",
            data=body,
            method="POST",
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                players_n = data.get("players_upserted", 0)
                pool_n    = data.get("pool_upserted", 0)
                return True, f"Publicado — {players_n} jogadores, {pool_n} pool entries"
        except urllib.error.HTTPError as e:
            try:
                body_err = json.loads(e.read())
                msg = body_err.get("error", str(e))
            except Exception:
                msg = str(e)
            return False, f"HTTP {e.code}: {msg}"
        except Exception as e:
            return False, str(e)
