# -*- coding: utf-8 -*-
"""
Instant Start - Modo de Inicialização INSTANTÂNEA
Câmera abre IMEDIATAMENTE sem delays
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import PlayerMonitor

# Configuração rápida
print("VisionLOL - INSTANT START")
print("Inicializando...")

# Cria e inicia em uma linha
monitor = PlayerMonitor(auto_start_camera=True, show_debug=False)

print("Pronto! Pressione 'q' para sair\n")

# Roda indefinidamente (até pressionar 'q')
monitor.run(duration=999999)
