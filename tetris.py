# -*- coding: utf-8 -*-
"""
Motor de Jogo do Tetris.
Contém a lógica de peças, movimentação, colisão, pontuação e níveis.
"""
import random
from config import GRID_ROWS, GRID_COLS, SCORE_VALUES

# Definição matricial das 7 peças clássicas (Tetrominos)
# As matrizes são quadradas para facilitar a rotação matemática simples
SHAPES = {
    'I': [
        [0, 0, 0, 0],
        [1, 1, 1, 1],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ],
    'O': [
        [1, 1],
        [1, 1]
    ],
    'T': [
        [0, 1, 0],
        [1, 1, 1],
        [0, 0, 0]
    ],
    'S': [
        [0, 1, 1],
        [1, 1, 0],
        [0, 0, 0]
    ],
    'Z': [
        [1, 1, 0],
        [0, 1, 1],
        [0, 0, 0]
    ],
    'J': [
        [1, 0, 0],
        [1, 1, 1],
        [0, 0, 0]
    ],
    'L': [
        [0, 0, 1],
        [1, 1, 1],
        [0, 0, 0]
    ]
}

# Pré-gera os 4 estados de rotação de cada peça por transformação matemática (90° CW)
def _gen_rotations(matrix):
    rotations = []
    cur = [row[:] for row in matrix]
    for _ in range(4):
        rotations.append(cur)
        cur = [list(row) for row in zip(*cur[::-1])]  # 90° horário
    return rotations

ROTATION_CYCLES = {name: _gen_rotations(mat) for name, mat in SHAPES.items()}

