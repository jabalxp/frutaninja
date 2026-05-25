# -*- coding: utf-8 -*-
"""
Interface Gráfica e Loop Principal do Tetris Vision AI.
Integra a lógica de jogo (toetris.py) e o detector de câmera (vision_controller.py)
em um visual escuro moderno com detalhes neon.
"""
import sys
import pygame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE, GRID_COLS, GRID_ROWS, FPS,
    COLOR_BG, COLOR_PANEL_BG, COLOR_GRID_BG, COLOR_BORDER, COLOR_TEXT,
    COLOR_MUTED, COLOR_ACCENT, TETROMINO_COLORS, CAMERA_WIDTH, CAMERA_HEIGHT
)
from tetris import TetrisGame
from vision_controller import VisionController

# Inicializar Pygame e subsistemas
pygame.init()
pygame.font.init()
pygame.mixer.init() # Para o caso do usuário querer estender com efeitos sonoros

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Tetris Vision AI - Controle por Gestos")
clock = pygame.time.Clock()

# Tentar carregar fontes elegantes disponíveis no Windows, senão usa a padrão
def get_font(size, bold=False):
    font_names = ["Segoe UI", "Century Gothic", "Trebuchet MS", "Arial"]
    for name in font_names:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            continue
    return pygame.font.Font(None, size)

FONT_TITLE = get_font(32, bold=True)
FONT_SUBTITLE = get_font(20, bold=True)
FONT_LABEL = get_font(16, bold=False)
FONT_VALUE = get_font(24, bold=True)
FONT_SMALL = get_font(12, bold=False)
FONT_HUGE = get_font(48, bold=True)

# Instanciar motores de jogo e IA
game = TetrisGame()
vision = VisionController()

# Layout principal:
# [Painel Stats 250px] [Board 320px] [Painel Câmera 590px] = 1160px + margens
BOARD_X = 270
BOARD_Y = 30
CAM_PANEL_X = 610

