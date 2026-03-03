# -*- coding: utf-8 -*-
"""
Quick Test - Teste Rápido com Câmera
Executa o monitoramento imediatamente ao rodar o script
"""

import sys
import os
import time

# Adiciona o diretório .venv ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.venv'))

from main import PlayerMonitor

def main():
    print("=" * 60)
    print("🚀 VISIONLOL - TESTE RÁPIDO COM CÂMERA")
    print("=" * 60)
    print()
    print("⚡ Inicialização rápida ativada!")
    print("📷 Câmera abrirá automaticamente")
    print("⏱️  Duração do teste: 30 segundos")
    print()
    print("💡 CONTROLES:")
    print("   • Pressione 'q' para parar a qualquer momento")
    print("   • A janela mostrará seu rosto e métricas em tempo real")
    print()
    print("-" * 60)
    print()

    try:
        # Inicializa com debug habilitado
        print("⏳ Preparando sistema...")
        start_init = time.time()

        monitor = PlayerMonitor(auto_start_camera=True, show_debug=True)

        init_time = time.time() - start_init
        print()
        print(f"⚡ Sistema pronto em {init_time:.2f} segundos!")
        print()
        print("-" * 60)
        print("🎬 INICIANDO MONITORAMENTO...")
        print("-" * 60)
        print()

        # Executa por 30 segundos
        monitor.run(duration=30)

    except Exception as e:
        print()
        print("❌ ERRO:", str(e))
        print()
        print("💡 Possíveis soluções:")
        print("   1. Verifique se a câmera está conectada")
        print("   2. Feche outros programas usando a câmera")
        print("   3. Reinicie o script")
        print()
        return 1

    print()
    print("=" * 60)
    print("✅ Teste concluído com sucesso!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(main())
