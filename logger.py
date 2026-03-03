# -*- coding: utf-8 -*-
"""
Sistema de Logging para VisionLOL
Salva logs em arquivo e console
"""

import logging
import os
from datetime import datetime


class VisionLogger:
    """Logger customizado para VisionLOL"""

    def __init__(self, name="VisionLOL", log_to_file=True, log_to_console=True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Limpa handlers anteriores
        self.logger.handlers = []

        # Formato do log
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Log para arquivo
        if log_to_file:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"visionlol_{timestamp}.log")

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            print(f"Log file: {log_file}")

        # Log para console
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def debug(self, msg):
        """Log de debug (mais detalhado)"""
        self.logger.debug(msg)

    def info(self, msg):
        """Log de informação"""
        self.logger.info(msg)

    def warning(self, msg):
        """Log de aviso"""
        self.logger.warning(msg)

    def error(self, msg):
        """Log de erro"""
        self.logger.error(msg)

    def critical(self, msg):
        """Log crítico"""
        self.logger.critical(msg)

    def exception(self, msg):
        """Log de exceção (inclui traceback)"""
        self.logger.exception(msg)


# Instância global
_logger = None


def get_logger(name="VisionLOL"):
    """Obtém o logger global"""
    global _logger
    if _logger is None:
        _logger = VisionLogger(name)
    return _logger
