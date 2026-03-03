# -*- coding: utf-8 -*-
"""
Exemplo de Uso do PlayerMonitor
================================

Este script demonstra como usar o sistema de monitoramento de jogadores
com diferentes configurações.
"""

import sys
sys.path.insert(0, '.venv')

# Para usar o PlayerMonitor, você precisa de uma câmera conectada
# Caso contrário, o script vai dar erro ao tentar abrir a câmera

print("=" * 60)
print("EXEMPLO DE USO - PlayerMonitor")
print("=" * 60)
print()

# Exemplo 1: Uso básico (30 segundos)
print("Exemplo 1: Monitoramento básico de 30 segundos")
print("-" * 60)
print("from main import PlayerMonitor")
print("monitor = PlayerMonitor()")
print("monitor.run(duration=30)")
print()

# Exemplo 2: Sessão longa (5 minutos)
print("Exemplo 2: Sessão longa de 5 minutos")
print("-" * 60)
print("from main import PlayerMonitor")
print("monitor = PlayerMonitor()")
print("monitor.run(duration=300)  # 300 segundos = 5 minutos")
print()

# Exemplo 3: Como interpretar os resultados
print("Exemplo 3: Interpretando os resultados")
print("-" * 60)
print("Após executar, você verá:")
print()
print("TELA DE MONITORAMENTO:")
print("  - FOCADO / DISTRAIDO / MUITO DISTRAIDO")
print("  - Motivo: (tipo de distração detectada)")
print("  - Olhar: ESQUERDA / CENTRO / DIREITA")
print("  - Confianca: percentual de certeza")
print("  - Distracoes: contador de eventos")
print("  - APM: Actions Per Minute (teclas + cliques)")
print()
print("RELATÓRIO FINAL:")
print("  - Duração total")
print("  - Total de distrações")
print("  - Total de inputs (teclas e cliques)")
print("  - APM médio")
print("  - Distribuição de olhar (% por direção)")
print()

# Exemplo 4: Configurações recomendadas
print("Exemplo 4: Configurações Recomendadas")
print("-" * 60)
print()
print("Para JOGOS COMPETITIVOS (LoL, CS:GO, etc):")
print("  - Duração: 15-30 minutos")
print("  - Foco em: APM, direção do olhar, distrações")
print()
print("Para ESTUDOS/TRABALHO:")
print("  - Duração: 25 minutos (Pomodoro)")
print("  - Foco em: distrações, sonolência")
print()
print("Para TESTES RÁPIDOS:")
print("  - Duração: 1-2 minutos")
print("  - Foco em: validar detecção de rosto e olhos")
print()

# Exemplo 5: Troubleshooting
print("Exemplo 5: Solução de Problemas")
print("-" * 60)
print()
print("PROBLEMA: Script trava ao abrir")
print("SOLUÇÃO: Verifique se a câmera está disponível e não em uso")
print()
print("PROBLEMA: Não detecta olhos com óculos")
print("SOLUÇÃO: Sistema usa detecção híbrida, mas óculos muito")
print("         escuros/reflexivos podem dificultar")
print()
print("PROBLEMA: Muitos falsos positivos de distração")
print("SOLUÇÃO: Ajuste os thresholds no código (veja MELHORIAS.md)")
print()
print("PROBLEMA: FPS baixo")
print("SOLUÇÃO: Reduza resolução da câmera ou minSize dos cascades")
print()

print("=" * 60)
print("Para executar o monitor:")
print(".venv\\Scripts\\python.exe .venv\\main.py")
print("=" * 60)
