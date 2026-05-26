# -*- coding: utf-8 -*-
"""
Controlador de Visão Computacional para o Tetris Vision AI.
Utiliza OpenCV para captura da webcam e MediaPipe HandLandmarker para processamento de gestos.
Adaptado para a nova API mediapipe.tasks com RunningMode.VIDEO para maior precisão e estabilidade.
"""
import os
import cv2
import mediapipe as mp
import numpy as np
import pygame
import time
from collections import deque
from config import (
    CAMERA_WIDTH, CAMERA_HEIGHT,
    ZONE_LEFT, ZONE_RIGHT, ZONE_DOWN,
    COOLDOWN_MOVE_HORIZONTAL, COOLDOWN_ROTATE, COOLDOWN_PAUSE
)

# Caminho para o modelo de landmarking de mãos
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

# Conexões do esqueleto da mão (índices de landmarks do MediaPipe)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17), (5, 9), (9, 13), (0, 5),
]

# Janela de suavização de posição da mão (quantos frames usar para média móvel)
_SMOOTH_WINDOW = 5


class VisionController:
    def __init__(self):
        # Suavização: histórico de posições da mão principal (deques por mão)
        self._smooth_x = deque(maxlen=_SMOOTH_WINDOW)
        self._smooth_y = deque(maxlen=_SMOOTH_WINDOW)

        # Verifica se o modelo existe
        if not os.path.exists(_MODEL_PATH):
            print(f"[AVISO] Modelo '{_MODEL_PATH}' não encontrado. O jogo funcionará apenas pelo teclado.")
            self.camera_available = False
            self.landmarker = None
        else:
            BaseOptions = mp.tasks.BaseOptions
            HandLandmarker = mp.tasks.vision.HandLandmarker
            HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
            VisionRunningMode = mp.tasks.vision.RunningMode

            # Carrega o modelo como bytes para evitar problemas com caracteres especiais no caminho
            with open(_MODEL_PATH, "rb") as f:
                model_bytes = f.read()

            # Modo VIDEO: fornece timestamps reais, habilita rastreamento contínuo entre frames
            # muito mais estável e preciso do que IMAGE mode
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_buffer=model_bytes),
                running_mode=VisionRunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=0.75,
                min_hand_presence_confidence=0.75,
                min_tracking_confidence=0.65,
            )
            try:
                self.landmarker = HandLandmarker.create_from_options(options)
                self.camera_available = True
            except Exception as e:
                print(f"[AVISO] Falha ao criar HandLandmarker: {e}")
                self.landmarker = None
                self.camera_available = False

        if self.camera_available:
            # Inicializa a câmera com alta resolução para melhor detecção
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("[AVISO] Câmera não pôde ser aberta. O jogo funcionará apenas pelo teclado.")
                self.camera_available = False
            else:
                # Pedir resolução máxima para a câmera (melhor qualidade de tracking)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Estados dos Cooldowns (em milissegundos usando pygame.time.get_ticks())
        self.last_move_time = 0
        self.last_rotate_time = 0
        self.last_pause_time = 0

        # Sistema de key-repeat para movimentos horizontais:
        # 1º disparo: imediato ao entrar na zona
        # 2º+ disparo: após MOVE_REPEAT_DELAY ms
        # Repetição contínua: a cada MOVE_REPEAT_RATE ms
        self._current_h_zone = None   # 'LEFT', 'RIGHT' ou None
        self._move_repeat_started = False
        self._move_first_time = 0
        MOVE_REPEAT_DELAY = 500   # ms até começar a repetição automática
        MOVE_REPEAT_RATE  = 280   # ms entre repetições após o delay
        self._MOVE_REPEAT_DELAY = MOVE_REPEAT_DELAY
        self._MOVE_REPEAT_RATE  = MOVE_REPEAT_RATE

        # Debounce do punho fechado: exige que a mão se mantenha fechada
        # por pelo menos _FIST_MIN_HOLD ms antes de disparar ROTATE.
        # Evita falsos positivos ao coçar o nariz, ajustar óculos, etc.
        self._fist_start_time = None    # quando o punho foi detectado pela 1ª vez
        self._FIST_MIN_HOLD = 220       # ms que a mão precisa ficar fechada

        # Debounce do gesto de pausa (2 mãos):
        # Exige que as duas mãos sejam detectadas como válidas por pelo menos
        # _PAUSE_MIN_HOLD ms antes de pausar. Evita pausas acidentais ao coçar o rosto.
        self._pause_hands_start = None  # quando as 2 mãos foram detectadas pela 1ª vez
        self._PAUSE_MIN_HOLD = 700      # ms de 2 mãos continuías para pausar

        # Estado atual do gesto detectado para feedback visual
        self.active_gesture = "Nenhum"

        # Frame processado mais recente para renderização
        self.latest_frame = None

        # Timestamp em microsegundos para o modo VIDEO
        self._timestamp_us = 0

    def get_actions(self):
        """
        Captura um frame, processa gestos com IA e retorna ações do jogo.
        Usa modo VIDEO para rastreamento contínuo mais estável.
        """
        actions = []
        if not self.camera_available:
            return actions

        ret, frame = self.cap.read()
        if not ret:
            return actions

        # Espelhar imagem horizontalmente (mais intuitivo para o jogador)
        frame = cv2.flip(frame, 1)

        # Redimensionar para o tamanho do painel da câmera para exibição
        display_frame = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))

        # Usar o frame em alta resolução para detecção (mais preciso)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Avançar timestamp (necessário para RunningMode.VIDEO)
        self._timestamp_us += 33333  # ~30fps em microsegundos

        results = self.landmarker.detect_for_video(mp_image, self._timestamp_us)

        current_time = pygame.time.get_ticks()
        self.active_gesture = "Nenhum"

        # Desenhar linhas das zonas de controle no display_frame para feedback visual
        self.draw_overlay_zones(display_frame)

        hand_landmarks_list = results.hand_landmarks

        # Filtrar: manter apenas detecções com proporções plausíveis de mão real
        # (elimina rostos, cabeças e objetos falsamente detectados como mãos)
        hand_landmarks_list = [
            lm for lm in hand_landmarks_list if self._is_valid_hand(lm)
        ]

        if hand_landmarks_list:
            num_hands = len(hand_landmarks_list)

            # Gesto de Pausa: 2 Mãos simultaneamente válidas + debounce
            if num_hands >= 2:
                if self._pause_hands_start is None:
                    self._pause_hands_start = current_time

                pause_held = current_time - self._pause_hands_start
                pause_confirmed = pause_held >= self._PAUSE_MIN_HOLD

                if pause_confirmed:
                    self.active_gesture = "Duas Mãos (PAUSAR)"
                    if current_time - self.last_pause_time > COOLDOWN_PAUSE:
                        actions.append('PAUSE')
                        self.last_pause_time = current_time
                else:
                    pct = int(pause_held / self._PAUSE_MIN_HOLD * 100)
                    self.active_gesture = f"Segure para pausar... {pct}%"

                # Desenhar ambas as mãos
                for hand_lm in hand_landmarks_list:
                    self._draw_hand_landmarks(display_frame, hand_lm)
            else:
                # Menos de 2 mãos válidas — resetar debounce do pause
                self._pause_hands_start = None
                # Apenas 1 mão
                hand_landmarks = hand_landmarks_list[0]

                # Desenhar esqueleto no display
                self._draw_hand_landmarks(display_frame, hand_landmarks)

                # Posição suavizada: média móvel das últimas N posições
                raw_x = hand_landmarks[9].x
                raw_y = hand_landmarks[9].y
                self._smooth_x.append(raw_x)
                self._smooth_y.append(raw_y)
                center_x = sum(self._smooth_x) / len(self._smooth_x)
                center_y = sum(self._smooth_y) / len(self._smooth_y)

                # Classificar abertura/fechamento da mão
                is_open = self.is_hand_open(hand_landmarks)

                if not is_open:
                    # Debounce: só registra punho se mantiver fechado por _FIST_MIN_HOLD ms
                    if self._fist_start_time is None:
                        self._fist_start_time = current_time  # começa cronometrar

                    fist_duration = current_time - self._fist_start_time
                    fist_confirmed = fist_duration >= self._FIST_MIN_HOLD

                    if fist_confirmed:
                        self.active_gesture = "Punho Fechado (ROTACIONAR)"
                    else:
                        # Ainda dentro do debounce — mostra feedback mas não dispara
                        self.active_gesture = f"Fechando mão... ({fist_duration}ms)"

                    if fist_confirmed and current_time - self.last_rotate_time > COOLDOWN_ROTATE:
                        actions.append('ROTATE')
                        self.last_rotate_time = current_time

                    # Sai de qualquer zona lateral ao fechar a mão
                    self._current_h_zone = None
                    self._move_repeat_started = False
                else:
                    # Mão aberta — resetar cronometro do punho
                    self._fist_start_time = None
                    if center_x < ZONE_LEFT:
                        new_zone = 'LEFT'
                    elif center_x > ZONE_RIGHT:
                        new_zone = 'RIGHT'
                    else:
                        new_zone = None

                    if new_zone in ('LEFT', 'RIGHT'):
                        self.active_gesture = (
                            "Mão Esquerda (MOVER ESQ)" if new_zone == 'LEFT'
                            else "Mão Direita (MOVER DIR)"
                        )
                        if new_zone != self._current_h_zone:
                            # Entrou numa nova zona: disparo imediato + resetar repeat
                            actions.append(new_zone)
                            self._current_h_zone = new_zone
                            self._move_repeat_started = False
                            self._move_first_time = current_time
                        else:
                            # Permanece na mesma zona: lógica de key-repeat
                            time_in_zone = current_time - self._move_first_time
                            if not self._move_repeat_started:
                                # Aguarda o delay antes de começar a repetir
                                if time_in_zone >= self._MOVE_REPEAT_DELAY:
                                    self._move_repeat_started = True
                                    self.last_move_time = current_time
                                    actions.append(new_zone)
                            else:
                                # Repetição contínua na taxa definida
                                if current_time - self.last_move_time >= self._MOVE_REPEAT_RATE:
                                    actions.append(new_zone)
                                    self.last_move_time = current_time
                    else:
                        # Mão saiu das zonas laterais
                        self._current_h_zone = None
                        self._move_repeat_started = False

                        if center_y > ZONE_DOWN:
                            self.active_gesture = "Mão Baixa (ACELERAR QUEDA)"
                            actions.append('DOWN')
                        else:
                            self.active_gesture = "Mão Aberta (Neutro)"

            # Desenhar indicador de posição suavizada no display
            if num_hands == 1 and self._smooth_x:
                sx = int(sum(self._smooth_x) / len(self._smooth_x) * CAMERA_WIDTH)
                sy = int(sum(self._smooth_y) / len(self._smooth_y) * CAMERA_HEIGHT)
                cv2.circle(display_frame, (sx, sy), 10, (255, 255, 0), -1)
                cv2.circle(display_frame, (sx, sy), 12, (255, 200, 0), 2)
        else:
            # Sem mão detectada: limpar tudo
            self._smooth_x.clear()
            self._smooth_y.clear()
            self._fist_start_time = None
            self._current_h_zone = None
            self._move_repeat_started = False
            self._pause_hands_start = None

        self.latest_frame = display_frame
        return actions

    def _is_valid_hand(self, landmarks):
        """
        Verifica se os landmarks detectados formam uma mão geometricamente plausível.
        Filtra falsos positivos causados por rostos, cabeças e outros objetos.

        Critérios:
        - Distância pulso (0) -> ponta do dedo médio (12) >= 10% da largura do frame
        - Largura da palma (base indicador 5 -> base mínimo 17) >= 4% do frame
        - Razão comprimento/largura entre 1.0 e 5.0
        """
        import math
        wrist = landmarks[0]
        mid_tip = landmarks[12]      # ponta do dedo médio
        idx_knuckle = landmarks[5]   # base do indicador
        pin_knuckle = landmarks[17]  # base do mínimo

        # Comprimento da mão (pulso até ponta do médio)
        hand_len = math.hypot(mid_tip.x - wrist.x, mid_tip.y - wrist.y)

        # Largura da palma (base indicador até base mínimo)
        palm_w = math.hypot(pin_knuckle.x - idx_knuckle.x, pin_knuckle.y - idx_knuckle.y)

        # Tamanho mínimo absoluto: mão deve ter pelo menos 10% do frame de comprimento
        if hand_len < 0.10:
            return False

        # Largura mínima da palma: pelo menos 4% do frame
        if palm_w < 0.04:
            return False

        # Razão comprimento/largura: mão real fica entre 1.0 e 5.0
        ratio = hand_len / max(palm_w, 0.001)
        if ratio < 1.0 or ratio > 5.0:
            return False

        return True

    def is_hand_open(self, landmarks):
        """
        Retorna True se a mão estiver claramente aberta (3+ dedos estendidos com margem).
        Retorna False (punho) apenas se 3+ dedos estiverem claramente dobrados.
        A margem mínima de y evita que dedos levemente curvados (ao coçar o nariz)
        sejam confundidos com punho.
        """
        # Margem mínima: ponta do dedo precisa estar acima da articulacão por mais de 3% da frame
        _MIN_GAP = 0.03

        open_fingers = 0
        # Indicador: 8 vs 6 | Médio: 12 vs 10 | Anelar: 16 vs 14 | Mínimo: 20 vs 18
        if landmarks[6].y - landmarks[8].y > _MIN_GAP: open_fingers += 1   # ponta acima da junta
        if landmarks[10].y - landmarks[12].y > _MIN_GAP: open_fingers += 1
        if landmarks[14].y - landmarks[16].y > _MIN_GAP: open_fingers += 1
        if landmarks[18].y - landmarks[20].y > _MIN_GAP: open_fingers += 1

        # Punho confirmado: 3 ou mais dedos claramente dobrados
        # Aberto: 3 ou mais dedos claramente estendidos
        # Ambiguo (1-2 dedos): sem ação (retorna True = "não é punho")
        return open_fingers >= 2

    def _draw_hand_landmarks(self, frame, landmarks):
        """Desenha o esqueleto da mão no frame OpenCV com estilo neon."""
        h, w, _ = frame.shape
        pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

        # Conexões (ossos) com cor ciano neon
        for start_idx, end_idx in HAND_CONNECTIONS:
            if start_idx < len(pts) and end_idx < len(pts):
                cv2.line(frame, pts[start_idx], pts[end_idx], (0, 220, 255), 2, cv2.LINE_AA)

        # Articulações
        for pt in pts:
            cv2.circle(frame, pt, 5, (255, 255, 255), -1)
            cv2.circle(frame, pt, 5, (0, 180, 255), 2)

    def draw_overlay_zones(self, frame):
        """Desenha guias de zonas de controle com transparência semi-neon."""
        h, w, _ = frame.shape

        # Criar overlay transparente para preenchimento das zonas
        overlay = frame.copy()

        left_x = int(w * ZONE_LEFT)
        right_x = int(w * ZONE_RIGHT)
        down_y = int(h * ZONE_DOWN)

        # Zonas coloridas com transparência
        cv2.rectangle(overlay, (0, 0), (left_x, h), (180, 0, 80), -1)           # Zona esquerda (rosa)
        cv2.rectangle(overlay, (right_x, 0), (w, h), (180, 0, 80), -1)          # Zona direita (rosa)
        cv2.rectangle(overlay, (left_x, down_y), (right_x, h), (0, 150, 60), -1) # Zona baixo (verde)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        # Bordas nítidas das zonas
        cv2.line(frame, (left_x, 0), (left_x, h), (255, 0, 96), 2, cv2.LINE_AA)
        cv2.line(frame, (right_x, 0), (right_x, h), (255, 0, 96), 2, cv2.LINE_AA)
        cv2.line(frame, (0, down_y), (w, down_y), (0, 255, 102), 2, cv2.LINE_AA)

        # Labels das zonas
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, "ESQ", (10, 30), font, 0.8, (255, 80, 140), 2, cv2.LINE_AA)
        cv2.putText(frame, "DIR", (right_x + 8, 30), font, 0.8, (255, 80, 140), 2, cv2.LINE_AA)
        cv2.putText(frame, "QUEDA RAPIDA", (left_x + 8, down_y - 10), font, 0.65, (0, 255, 102), 2, cv2.LINE_AA)

        # Zona central neutra - label discreto
        cv2.putText(frame, "NEUTRO", (left_x + (right_x - left_x) // 2 - 40, 30), font, 0.65, (180, 220, 255), 1, cv2.LINE_AA)

    def get_pygame_surface(self):
        """Converte o último frame processado do OpenCV em uma superfície Pygame."""
        if not self.camera_available or self.latest_frame is None:
            surf = pygame.Surface((CAMERA_WIDTH, CAMERA_HEIGHT))
            surf.fill((20, 25, 35))
            font = pygame.font.SysFont("Arial", 18)
            text = font.render("CÂMERA INDISPONÍVEL", True, (239, 68, 68))
            text_rect = text.get_rect(center=(CAMERA_WIDTH // 2, CAMERA_HEIGHT // 2))
            surf.blit(text, text_rect)
            return surf

        rgb_image = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
        surface = pygame.surfarray.make_surface(cv2.transpose(rgb_image))
        return surface

    def release(self):
        """Libera os recursos da câmera e do landmarker."""
        if hasattr(self, 'cap') and self.cap is not None and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None
        self.camera_available = False