class TetrisGame:
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Inicializa ou reinicia o estado completo do jogo."""
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.started = False
        
        # Fila de peças
        self.current_piece = None
        self.next_piece = self.new_piece()
        self.spawn_piece()
        
    def new_piece(self):
        """Escolhe uma nova peça aleatória com seu tipo e matriz."""
        shape_name = random.choice(list(SHAPES.keys()))
        return {
            'type': shape_name,
            'matrix': [row[:] for row in ROTATION_CYCLES[shape_name][0]],
            'rotation': 0,  # índice do estado de rotação atual (0-3)
            'x': 0,
            'y': 0
        }
        
    def spawn_piece(self):
        """Transfere a próxima peça para a ativa e gera outra."""
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()
        
        # Centralizar a peça horizontalmente no topo
        # Largura da matriz da peça
        matrix_width = len(self.current_piece['matrix'][0])
        self.current_piece['x'] = (GRID_COLS - matrix_width) // 2
        self.current_piece['y'] = 0
        
        # Se ao nascer já colidir, é Game Over imediato
        if self.check_collision(self.current_piece['matrix'], self.current_piece['x'], self.current_piece['y']):
            self.game_over = True

    def check_collision(self, matrix, offset_x, offset_y):
        """
        Retorna True se a peça colidir com as bordas do tabuleiro
        ou com blocos já travados.
        """
        for r, row in enumerate(matrix):
            for c, cell in enumerate(row):
                if cell:  # Se existe um bloco nessa posição da peça
                    grid_x = offset_x + c
                    grid_y = offset_y + r
                    
                    # Verificar limites das paredes laterais e do fundo
                    if grid_x < 0 or grid_x >= GRID_COLS or grid_y >= GRID_ROWS:
                        return True
                        
                    # Verificar colisão com peças travadas (grid_y < 0 é válido no topo)
                    if grid_y >= 0 and self.grid[grid_y][grid_x] is not None:
                        return True
        return False

    def move_left(self):
        """Move a peça atual uma unidade para a esquerda se possível."""
        if self.game_over or self.paused:
            return False
        new_x = self.current_piece['x'] - 1
        if not self.check_collision(self.current_piece['matrix'], new_x, self.current_piece['y']):
            self.current_piece['x'] = new_x
            return True
        return False

    def move_right(self):
        """Move a peça atual uma unidade para a direita se possível."""
        if self.game_over or self.paused:
            return False
        new_x = self.current_piece['x'] + 1
        if not self.check_collision(self.current_piece['matrix'], new_x, self.current_piece['y']):
            self.current_piece['x'] = new_x
            return True
        return False

    def rotate(self):
        """Rotaciona a peça atual em 90 graus no sentido horário usando estados pré-computados."""
        if self.game_over or self.paused:
            return False

        piece_type = self.current_piece['type']
        current_rot = self.current_piece['rotation']
        next_rot = (current_rot + 1) % 4
        new_matrix = [row[:] for row in ROTATION_CYCLES[piece_type][next_rot]]

        # Wall Kick: tenta posicionar a peça com pequenos desvios laterais e verticais
        offsets_to_try = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
        for dx, dy in offsets_to_try:
            test_x = self.current_piece['x'] + dx
            test_y = self.current_piece['y'] + dy
            if not self.check_collision(new_matrix, test_x, test_y):
                self.current_piece['matrix'] = new_matrix
                self.current_piece['rotation'] = next_rot
                self.current_piece['x'] = test_x
                self.current_piece['y'] = test_y
                return True
        return False

    def drop(self):
        """
        Desce a peça ativa uma posição.
        Retorna False se colidir e precisar ser travada.
        """
        if self.game_over or self.paused:
            return False
            
        new_y = self.current_piece['y'] + 1
        if not self.check_collision(self.current_piece['matrix'], self.current_piece['x'], new_y):
            self.current_piece['y'] = new_y
            return True
        else:
            self.lock_piece()
            return False

    def hard_drop(self):
        """Despenca a peça até o fundo imediatamente e a trava."""
        if self.game_over or self.paused:
            return
        
        while not self.check_collision(self.current_piece['matrix'], self.current_piece['x'], self.current_piece['y'] + 1):
            self.current_piece['y'] += 1
            
        self.lock_piece()

    def lock_piece(self):
        """Trava a peça atual no tabuleiro, limpa linhas e spawna a próxima."""
        piece = self.current_piece
        for r, row in enumerate(piece['matrix']):
            for c, cell in enumerate(row):
                if cell:
                    grid_y = piece['y'] + r
                    grid_x = piece['x'] + c
                    # Apenas desenha se estiver dentro dos limites visíveis da tela
                    if 0 <= grid_y < GRID_ROWS and 0 <= grid_x < GRID_COLS:
                        self.grid[grid_y][grid_x] = piece['type']
                        
        self.clear_lines()
        self.spawn_piece()

    def clear_lines(self):
        """Remove linhas completas, atualiza pontuação, nível e linhas totais."""
        lines_to_clear = []
        for r in range(GRID_ROWS):
            if all(cell is not None for cell in self.grid[r]):
                lines_to_clear.append(r)
                
        num_cleared = len(lines_to_clear)
        if num_cleared > 0:
            # Remover as linhas identificadas
            for r in lines_to_clear:
                del self.grid[r]
                # Inserir uma linha vazia no topo para compensar
                self.grid.insert(0, [None for _ in range(GRID_COLS)])
                
            # Atualizar pontuação e estatísticas
            self.lines += num_cleared
            self.score += SCORE_VALUES.get(num_cleared, 800) * self.level
            
            # Subir de nível a cada 10 linhas eliminadas
            self.level = (self.lines // 10) + 1

    def toggle_pause(self):
        """Alterna o estado de pausa do jogo."""
        if not self.game_over and self.started:
            self.paused = not self.paused
            
    def get_drop_speed(self):
        """Calcula o intervalo de descida automática em milissegundos com base no nível."""
        # Nível 1: 1000ms, Nível 2: 850ms, Nível 3: 700ms... até um limite rápido
        speed = 1000 - (self.level - 1) * 100
        return max(150, speed)  # Nunca mais rápido do que 150ms por queda