# Retângulos dos botões para interações do mouse
BTN_PLAY = pygame.Rect(SCREEN_WIDTH // 2 - 130, 490, 260, 55)
BTN_RESTART = pygame.Rect(BOARD_X + (GRID_COLS * CELL_SIZE) // 2 - 100, 440, 200, 50)

def draw_neon_box(surface, rect, color, border_width=2, glow_radius=4):
    """Desenha uma caixa com estilo neon brilhante e bordas arredondadas."""
    # Desenhar o brilho externo (múltiplas passagens com alpha)
    for i in range(glow_radius, 0, -1):
        glow_color = (*color, int(100 / (i * 1.5)))
        glow_surf = pygame.Surface((rect.width + i*2, rect.height + i*2), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, glow_color, (0, 0, rect.width + i*2, rect.height + i*2), border_width, border_radius=4)
        surface.blit(glow_surf, (rect.x - i, rect.y - i))
    
    # Desenhar a borda sólida principal
    pygame.draw.rect(surface, color, rect, border_width, border_radius=4)

def draw_block(surface, x, y, color):
    """Desenha um bloco individual do Tetris com estilo neon tridimensional."""
    rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
    # Caixa principal com cor neon
    pygame.draw.rect(surface, color, rect, border_radius=3)
    
    # Detalhe brilhante interno
    inner_color = (
        min(255, color[0] + 50),
        min(255, color[1] + 50),
        min(255, color[2] + 50)
    )
    inner_rect = pygame.Rect(x + 3, y + 3, CELL_SIZE - 6, CELL_SIZE - 6)
    pygame.draw.rect(surface, inner_color, inner_rect, border_radius=2)

def draw_board(surface, board_x, board_y):
    """Desenha a grade e as peças ativas e travadas no tabuleiro."""
    # Fundo do grid do Tetris
    board_rect = pygame.Rect(board_x, board_y, GRID_COLS * CELL_SIZE, GRID_ROWS * CELL_SIZE)
    pygame.draw.rect(surface, COLOR_GRID_BG, board_rect)
    
    # Linhas da grade interna (subtis)
    for c in range(GRID_COLS + 1):
        x = board_x + c * CELL_SIZE
        pygame.draw.line(surface, (28, 35, 50), (x, board_y), (x, board_y + GRID_ROWS * CELL_SIZE), 1)
    for r in range(GRID_ROWS + 1):
        y = board_y + r * CELL_SIZE
        pygame.draw.line(surface, (28, 35, 50), (board_x, y), (board_x + GRID_COLS * CELL_SIZE, y), 1)
        
    # Desenhar peças travadas no tabuleiro
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            cell_type = game.grid[r][c]
            if cell_type:
                color = TETROMINO_COLORS.get(cell_type, COLOR_ACCENT)
                draw_block(surface, board_x + c * CELL_SIZE, board_y + r * CELL_SIZE, color)
                
    # Desenhar a peça ativa em queda
    if game.current_piece and not game.game_over:
        piece = game.current_piece
        color = TETROMINO_COLORS.get(piece['type'], COLOR_ACCENT)
        for r, row in enumerate(piece['matrix']):
            for c, cell in enumerate(row):
                if cell:
                    grid_x = piece['x'] + c
                    grid_y = piece['y'] + r
                    if 0 <= grid_y < GRID_ROWS and 0 <= grid_x < GRID_COLS:
                        draw_block(surface, board_x + grid_x * CELL_SIZE, board_y + grid_y * CELL_SIZE, color)

    # Borda externa do tabuleiro com neon ciano suave
    draw_neon_box(surface, board_rect, COLOR_BORDER, 2)

def draw_next_piece(surface, x, y, size=150):
    """Desenha a caixa de pré-visualização da próxima peça."""
    panel_rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=4)
    draw_neon_box(surface, panel_rect, COLOR_BORDER, 2)
    
    # Cabeçalho da caixa
    title_text = FONT_LABEL.render("PRÓXIMA PEÇA", True, COLOR_MUTED)
    surface.blit(title_text, (x + 10, y + 10))
    
    # Desenhar a peça centralizada no meio da caixa
    if game.next_piece:
        piece = game.next_piece
        color = TETROMINO_COLORS.get(piece['type'], COLOR_ACCENT)
        matrix = piece['matrix']
        
        # Calcular dimensões reais da peça para centralizar perfeitamente
        max_r, max_c = len(matrix), len(matrix[0])
        block_w = 20  # Bloco menor na visualização
        
        # Calcular deslocamento de centralização
        offset_x = x + (size - max_c * block_w) // 2
        offset_y = y + (size - max_r * block_w) // 2 + 10
        
        for r, row in enumerate(matrix):
            for c, cell in enumerate(row):
                if cell:
                    bx = offset_x + c * block_w
                    by = offset_y + r * block_w
                    pygame.draw.rect(surface, color, (bx, by, block_w - 2, block_w - 2), border_radius=2)

def draw_stats_panel(surface, x, y, width=250):
    """Painel lateral esquerdo com pontuação, nível e linhas."""
    panel_rect = pygame.Rect(x, y, width, SCREEN_HEIGHT - 60)
    pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=4)
    draw_neon_box(surface, panel_rect, COLOR_BORDER, 2)
    
    # Título do Jogo com efeito neon
    title_shadow = FONT_TITLE.render("TETRIS AI", True, (244, 63, 94))
    title_main = FONT_TITLE.render("TETRIS AI", True, (255, 0, 96))
    surface.blit(title_shadow, (x + 22, y + 22))
    surface.blit(title_main, (x + 20, y + 20))
    
    sub_title = FONT_SMALL.render("CONTROLE POR CÂMERA", True, COLOR_ACCENT)
    surface.blit(sub_title, (x + 20, y + 60))
    
    # Divisor
    pygame.draw.line(surface, COLOR_BORDER, (x + 20, y + 80), (x + width - 20, y + 80), 1)
    
    # Estatísticas
    stats = [
        ("PONTUAÇÃO", str(game.score), (56, 189, 248)),       # Azul Céu
        ("NÍVEL ATUAL", str(game.level), (192, 132, 252)),     # Roxo Neon
        ("LINHAS LIMPAS", str(game.lines), (74, 222, 128))     # Verde Neon
    ]
    
    curr_y = y + 100
    for label, val, color in stats:
        lbl_surf = FONT_LABEL.render(label, True, COLOR_MUTED)
        val_surf = FONT_VALUE.render(val, True, color)
        
        surface.blit(lbl_surf, (x + 20, curr_y))
        surface.blit(val_surf, (x + 20, curr_y + 22))
        curr_y += 70
        
    # Instruções rápidas na parte inferior do painel esquerdo
    pygame.draw.line(surface, COLOR_BORDER, (x + 20, curr_y), (x + width - 20, curr_y), 1)
    
    curr_y += 15
    lbl_instru = FONT_SUBTITLE.render("TECLADO (TESTES)", True, COLOR_MUTED)
    surface.blit(lbl_instru, (x + 20, curr_y))
    
    instrucoes = [
        "Seta Esquerda/Direita: Mover",
        "Seta Cima: Rotacionar peça",
        "Seta Baixo: Acelerar descida",
        "Espaço: Queda Rápida (Drop)",
        "Tecla P: Pausar Jogo",
        "Tecla R: Reiniciar Jogo"
    ]
    
    curr_y += 30
    for inst in instrucoes:
        inst_surf = FONT_SMALL.render(inst, True, COLOR_MUTED)
        surface.blit(inst_surf, (x + 20, curr_y))
        curr_y += 20

