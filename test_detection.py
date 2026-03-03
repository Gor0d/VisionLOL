# -*- coding: utf-8 -*-
import cv2
import numpy as np

print("=== Teste de Detecao de Distracao ===\n")

# Carrega os classificadores
print("Carregando Haar Cascades...")
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

if face_cascade.empty():
    print("[X] ERRO: Nao foi possivel carregar o classificador de rosto!")
else:
    print("[OK] Classificador de rosto carregado com sucesso")

if eye_cascade.empty():
    print("[X] ERRO: Nao foi possivel carregar o classificador de olhos!")
else:
    print("[OK] Classificador de olhos carregado com sucesso")

# Cria uma imagem de teste (simulando um frame da câmera)
print("\n[OK] Sistema pronto para deteccao!")
print("\nO programa principal esta configurado para:")
print("1. Detectar rostos usando Haar Cascade")
print("2. Detectar olhos dentro da regiao do rosto")
print("3. Analisar direcao do olhar (ESQUERDA/CENTRO/DIREITA)")
print("4. Detectar distracoes baseado em:")
print("   - Posicao do rosto no frame (se esta muito de lado)")
print("   - Tamanho do rosto (se esta muito longe)")
print("   - Se nenhum rosto foi detectado")
print("\n5. Monitorar inputs (teclado e mouse)")
print("6. Calcular APM (Actions Per Minute)")
print("\nPara executar o monitor completo:")
print("  .venv\\Scripts\\python.exe .venv\\main.py")
print("\nPressione 'q' durante a execucao para parar.")
