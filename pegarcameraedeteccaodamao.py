# -*- coding: utf-8 -*-
"""
Script Independente: Pegar Câmera e Detecção de Mão 🖐️🤖
Demonstração da detecção de mão e rastreamento da ponta do dedo indicador
usando OpenCV e a nova API mp.tasks do MediaPipe (compatível com Python 3.14).
"""

import os
import cv2
import mediapipe as mp
import time

def main():
    # Caminho do modelo local
    model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
    if not os.path.exists(model_path):
        print(f"Erro: O arquivo de modelo '{model_path}' não foi encontrado!")
        print("Certifique-se de que o arquivo 'hand_landmarker.task' está no mesmo diretório.")
        return

    # Inicializa a captura de vídeo
    print("Inicializando webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro: Não foi possível acessar a webcam!")
        return

    # Configura a resolução da câmera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print("Webcam pronta. Inicializando o HandLandmarker do MediaPipe...")
    print("Pressione 'ESC' na janela de vídeo para sair.")

    # Lê os bytes do modelo
    with open(model_path, "rb") as f:
        model_bytes = f.read()

    # Configurações do MediaPipe Tasks
    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_buffer=model_bytes),
        running_mode=VisionRunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    timestamp_ms = 0

    with HandLandmarker.create_from_options(options) as landmarker:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("Aviso: Falha ao capturar frame. Ignorando...")
                time.sleep(0.01)
                continue

            # Espelha o frame horizontalmente
            frame = cv2.flip(frame, 1)
            h, w, c = frame.shape

            # Converte de BGR para RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Incrementa o timestamp para o modo VIDEO
            timestamp_ms += 33  # ~30 FPS

            # Executa a detecção
            results = landmarker.detect_for_video(mp_image, timestamp_ms)

            # Se detectar mãos
            if results.hand_landmarks:
                for hand_landmarks in results.hand_landmarks:
                    # Desenha as articulações (landmarks) e conexões
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(frame, (cx, cy), 4, (0, 220, 255), -1, cv2.LINE_AA)
                    
                    # Conexões do esqueleto da mão para desenhar linhas
                    connections = [
                        (0, 1), (1, 2), (2, 3), (3, 4),
                        (0, 5), (5, 6), (6, 7), (7, 8),
                        (5, 9), (9, 10), (10, 11), (11, 12),
                        (9, 13), (13, 14), (14, 15), (15, 16),
                        (13, 17), (17, 18), (18, 19), (19, 20),
                        (0, 17), (5, 9), (9, 13)
                    ]
                    for start, end in connections:
                        pt1 = (int(hand_landmarks[start].x * w), int(hand_landmarks[start].y * h))
                        pt2 = (int(hand_landmarks[end].x * w), int(hand_landmarks[end].y * h))
                        cv2.line(frame, pt1, pt2, (0, 180, 255), 1, cv2.LINE_AA)

                    # Pega a ponta do indicador (Landmark 8)
                    index_tip = hand_landmarks[8]
                    cx_tip, cy_tip = int(index_tip.x * w), int(index_tip.y * h)

                    # Destaque neon na ponta do indicador
                    cv2.circle(frame, (cx_tip, cy_tip), 12, (0, 255, 0), -1, cv2.LINE_AA)
                    cv2.circle(frame, (cx_tip, cy_tip), 15, (255, 255, 255), 2, cv2.LINE_AA)

                    # Exibe a posição na tela
                    cv2.putText(
                        frame,
                        f"Indicador: {cx_tip}, {cy_tip}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2,
                        cv2.LINE_AA
                    )

            # Mostra o feed de vídeo processado
            cv2.imshow('Deteccao de Mao - Teste Tasks', frame)

            # Pressione ESC para fechar a janela
            if cv2.waitKey(5) & 0xFF == 27:
                break

    # Libera os recursos
    cap.release()
    cv2.destroyAllWindows()
    print("Recursos liberados. Concluído!")

if __name__ == '__main__':
    main()