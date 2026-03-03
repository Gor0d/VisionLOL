# -*- coding: utf-8 -*-
"""
Cliente HTTP compartilhado para APIs da Riot Games
- SSL bypass para Live Client API (localhost)
- Injecao de API key para Riot REST APIs
- Rate limiting com sliding window
"""

import time
import sys
import os
from collections import deque

import requests
import urllib3

# Desabilita warning de SSL para requests ao localhost
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logger com fallback
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from logger import get_logger
    logger = get_logger("RiotHTTP")
except Exception:
    class _DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = _DummyLogger()


class RiotHTTPClient:
    """Cliente HTTP para todas as APIs da Riot"""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self._request_timestamps = deque(maxlen=100)

    def get_live(self, endpoint, timeout=2):
        """GET para Live Client API (localhost, SSL bypass, sem API key)"""
        try:
            resp = requests.get(endpoint, verify=False, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            # Jogo nao esta ativo — silencioso
            return None
        except requests.exceptions.Timeout:
            logger.debug(f"Timeout ao acessar Live Client API: {endpoint}")
            return None
        except Exception as e:
            logger.warning(f"Erro ao acessar Live Client API: {e}")
            return None

    def get_riot(self, url, params=None, timeout=10):
        """GET para Riot REST APIs (com API key e rate limiting)"""
        if not self.api_key:
            logger.error("API key nao configurada!")
            return None

        # Verifica rate limit
        self._wait_rate_limit()

        headers = {"X-Riot-Token": self.api_key}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)

            # Registra timestamp da requisicao
            self._request_timestamps.append(time.time())

            # Rate limited
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                logger.warning(f"Rate limited! Aguardando {retry_after}s...")
                time.sleep(retry_after)
                return self.get_riot(url, params, timeout)

            # API key invalida/expirada
            if resp.status_code == 403:
                logger.error("API key invalida ou expirada! Renove em developer.riotgames.com")
                return None

            # Nao encontrado
            if resp.status_code == 404:
                logger.warning(f"Recurso nao encontrado: {url}")
                return None

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.ConnectionError:
            logger.error(f"Erro de conexao com Riot API: {url}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao acessar Riot API: {url}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado na Riot API: {e}")
            return None

    def test_connection(self):
        """Testa se a API key esta funcionando"""
        if not self.api_key:
            return False, "API key nao configurada"

        # Usa endpoint de status da plataforma (sempre disponivel)
        url = "https://br1.api.riotgames.com/lol/status/v4/platform-data"
        headers = {"X-Riot-Token": self.api_key}
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                return True, "Conexao OK - API key valida!"
            elif resp.status_code == 403:
                return False, "API key invalida ou expirada"
            else:
                return False, f"Erro {resp.status_code}"
        except Exception as e:
            return False, f"Erro de conexao: {e}"

    def _wait_rate_limit(self):
        """Aguarda se estiver perto do rate limit"""
        now = time.time()

        # Limpa timestamps antigos (> 2 min)
        while self._request_timestamps and now - self._request_timestamps[0] > 120:
            self._request_timestamps.popleft()

        # Verifica limite de 2 minutos (100 requests)
        if len(self._request_timestamps) >= 95:
            oldest = self._request_timestamps[0]
            wait = 120 - (now - oldest) + 1
            if wait > 0:
                logger.info(f"Perto do rate limit (2min). Aguardando {wait:.1f}s...")
                time.sleep(wait)

        # Verifica limite de 1 segundo (20 requests)
        recent = [t for t in self._request_timestamps if now - t < 1.0]
        if len(recent) >= 18:
            time.sleep(0.2)
