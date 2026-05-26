# -*- coding: utf-8 -*-
"""
Configurações globais para o Tetris Vision AI.
Define cores neon, dimensões de layout e constantes de detecção de gestos.
"""

# Configurações do Grid do Tetris
GRID_COLS = 10
GRID_ROWS = 20
CELL_SIZE = 32  # Tamanho de cada bloco em pixels (32 * 20 = 640px de altura)

# Configurações de Janela
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Cores Neon (RGB)
COLOR_BG = (11, 15, 25)          # Fundo escuro azulado
COLOR_PANEL_BG = (22, 28, 45)    # Painel de fundo dos dados
COLOR_GRID_BG = (17, 24, 39)     # Fundo do grid do Tetris
COLOR_BORDER = (51, 65, 85)      # Borda padrão cinza
COLOR_TEXT = (248, 250, 252)     # Texto principal claro
COLOR_MUTED = (148, 163, 184)    # Texto cinza secundário
COLOR_ACCENT = (56, 189, 248)    # Destaque azul céu

# Cores dos Tetrominos em estilo Neon Vibrante
TETROMINO_COLORS = {
    'I': (0, 240, 255),   # Ciano Neon
    'O': (255, 222, 0),   # Amarelo Neon
    'T': (189, 0, 255),   # Roxo Neon
    'S': (0, 255, 102),   # Verde Neon
    'Z': (255, 0, 60),    # Vermelho Neon
    'J': (0, 102, 255),   # Azul Neon
    'L': (255, 122, 0)    # Laranja Neon
}

# Configurações de Pontuação
SCORE_VALUES = {
    1: 100,   # 1 linha
    2: 300,   # 2 linhas
    3: 500,   # 3 linhas
    4: 800    # 4 linhas (Tetris!)
}

# Configurações da Câmera e IA (MediaPipe)
CAMERA_WIDTH = 560
CAMERA_HEIGHT = 420

# Zonas de Detecção (Porcentagem da largura/altura da tela do OpenCV)
# Zonas mais amplas para evitar falsos positivos e exigir movimento mais deliberado
ZONE_LEFT = 0.35   # Se X da mão for menor que 35% -> Esquerda
ZONE_RIGHT = 0.65  # Se X da mão for maior que 65% -> Direita
ZONE_DOWN = 0.72   # Se Y da mão for maior que 72% -> Descida rápida

# Cooldowns em milissegundos para evitar comandos duplicados
COOLDOWN_MOVE_HORIZONTAL = 180  # Tempo mínimo entre movimentos laterais
COOLDOWN_ROTATE = 400           # Tempo mínimo entre rotações (punho)
COOLDOWN_PAUSE = 1500           # Tempo mínimo para pausar/despausar (duas mãos)
