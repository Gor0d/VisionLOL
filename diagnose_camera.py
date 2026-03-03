# -*- coding: utf-8 -*-
"""
Diagnóstico de Câmera - Identifica problemas
"""

import cv2
import sys
import psutil

print("=" * 70)
print("DIAGNOSTICO DE CAMERA - VisionLOL")
print("=" * 70)
print()

# 1. Verifica processos que podem estar usando câmera
print("1. VERIFICANDO PROCESSOS QUE PODEM USAR CAMERA...")
print("-" * 70)

camera_apps = [
    "Teams.exe",
    "Zoom.exe",
    "Skype.exe",
    "Discord.exe",
    "Chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "obs64.exe",
    "obs32.exe",
    "StreamlabsOBS.exe"
]

found_apps = []
for proc in psutil.process_iter(['name']):
    try:
        if proc.info['name'] in camera_apps:
            found_apps.append(proc.info['name'])
    except:
        pass

if found_apps:
    print("AVISO: Programas que podem estar usando a camera:")
    for app in set(found_apps):
        print(f"  - {app}")
    print("\nRecomendacao: Feche esses programas e tente novamente")
else:
    print("OK: Nenhum programa conhecido usando camera detectado")

print()

# 2. Tenta abrir a câmera com diferentes índices
print("2. TESTANDO INDICES DE CAMERA...")
print("-" * 70)

for i in range(5):
    print(f"\nTestando camera indice {i}...")
    try:
        cap = cv2.VideoCapture(i)

        if cap is None:
            print(f"  [FALHOU] VideoCapture retornou None")
            continue

        is_opened = cap.isOpened()
        print(f"  isOpened(): {is_opened}")

        if is_opened:
            # Tenta ler um frame
            ret, frame = cap.read()
            print(f"  Leitura de frame: ret={ret}")

            if ret and frame is not None:
                print(f"  Resolucao: {frame.shape[1]}x{frame.shape[0]}")
                print(f"  [SUCESSO] Camera {i} funciona!")

                # Mostra propriedades
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)

                print(f"  Propriedades:")
                print(f"    - Width: {width}")
                print(f"    - Height: {height}")
                print(f"    - FPS: {fps}")
            else:
                print(f"  [FALHOU] Nao conseguiu ler frame")
        else:
            print(f"  [FALHOU] Camera nao abriu")

        cap.release()

    except Exception as e:
        print(f"  [ERRO] Exception: {str(e)}")

print()
print("=" * 70)

# 3. Teste específico com índice 0
print("\n3. TESTE DETALHADO COM CAMERA 0...")
print("-" * 70)

try:
    print("Criando VideoCapture(0)...")
    cap = cv2.VideoCapture(0)

    print(f"Objeto criado: {cap is not None}")

    if cap is None:
        print("ERRO CRITICO: VideoCapture retornou None!")
        sys.exit(1)

    print("Verificando se abriu...")
    is_opened = cap.isOpened()
    print(f"isOpened(): {is_opened}")

    if not is_opened:
        print("\nERRO: Camera nao abriu!")
        print("\nPossiveis causas:")
        print("  1. Camera desconectada")
        print("  2. Camera em uso por outro programa")
        print("  3. Drivers da camera com problema")
        print("  4. Permissoes de camera negadas pelo Windows")
        print("  5. Camera desabilitada no Gerenciador de Dispositivos")
        print("\nVerifique:")
        print("  - Configuracoes do Windows > Privacidade > Camera")
        print("  - Gerenciador de Dispositivos > Cameras")
        sys.exit(1)

    print("\nConfigurando propriedades...")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("Lendo primeiro frame...")
    ret, frame = cap.read()

    if not ret:
        print("ERRO: Nao conseguiu ler frame!")
        cap.release()
        sys.exit(1)

    print(f"Frame lido com sucesso!")
    print(f"Shape: {frame.shape}")
    print(f"Dtype: {frame.dtype}")

    print("\nLendo mais 5 frames para testar estabilidade...")
    for i in range(5):
        ret, frame = cap.read()
        status = "OK" if ret else "FALHOU"
        print(f"  Frame {i+1}: {status}")

    cap.release()

    print("\n" + "=" * 70)
    print("DIAGNOSTICO CONCLUIDO COM SUCESSO!")
    print("A camera esta funcionando normalmente.")
    print("=" * 70)

except Exception as e:
    print(f"\nERRO CRITICO: {str(e)}")
    import traceback
    print("\nTraceback completo:")
    traceback.print_exc()
    sys.exit(1)
