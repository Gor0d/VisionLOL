# -*- coding: utf-8 -*-
import cv2
import numpy as np
from collections import deque
import time
import sys
import os

try:
    from pynput import keyboard, mouse
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# Importa logger (se disponível)
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from logger import get_logger
    logger = get_logger("PlayerMonitor")
except Exception:
    class DummyLogger:
        def debug(self, msg): pass
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def exception(self, msg): print(f"[EXCEPTION] {msg}")
    logger = DummyLogger()


class PlayerMonitor:
    def __init__(self, auto_start_camera=True, show_debug=True):
        self.debug = show_debug

        # Face and eye detection using OpenCV Haar Cascades
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.eye_glasses_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml')

        if self.face_cascade.empty() or self.eye_cascade.empty():
            raise Exception("Erro ao carregar Haar Cascades!")

        # Camera
        self.cap = None
        if auto_start_camera:
            self.open_camera()

        # Métricas
        self.gaze_history          = deque(maxlen=30)
        self.distraction_events    = []
        self.key_presses           = deque(maxlen=100)
        self.mouse_clicks          = deque(maxlen=100)
        self.face_positions        = deque(maxlen=10)
        self.eyes_detected_history = deque(maxlen=15)
        self.distraction_frames    = 0
        self.no_face_frames        = 0
        self.blink_counter         = 0

        # Estado
        self.is_monitoring = False
        self.start_time    = None

    def open_camera(self, camera_index=None):
        """Abre a câmera tentando múltiplos índices e backends automaticamente."""
        # Índices a tentar: parâmetro explícito, ou varredura 0-3
        indices = [camera_index] if camera_index is not None else [0, 1, 2, 3]

        # No Windows tenta DirectShow primeiro (mais estável)
        backends = []
        if sys.platform == "win32":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        else:
            backends = [cv2.CAP_ANY]

        for idx in indices:
            for backend in backends:
                logger.info(f"Tentando câmera índice={idx} backend={backend}...")
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap is None or not cap.isOpened():
                        cap.release()
                        continue

                    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 30)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    # Descarta primeiros frames que podem estar escuros
                    for _ in range(3):
                        cap.read()

                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.cap = cap
                        logger.info(f"Câmera aberta: índice={idx}, backend={backend}")
                        return True

                    cap.release()
                except Exception as e:
                    logger.debug(f"Falha índice={idx} backend={backend}: {e}")
                    continue

        raise Exception(
            "Nenhuma câmera disponível.\n"
            "Verifique:\n"
            "  • Câmera conectada e não em uso por outro app\n"
            "  • Permissão de câmera nas configurações do Windows\n"
            "  • Drivers atualizados"
        )

    def close_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def detect_eyes_hybrid(self, roi_gray):
        eyes = self.eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(eyes) == 0:
            eyes = self.eye_glasses_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(eyes) == 0:
            eyes = self.eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.05, minNeighbors=3, minSize=(25, 25))
        return eyes

    def detect_gaze_direction(self, eyes, face_roi):
        if len(eyes) < 2:
            return "CENTRO"
        eyes = sorted(eyes, key=lambda e: e[0])
        left_eye, right_eye = eyes[0], eyes[-1]
        face_width = face_roi.shape[1]
        eyes_center = ((left_eye[0] + left_eye[2] // 2) + (right_eye[0] + right_eye[2] // 2)) // 2
        offset_ratio = (eyes_center - face_width // 2) / face_width
        if offset_ratio > 0.08:
            return "DIREITA"
        elif offset_ratio < -0.08:
            return "ESQUERDA"
        return "CENTRO"

    def is_looking_away(self, face_rect, frame_shape):
        x, y, w, h = face_rect
        hx = (x + w / 2) / frame_shape[1]
        vy = (y + h / 2) / frame_shape[0]
        return hx < 0.25 or hx > 0.75 or vy < 0.2 or vy > 0.8 or w < frame_shape[1] * 0.15

    def detect_head_movement(self, current_face):
        if len(self.face_positions) < 5:
            return False
        x, y, w, h = current_face
        cx, cy = x + w // 2, y + h // 2
        movements = []
        for px, py, pw, ph in list(self.face_positions)[-5:]:
            movements.append(np.sqrt((cx - px - pw // 2) ** 2 + (cy - py - ph // 2) ** 2))
        return np.mean(movements) > 50

    def detect_drowsiness(self, eyes_count):
        self.eyes_detected_history.append(eyes_count)
        if len(self.eyes_detected_history) < 10:
            return False
        no_eyes = sum(1 for c in list(self.eyes_detected_history)[-10:] if c == 0)
        if no_eyes > 4:
            self.blink_counter += 1
            return True
        return False

    def analyze_attention(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        attention_data = {
            'timestamp':       time.time() - self.start_time,
            'gaze_direction':  None,
            'is_distracted':   False,
            'distraction_type': None,
            'confidence':      0.0,
        }
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(100, 100))

        if len(faces) > 0:
            self.no_face_frames = 0
            face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = face
            self.face_positions.append(face)

            roi_gray  = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            eyes      = self.detect_eyes_hybrid(roi_gray)

            attention_data['gaze_direction'] = self.detect_gaze_direction(eyes, roi_gray)

            reasons = []
            if self.is_looking_away(face, frame.shape):   reasons.append("posicao_rosto")
            if self.detect_head_movement(face):           reasons.append("movimento_cabeca")
            if self.detect_drowsiness(len(eyes)):         reasons.append("sonolencia")
            if len(eyes) == 0:                            reasons.append("olhos_nao_detectados")

            if reasons:
                attention_data['is_distracted']    = True
                attention_data['distraction_type'] = ", ".join(reasons)
                attention_data['confidence']       = min(0.9, 0.5 + len(reasons) * 0.15)
                self.distraction_frames += 1
            else:
                attention_data['confidence']       = 0.85
                self.distraction_frames            = 0

            self.gaze_history.append(attention_data['gaze_direction'])

            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)

            if attention_data['is_distracted'] and self.distraction_frames > 3:
                if not self.distraction_events or attention_data['timestamp'] - self.distraction_events[-1] > 2.0:
                    self.distraction_events.append(attention_data['timestamp'])
        else:
            self.no_face_frames += 1
            if self.no_face_frames > 5:
                attention_data['is_distracted']    = True
                attention_data['distraction_type'] = "sem_rosto"
                attention_data['confidence']       = 0.9
                self.distraction_frames           += 1
            else:
                attention_data['confidence'] = 0.3

        self.draw_gaze_info(frame, attention_data)
        return attention_data, frame

    def draw_gaze_info(self, frame, data):
        h, w = frame.shape[:2]
        if data['is_distracted']:
            color  = (0, 0, 200) if self.distraction_frames > 15 else (0, 100, 255)
            status = "MUITO DISTRAIDO!" if self.distraction_frames > 15 else "DISTRAIDO"
        else:
            color, status = (0, 255, 0), "FOCADO"

        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        if data.get('distraction_type'):
            cv2.putText(frame, f"Motivo: {data['distraction_type']}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
        if data['gaze_direction']:
            cv2.putText(frame, f"Olhar: {data['gaze_direction']}", (10, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Confianca: {data['confidence']:.0%}", (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Distracoes: {len(self.distraction_events)}", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if self.blink_counter > 5:
            cv2.putText(frame, "ALERTA: Possivel sonolencia!", (10, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    def start_input_monitoring(self):
        if not HAS_PYNPUT:
            logger.warning("pynput não instalado — monitoramento de inputs desativado.")
            return None, None

        def on_key_press(key):
            if self.is_monitoring:
                self.key_presses.append({'key': str(key), 'timestamp': time.time() - self.start_time})

        def on_click(x, y, button, pressed):
            if self.is_monitoring and pressed:
                self.mouse_clicks.append({'position': (x, y), 'button': str(button),
                                          'timestamp': time.time() - self.start_time})

        kb = keyboard.Listener(on_press=on_key_press)
        ms = mouse.Listener(on_click=on_click)
        kb.start(); ms.start()
        return kb, ms

    def analyze_inputs(self, window_size=1.0):
        if not self.start_time:
            return {'apm': 0, 'keys_per_sec': 0, 'clicks_per_sec': 0, 'spam_detected': False}
        t = time.time() - self.start_time
        rk = [k for k in self.key_presses  if t - k['timestamp'] < window_size]
        rc = [c for c in self.mouse_clicks if t - c['timestamp'] < window_size]
        apm = (len(rk) + len(rc)) * (60 / window_size)
        spam = len(rk) >= 3 and len(set(k['key'] for k in list(rk)[-3:])) == 1
        return {'apm': apm, 'keys_per_sec': len(rk) / window_size,
                'clicks_per_sec': len(rc) / window_size, 'spam_detected': spam}

    def run(self, duration=60):
        print("Iniciando monitoramento... Pressione 'q' para parar")
        self.is_monitoring = True
        self.start_time    = time.time()
        kb, ms = self.start_input_monitoring()
        try:
            while self.is_monitoring:
                ret, frame = self.cap.read()
                if not ret:
                    break
                attention_data, display_frame = self.analyze_attention(frame)
                input_data = self.analyze_inputs()
                cv2.putText(display_frame, f"APM: {input_data['apm']:.0f}",
                            (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                if input_data['spam_detected']:
                    cv2.putText(display_frame, "SPAM DETECTADO!", (10, 190),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.imshow('Player Monitor', display_frame)
                if time.time() - self.start_time > duration or cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.is_monitoring = False
            if kb: kb.stop()
            if ms: ms.stop()
            self.close_camera()
            cv2.destroyAllWindows()
            self.print_report()

    def print_report(self):
        total = time.time() - self.start_time if self.start_time else 0
        print(f"\n{'='*50}\nRELATÓRIO DE MONITORAMENTO\n{'='*50}")
        print(f"Duração: {total:.1f}s")
        print(f"Eventos de distração: {len(self.distraction_events)}")
        print(f"Total de teclas: {len(self.key_presses)}")
        print(f"Total de cliques: {len(self.mouse_clicks)}")
        if self.key_presses and total > 0:
            print(f"APM médio: {(len(self.key_presses)+len(self.mouse_clicks))*60/total:.0f}")
        if self.gaze_history:
            print("\nDistribuição do olhar:")
            counts = {}
            for g in self.gaze_history:
                counts[g] = counts.get(g, 0) + 1
            for direction, count in counts.items():
                print(f"  {direction}: {count/len(self.gaze_history)*100:.1f}%")


if __name__ == "__main__":
    monitor = PlayerMonitor()
    monitor.run(duration=999999)