def draw_camera_panel(surface, x, y):
    """Painel lateral direito com câmera em tela cheia e status do gesto."""
    panel_w = SCREEN_WIDTH - x - 15
    panel_rect = pygame.Rect(x, y, panel_w, SCREEN_HEIGHT - y - 15)
    pygame.draw.rect(surface, COLOR_PANEL_BG, panel_rect, border_radius=6)
    draw_neon_box(surface, panel_rect, COLOR_BORDER, 2)

    # Título do Painel
    lbl_cam = FONT_SUBTITLE.render("VISÃO COMPUTACIONAL  [ IA ]", True, COLOR_ACCENT)
    surface.blit(lbl_cam, (x + 15, y + 14))

    # Câmera ocupa toda a largura disponível
    cam_x = x + 15
    cam_y = y + 48
    cam_rect = pygame.Rect(cam_x, cam_y, CAMERA_WIDTH, CAMERA_HEIGHT)
    cam_surf = vision.get_pygame_surface()
    surface.blit(cam_surf, cam_rect)
    draw_neon_box(surface, cam_rect, (0, 255, 102), 2)  # Borda verde neon

    # Status do gesto logo abaixo da câmera
    gesture_y = cam_y + CAMERA_HEIGHT + 12
    gest_label = FONT_LABEL.render("GESTO:", True, COLOR_MUTED)
    surface.blit(gest_label, (cam_x, gesture_y))

    gest_color = (0, 255, 102)
    if "Nenhum" in vision.active_gesture:
        gest_color = COLOR_MUTED
    elif "ROTACIONAR" in vision.active_gesture:
        gest_color = (189, 0, 255)
    elif "PAUSAR" in vision.active_gesture:
        gest_color = (255, 0, 60)
    elif "ACELERAR" in vision.active_gesture:
        gest_color = (255, 200, 0)

    gest_val = FONT_SUBTITLE.render(vision.active_gesture, True, gest_color)
    surface.blit(gest_val, (cam_x + 65, gesture_y))

    # Guia compacto de gestos abaixo
    guide_y = gesture_y + 32
    pygame.draw.line(surface, COLOR_BORDER, (cam_x, guide_y), (cam_x + CAMERA_WIDTH, guide_y), 1)
    guide_y += 10

    cam_guides = [
        ("✋ ESQ/DIR", "Mão aberta nas zonas laterais"),
        ("✊ ROTACIONAR", "Punho fechado em qualquer lugar"),
        ("⬇ ACELERAR", "Mão aberta na zona inferior"),
        ("🤲 PAUSAR", "Duas mãos visíveis ao mesmo tempo"),
    ]
    for icon_action, desc in cam_guides:
        h_surf = FONT_SMALL.render(icon_action, True, COLOR_ACCENT)
        a_surf = FONT_SMALL.render(desc, True, COLOR_MUTED)
        surface.blit(h_surf, (cam_x, guide_y))
        surface.blit(a_surf, (cam_x + 130, guide_y))
        guide_y += 20

    # Indicador câmera disponível ou não
    cam_status = "🟢 CÂMERA ATIVA" if vision.camera_available else "🔴 CÂMERA INATIVA"
    cam_status_color = (0, 255, 102) if vision.camera_available else (255, 60, 60)
    status_surf = FONT_SMALL.render(cam_status, True, cam_status_color)
    surface.blit(status_surf, (cam_x, panel_rect.bottom - 24))

def draw_start_screen(surface):
    """Renderiza a tela inicial de carregamento/início."""
    surface.fill(COLOR_BG)
    
    # Título Principal Gigante
    title_glow = FONT_HUGE.render("TETRIS VISION AI", True, (244, 63, 94))
    title = FONT_HUGE.render("TETRIS VISION AI", True, (255, 0, 96))
    surface.blit(title_glow, (SCREEN_WIDTH // 2 - title.get_width() // 2 + 3, 153))
    surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 150))
    
    sub = FONT_SUBTITLE.render("Inteligência Artificial & Visão Computacional na Feira de Ciências", True, COLOR_MUTED)
    surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 220))
    
    # Caixa central explicativa
    info_rect = pygame.Rect(SCREEN_WIDTH // 2 - 300, 270, 600, 180)
    pygame.draw.rect(surface, COLOR_PANEL_BG, info_rect, border_radius=8)
    draw_neon_box(surface, info_rect, COLOR_BORDER, 2)
    
    desc_lines = [
        "Bem-vindo ao Tetris Vision AI!",
        "Este jogo demonstra o poder das Redes Neurais para detecção de pose.",
        "Uma câmera lê seus movimentos e os traduz em comandos em tempo real.",
        "",
        "Para iniciar, certifique-se de que sua câmera está bem iluminada.",
        "Pressione o botão abaixo ou clique com o mouse para iniciar!"
    ]
    
    curr_y = 290
    for line in desc_lines:
        line_surf = FONT_LABEL.render(line, True, COLOR_TEXT if line.startswith("Bem") or line.endswith("!") else COLOR_MUTED)
        surface.blit(line_surf, (SCREEN_WIDTH // 2 - line_surf.get_width() // 2, curr_y))
        curr_y += 24
        
    # Desenhar Botão de Jogar
    pygame.draw.rect(surface, (16, 185, 129), BTN_PLAY, border_radius=6)
    draw_neon_box(surface, BTN_PLAY, (52, 211, 153), 2, glow_radius=6)
    
    play_text = FONT_SUBTITLE.render("INICIAR JOGO", True, COLOR_TEXT)
    surface.blit(play_text, (BTN_PLAY.centerx - play_text.get_width() // 2, BTN_PLAY.centery - play_text.get_height() // 2))

def draw_overlays(surface, board_x, board_y):
    """Desenha sobreposições sobre o tabuleiro de jogo (Pausa / Game Over)."""
    board_w = GRID_COLS * CELL_SIZE
    board_h = GRID_ROWS * CELL_SIZE
    
    if game.game_over:
        # Fundo vermelho semitransparente sobre o grid
        overlay = pygame.Surface((board_w, board_h), pygame.SRCALPHA)
        overlay.fill((255, 0, 60, 180)) # Vermelho translúcido
        surface.blit(overlay, (board_x, board_y))
        
        # Textos de fim de jogo
        go_title = FONT_HUGE.render("FIM JOGO", True, COLOR_TEXT)
        surface.blit(go_title, (board_x + (board_w - go_title.get_width()) // 2, board_y + 120))
        
        sc_lbl = FONT_LABEL.render("PONTUAÇÃO FINAL:", True, COLOR_MUTED)
        surface.blit(sc_lbl, (board_x + (board_w - sc_lbl.get_width()) // 2, board_y + 220))
        
        sc_val = FONT_VALUE.render(str(game.score), True, COLOR_TEXT)
        surface.blit(sc_val, (board_x + (board_w - sc_val.get_width()) // 2, board_y + 245))
        
        # Botão de reiniciar
        pygame.draw.rect(surface, (30, 41, 59), BTN_RESTART, border_radius=4)
        draw_neon_box(surface, BTN_RESTART, (148, 163, 184), 2)
        
        rst_text = FONT_SUBTITLE.render("REINICIAR", True, COLOR_TEXT)
        surface.blit(rst_text, (BTN_RESTART.centerx - rst_text.get_width() // 2, BTN_RESTART.centery - rst_text.get_height() // 2))
        
    elif game.paused:
        # Fundo azul/cinza translúcido
        overlay = pygame.Surface((board_w, board_h), pygame.SRCALPHA)
        overlay.fill((11, 15, 25, 200)) # Escuro translúcido
        surface.blit(overlay, (board_x, board_y))
        
        # Texto de Pausa
        pause_title = FONT_HUGE.render("PAUSADO", True, COLOR_ACCENT)
        surface.blit(pause_title, (board_x + (board_w - pause_title.get_width()) // 2, board_y + 220))
        
        pause_sub = FONT_LABEL.render("Faça o gesto de 2 mãos", True, COLOR_MUTED)
        pause_sub2 = FONT_LABEL.render("ou aperte 'P' para voltar", True, COLOR_MUTED)
        surface.blit(pause_sub, (board_x + (board_w - pause_sub.get_width()) // 2, board_y + 300))
        surface.blit(pause_sub2, (board_x + (board_w - pause_sub2.get_width()) // 2, board_y + 320))

def main():
    # Posições de desenho
    board_x = BOARD_X
    board_y = BOARD_Y

    last_fall_time = pygame.time.get_ticks()
    
    running = True
    while running:
        current_time = pygame.time.get_ticks()
        
        # --- 1. CAPTURAR ENTRADAS DA IA (VISION CONTROLLER) ---
        ai_actions = []
        if vision.camera_available and game.started and not game.paused and not game.game_over:
            ai_actions = vision.get_actions()
            
            # Aplicar ações físicas detectadas
            for action in ai_actions:
                if action == 'LEFT':
                    game.move_left()
                elif action == 'RIGHT':
                    game.move_right()
                elif action == 'ROTATE':
                    game.rotate()
                elif action == 'DOWN':
                    game.drop()
                    last_fall_time = current_time # Reseta timer de gravidade natural se caiu ativamente
        elif vision.camera_available and game.started:
            # Rastrear as mãos mesmo quando pausado ou game over para permitir pausar/despausar e reiniciar
            ai_actions = vision.get_actions()
            
        # Tratamento especial para Pausa por 2 mãos da IA
        if 'PAUSE' in ai_actions:
            game.toggle_pause()
            
        # --- 2. TRATAR ENTRADAS DO TECLADO E EVENTOS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clique botão esquerdo
                    if not game.started:
                        if BTN_PLAY.collidepoint(event.pos):
                            game.reset()
                            game.started = True
                    elif game.game_over:
                        if BTN_RESTART.collidepoint(event.pos):
                            game.reset()
                            game.started = True
                            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    
                # Se o jogo ainda não começou, qualquer tecla ou Enter inicia
                elif not game.started:
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        game.reset()
                        game.started = True
                        
                # Controles principais quando jogando
                elif game.started and not game.paused and not game.game_over:
                    if event.key == pygame.K_LEFT:
                        game.move_left()
                    elif event.key == pygame.K_RIGHT:
                        game.move_right()
                    elif event.key == pygame.K_UP:
                        game.rotate()
                    elif event.key == pygame.K_DOWN:
                        game.drop()
                        last_fall_time = current_time
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()
                        last_fall_time = current_time
                    elif event.key == pygame.K_p:
                        game.toggle_pause()
                        
                # Pausado
                elif game.started and game.paused:
                    if event.key == pygame.K_p:
                        game.toggle_pause()
                        
                # Game Over
                elif game.started and game.game_over:
                    if event.key == pygame.K_r:
                        game.reset()

        # --- 3. GRAVIDADE / ATUALIZAÇÃO DO JOGO ---
        if game.started and not game.paused and not game.game_over:
            # Pegar velocidade baseado no nível atual
            fall_speed = game.get_drop_speed()
            if current_time - last_fall_time > fall_speed:
                game.drop()
                last_fall_time = current_time
                
        # --- 4. RENDERIZAÇÃO DA TELA (DESENHO) ---
        if not game.started:
            draw_start_screen(screen)
        else:
            screen.fill(COLOR_BG)

            # Painel esquerdo de estatísticas
            draw_stats_panel(screen, 15, 15)

            # Tabuleiro central
            draw_board(screen, board_x, board_y)

            # Painel da próxima peça (abaixo do painel de stats)
            draw_next_piece(screen, 15, 430, size=150)

            # Painel da câmera (coluna direita larga)
            draw_camera_panel(screen, CAM_PANEL_X, 15)

            # Sobreposições de estado (Pausa / Fim de Jogo)
            draw_overlays(screen, board_x, board_y)
            
        pygame.display.flip()
        clock.tick(FPS)
        
    # Liberar recursos ao fechar
    vision.release()
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
