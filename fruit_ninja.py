# -*- coding: utf-8 -*-
"""
Fruit Ninja Vision AI 🍉
Jogo de cortar frutas com a câmera real.
A ponta do dedo indicador é a lâmina — mova rápido para cortar!

Controles:
  ENTER / Clique → Iniciar
  R              → Reiniciar (após game over)
  ESC            → Sair
"""

import math
import os
import random
import sys
import threading
import urllib.request
import json
import time
from collections import deque

import cv2
import mediapipe as mp
import numpy as np
import pygame

# ─── Constantes ────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

FRUIT_TYPES = {
    'melancia': {'color': (40, 180, 40),   'inner': (210, 40, 60),   'seed': (20, 12, 8)},
    'laranja':  {'color': (230, 120, 10),  'inner': (255, 175, 60),  'seed': None},
    'maca':     {'color': (210, 30, 50),   'inner': (240, 175, 140), 'seed': (70, 25, 15)},
    'limao':    {'color': (200, 220, 20),  'inner': (245, 240, 90),  'seed': None},
    'uva':      {'color': (110, 30, 170),  'inner': (155, 70, 210),  'seed': None},
    'morango':  {'color': (220, 25, 55),   'inner': (255, 100, 110), 'seed': (15, 90, 20)},
    'abacaxi':  {'color': (220, 180, 10),  'inner': (255, 215, 60),  'seed': None},
}

GRAVITY        = 0.44
INITIAL_LIVES  = 3
TRAIL_LEN      = 20
SLICE_VEL_MIN  = 6   # px/frame mínimo para cortar


# ─── Utilitários ────────────────────────────────────────────────────────────
def seg_circle_hit(p1, p2, c, r):
    """Retorna True se o segmento p1→p2 intercepta o círculo (c, r).
    Usa projeção vetorial para encontrar o ponto mais próximo sem raiz quadrada.
    """
    x1, y1 = p1
    x2, y2 = p2
    cx, cy = c
    
    dx, dy = x2 - x1, y2 - y1
    lensq = dx*dx + dy*dy
    if lensq == 0:
        return (x1 - cx)**2 + (y1 - cy)**2 <= r*r
        
    # Calcula a projeção t do centro no segmento (limitado entre 0 e 1)
    t = ((cx - x1) * dx + (cy - y1) * dy) / lensq
    t = max(0.0, min(1.0, t))
    
    # Ponto mais próximo no segmento
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Compara a distância ao quadrado com o raio ao quadrado
    dist_sq = (closest_x - cx)**2 + (closest_y - cy)**2
    return dist_sq <= r*r


def lerp_col(c1, c2, t):
    return tuple(max(0, min(255, int(c1[i] + (c2[i]-c1[i])*t))) for i in range(3))


_GLOW_CACHE = {}

def draw_glow_circle(surface, color, pos, radius, glow=6):
    """Desenha círculo com brilho neon ao redor usando cache de superfícies para alto desempenho."""
    radius = max(1, int(radius))
    glow = max(1, int(glow))
    color_rgb = (int(color[0]), int(color[1]), int(color[2]))
    
    cache_key = (color_rgb, radius, glow)
    if cache_key not in _GLOW_CACHE:
        w = radius * 2 + glow * 2
        s = pygame.Surface((w, w), pygame.SRCALPHA)
        for g in range(glow, 0, -1):
            alpha = int(120 * (1 - g / glow))
            pygame.draw.circle(s, (*color_rgb, alpha), (radius + glow, radius + glow), radius + g)
        pygame.draw.circle(s, color_rgb, (radius + glow, radius + glow), radius)
        _GLOW_CACHE[cache_key] = s
    
    glow_surf = _GLOW_CACHE[cache_key]
    surface.blit(glow_surf, (pos[0] - radius - glow, pos[1] - radius - glow))


# ─── Caches de Performance e Gráficos pré-renderizados ───────────────────────
_FRUIT_SURFACE_CACHE = {}
_FRUIT_HALF_SURFACE_CACHE = {}
_BOMB_FUSE_TIP = {}

def get_fruit_surface(fruit_type, radius):
    key = (fruit_type, radius)
    if key in _FRUIT_SURFACE_CACHE:
        return _FRUIT_SURFACE_CACHE[key]
        
    size = radius * 2 + 16
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    r = radius
    
    if fruit_type == 'melancia':
        # Casca com listras escuras
        pygame.draw.circle(surf, (30, 120, 30), (cx, cy), r)
        for i in range(8):
            a = math.radians(i * 45)
            sx1 = cx + int(math.cos(a - 0.1) * r)
            sy1 = cy + int(math.sin(a - 0.1) * r)
            sx2 = cx + int(math.cos(a + 0.1) * r)
            sy2 = cy + int(math.sin(a + 0.1) * r)
            pygame.draw.polygon(surf, (15, 60, 15), [(cx, cy), (sx1, sy1), (sx2, sy2)], 0)
        # Casca interna clara (branca/verde-clara)
        pygame.draw.circle(surf, (180, 235, 120), (cx, cy), int(r * 0.85))
        # Polpa vermelha
        pygame.draw.circle(surf, (230, 45, 75), (cx, cy), int(r * 0.76))
        # Sementes espalhadas
        for i in range(5):
            a = math.radians(i * 72 + 15)
            sx = cx + int(math.cos(a) * r * 0.4)
            sy = cy + int(math.sin(a) * r * 0.4)
            pygame.draw.circle(surf, (20, 12, 8), (sx, sy), 3)
            
    elif fruit_type == 'laranja':
        pygame.draw.circle(surf, (230, 110, 10), (cx, cy), r)
        pygame.draw.circle(surf, (255, 235, 200), (cx, cy), int(r * 0.9))
        for i in range(8):
            a1 = math.radians(i * 45 + 3)
            a2 = math.radians((i + 1) * 45 - 3)
            pts = [
                (cx, cy),
                (cx + int(math.cos(a1)*r*0.82), cy + int(math.sin(a1)*r*0.82)),
                (cx + int(math.cos(a2)*r*0.82), cy + int(math.sin(a2)*r*0.82))
            ]
            pygame.draw.polygon(surf, (255, 150, 20), pts)
        pygame.draw.circle(surf, (255, 235, 200), (cx, cy), int(r * 0.15))
        
    elif fruit_type == 'limao':
        pygame.draw.circle(surf, (220, 210, 20), (cx, cy), r)
        pygame.draw.circle(surf, (220, 210, 20), (cx + int(r * 0.98), cy), int(r * 0.25))
        pygame.draw.circle(surf, (220, 210, 20), (cx - int(r * 0.98), cy), int(r * 0.25))
        pygame.draw.circle(surf, (255, 255, 220), (cx, cy), int(r * 0.88))
        for i in range(8):
            a1 = math.radians(i * 45 + 3)
            a2 = math.radians((i + 1) * 45 - 3)
            pts = [
                (cx, cy),
                (cx + int(math.cos(a1)*r*0.8), cy + int(math.sin(a1)*r*0.8)),
                (cx + int(math.cos(a2)*r*0.8), cy + int(math.sin(a2)*r*0.8))
            ]
            pygame.draw.polygon(surf, (245, 240, 80), pts)
        pygame.draw.circle(surf, (255, 255, 220), (cx, cy), int(r * 0.15))
        
    elif fruit_type == 'maca':
        pygame.draw.circle(surf, (210, 30, 45), (cx, cy), r)
        sa = math.radians(-90)
        stem_start = (cx + int(math.cos(sa)*r*0.8), cy + int(math.sin(sa)*r*0.8))
        stem_end = (cx + int(math.cos(sa - 0.3)*r*1.28), cy + int(math.sin(sa - 0.3)*r*1.28))
        pygame.draw.line(surf, (115, 70, 30), stem_start, stem_end, 3)
        leaf_pos = (cx + int(math.cos(sa - 0.15)*r*1.15), cy + int(math.sin(sa - 0.15)*r*1.15))
        pygame.draw.circle(surf, (40, 180, 50), leaf_pos, int(r * 0.26))
        shine_a = math.radians(-135)
        shine_x = cx + int(math.cos(shine_a) * r * 0.5)
        shine_y = cy + int(math.sin(shine_a) * r * 0.5)
        pygame.draw.circle(surf, (255, 255, 255), (shine_x, shine_y), int(r * 0.18))
        
    elif fruit_type == 'uva':
        offsets = [(0, -12), (-10, -3), (10, -3), (-15, 6), (0, 6), (15, 6), (-8, 15), (8, 15), (0, 24)]
        for ox, oy in offsets:
            rx = int(cx + ox * (r / 36.0))
            ry = int(cy + oy * (r / 36.0))
            pygame.draw.circle(surf, (100, 25, 160), (rx, ry), int(r * 0.35))
            pygame.draw.circle(surf, (220, 180, 255), (rx - int(r*0.08), ry - int(r*0.08)), int(r * 0.08))
            pygame.draw.circle(surf, (0, 0, 0), (rx, ry), int(r * 0.35), 1)
            
    elif fruit_type == 'morango':
        pts = []
        for i in range(12):
            a = math.radians(i * 30)
            rel_a = a % math.tau
            factor = 1.0 + 0.26 * math.sin(rel_a - math.pi/2)
            pts.append((cx + int(math.cos(a) * r * factor), cy + int(math.sin(a) * r * factor)))
        pygame.draw.polygon(surf, (220, 25, 55), pts)
        top_a = math.radians(-90)
        for leaf_off in [-0.5, 0.0, 0.5]:
            la = top_a + leaf_off
            lx = cx + int(math.cos(la) * r * 0.88)
            ly = cy + int(math.sin(la) * r * 0.88)
            pygame.draw.circle(surf, (34, 139, 34), (lx, ly), int(r * 0.28))
        for si in range(8):
            sa = math.radians(si * 45 + 10)
            sx = cx + int(math.cos(sa) * r * 0.5)
            sy = cy + int(math.sin(sa) * r * 0.5)
            pygame.draw.circle(surf, (250, 230, 80), (sx, sy), 2)
            
    elif fruit_type == 'abacaxi':
        pygame.draw.ellipse(surf, (225, 165, 10), (cx - r, cy - int(r*1.2), r*2, int(r*2.4)))
        for d in [-0.6, -0.2, 0.2, 0.6]:
            a1 = math.radians(45)
            p1 = (cx + int(math.cos(a1)*r*d) - int(math.cos(a1+1.57)*r), cy + int(math.sin(a1)*r*d) - int(math.sin(a1+1.57)*r))
            p2 = (cx + int(math.cos(a1)*r*d) + int(math.cos(a1+1.57)*r), cy + int(math.sin(a1)*r*d) + int(math.sin(a1+1.57)*r))
            pygame.draw.line(surf, (180, 110, 5), p1, p2, 2)
            a2 = math.radians(-45)
            p3 = (cx + int(math.cos(a2)*r*d) - int(math.cos(a2+1.57)*r), cy + int(math.sin(a2)*r*d) - int(math.sin(a2+1.57)*r))
            p4 = (cx + int(math.cos(a2)*r*d) + int(math.cos(a2+1.57)*r), cy + int(math.sin(a2)*r*d) + int(math.sin(a2+1.57)*r))
            pygame.draw.line(surf, (180, 110, 5), p3, p4, 2)
        top_a = math.radians(-90)
        for leaf_off in [-0.35, 0.0, 0.35]:
            la = top_a + leaf_off
            lx = cx + int(math.cos(la) * r * 1.22)
            ly = cy + int(math.sin(la) * r * 1.22)
            pygame.draw.circle(surf, (34, 139, 34), (lx, ly), int(r * 0.32))
            
    elif fruit_type == 'bomb':
        for g in range(r, 0, -3):
            col_val = int(22 + 78 * (1 - g/r))
            pygame.draw.circle(surf, (col_val, col_val, col_val + 6), (cx, cy), g)
        pygame.draw.circle(surf, (230, 230, 245), (cx - r//3, cy - r//3), r//6)
        pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r, 2)
        cap_a = math.radians(-90)
        ccx = cx + int(math.cos(cap_a) * r * 0.92)
        ccy = cy + int(math.sin(cap_a) * r * 0.92)
        pygame.draw.circle(surf, (185, 145, 25), (ccx, ccy), int(r * 0.25))
        pygame.draw.circle(surf, (0, 0, 0), (ccx, ccy), int(r * 0.25), 2)
        fuse_pts = []
        for i in range(12):
            t = i / 11.0
            fa = cap_a + t * 0.8
            fr = r * (1.0 + t * 0.42)
            fx = cx + int(math.cos(fa) * fr)
            fy = cy + int(math.sin(fa) * fr)
            fuse_pts.append((fx, fy))
            pygame.draw.circle(surf, (145, 98, 48), (fx, fy), 3)
        _BOMB_FUSE_TIP[key] = (fuse_pts[-1][0] - cx, fuse_pts[-1][1] - cy)

    if fruit_type != 'bomb':
        shine_w = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(shine_w, (255, 255, 255, 45), (r - r//3, r - r//3), r//4)
        surf.blit(shine_w, (cx - r, cy - r))
        pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r, 2)
        
    _FRUIT_SURFACE_CACHE[key] = surf
    return surf


def get_fruit_half_surface(fruit_type, radius, direction):
    key = (fruit_type, radius, direction)
    if key in _FRUIT_HALF_SURFACE_CACHE:
        return _FRUIT_HALF_SURFACE_CACHE[key]
        
    size = radius * 2 + 16
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    r = radius
    
    start_a = 0 if direction > 0 else math.pi
    end_a   = math.pi if direction > 0 else math.tau
    steps   = 18
    
    outer_pts, inner_pts = [], []
    for i in range(steps + 1):
        a = start_a + (end_a - start_a) * i / steps
        outer_pts.append((cx + math.cos(a)*r, cy + math.sin(a)*r))
        inner_pts.append((cx + math.cos(a)*r*0.82, cy + math.sin(a)*r*0.82))
    outer_pts.append((cx, cy))
    inner_pts.append((cx, cy))
    
    info = FRUIT_TYPES.get(fruit_type, list(FRUIT_TYPES.values())[0])
    color = info['color']
    inner = info['inner']
    
    try:
        pygame.draw.polygon(surf, color, outer_pts)
        pygame.draw.polygon(surf, inner, inner_pts)
        
        if color == FRUIT_TYPES['melancia']['color']:
            pulp_pts = []
            for i in range(steps + 1):
                a = start_a + (end_a - start_a) * i / steps
                pulp_pts.append((cx + math.cos(a)*r*0.78, cy + math.sin(a)*r*0.78))
            pulp_pts.append((cx, cy))
            pygame.draw.polygon(surf, (230, 45, 75), pulp_pts)
            for i in [2, 5]:
                a = start_a + (end_a - start_a) * i / 7
                sx = cx + int(math.cos(a) * r * 0.42)
                sy = cy + int(math.sin(a) * r * 0.42)
                pygame.draw.circle(surf, (20, 12, 8), (sx, sy), 3)
                
        elif color == FRUIT_TYPES['laranja']['color'] or color == FRUIT_TYPES['limao']['color']:
            wedge_col = (255, 150, 20) if color == FRUIT_TYPES['laranja']['color'] else (245, 240, 80)
            rind_col = (255, 235, 200) if color == FRUIT_TYPES['laranja']['color'] else (255, 255, 220)
            for i in range(4):
                a1 = start_a + (end_a - start_a) * i / 4 + 0.05
                a2 = start_a + (end_a - start_a) * (i + 1) / 4 - 0.05
                pts = [
                    (cx, cy),
                    (cx + int(math.cos(a1)*r*0.78), cy + int(math.sin(a1)*r*0.78)),
                    (cx + int(math.cos(a2)*r*0.78), cy + int(math.sin(a2)*r*0.78))
                ]
                pygame.draw.polygon(surf, wedge_col, pts)
            pygame.draw.circle(surf, rind_col, (cx, cy), int(r * 0.15))
            
        elif color == FRUIT_TYPES['maca']['color']:
            core_pts = []
            for i in range(steps + 1):
                a = start_a + (end_a - start_a) * i / steps
                core_pts.append((cx + math.cos(a)*r*0.38, cy + math.sin(a)*r*0.38))
            core_pts.append((cx, cy))
            pygame.draw.polygon(surf, (245, 240, 210), core_pts)
            sa = start_a + (end_a - start_a) * 0.5
            sx = cx + int(math.cos(sa) * r * 0.18)
            sy = cy + int(math.sin(sa) * r * 0.18)
            pygame.draw.circle(surf, (70, 25, 15), (sx, sy), 3)
            
        elif color == FRUIT_TYPES['morango']['color']:
            core_pts = []
            for i in range(steps + 1):
                a = start_a + (end_a - start_a) * i / steps
                core_pts.append((cx + math.cos(a)*r*0.42, cy + math.sin(a)*r*0.42))
            core_pts.append((cx, cy))
            pygame.draw.polygon(surf, (255, 150, 160), core_pts)
    except Exception:
        pass
        
    _FRUIT_HALF_SURFACE_CACHE[key] = surf
    return surf


# Caches para superfícies translúcidas e backgrounds estáticos
_START_BG_GRADIENT = None
_GLASS_OVERLAY = None
_GAMEOVER_OVERLAY = None
_HUD_BAR = None

def get_start_bg_gradient():
    global _START_BG_GRADIENT
    if _START_BG_GRADIENT is None:
        _START_BG_GRADIENT = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            r = int(8 + (25 - 8) * t)
            g = int(10 + (8 - 10) * t)
            b = int(20 + (35 - 20) * t)
            pygame.draw.line(_START_BG_GRADIENT, (r, g, b), (0, y), (SCREEN_W, y))
    return _START_BG_GRADIENT

def get_glass_overlay():
    global _GLASS_OVERLAY
    if _GLASS_OVERLAY is None:
        _GLASS_OVERLAY = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        _GLASS_OVERLAY.fill((10, 12, 24, 150))
    return _GLASS_OVERLAY

def get_gameover_overlay():
    global _GAMEOVER_OVERLAY
    if _GAMEOVER_OVERLAY is None:
        _GAMEOVER_OVERLAY = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        _GAMEOVER_OVERLAY.fill((0, 0, 0, 195))
    return _GAMEOVER_OVERLAY

def get_hud_bar():
    global _HUD_BAR
    if _HUD_BAR is None:
        _HUD_BAR = pygame.Surface((SCREEN_W, 76), pygame.SRCALPHA)
        _HUD_BAR.fill((0, 0, 0, 140))
    return _HUD_BAR


# Cache de labels e textos estáticos do jogo
_RESTART_LABEL_SURF = None
_MENU_LABEL_SURF = None
_VIDAS_LABEL_SURF = None
_PONTOS_LABEL_SURF = None

def get_restart_label(font):
    global _RESTART_LABEL_SURF
    if _RESTART_LABEL_SURF is None:
        _RESTART_LABEL_SURF = font.render("CORTAR P/ REINICIAR", True, (255, 100, 110))
    return _RESTART_LABEL_SURF

def get_menu_label(font):
    global _MENU_LABEL_SURF
    if _MENU_LABEL_SURF is None:
        _MENU_LABEL_SURF = font.render("CORTAR P/ VOLTAR MENU", True, (230, 230, 100))
    return _MENU_LABEL_SURF

def get_vidas_label(font):
    global _VIDAS_LABEL_SURF
    if _VIDAS_LABEL_SURF is None:
        _VIDAS_LABEL_SURF = font.render("VIDAS", True, (180,180,180))
    return _VIDAS_LABEL_SURF

def get_pontos_label(font):
    global _PONTOS_LABEL_SURF
    if _PONTOS_LABEL_SURF is None:
        _PONTOS_LABEL_SURF = font.render("PONTOS", True, (180,180,180))
    return _PONTOS_LABEL_SURF


# Tabela pré-calculada para cores do rastro
TRAIL_COLORS = []
for i in range(TRAIL_LEN + 1):
    t = i / max(1, TRAIL_LEN)
    c1 = (255, 220, 100)
    c2 = (255, 255, 255)
    tr = max(0, min(255, int(c1[0] + (c2[0]-c1[0])*t)))
    tg = max(0, min(255, int(c1[1] + (c2[1]-c1[1])*t)))
    tb = max(0, min(255, int(c1[2] + (c2[2]-c1[2])*t)))
    TRAIL_COLORS.append((tr, tg, tb))



# ─── Partícula ──────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','vx','vy','color','life','decay','r')

    def __init__(self, x, y, color, speed_range=(4, 14)):
        self.x, self.y = float(x), float(y)
        a = random.uniform(0, math.tau)
        s = random.uniform(*speed_range)
        self.vx, self.vy = math.cos(a)*s, math.sin(a)*s
        self.color  = color
        self.life   = 1.0
        self.decay  = random.uniform(0.022, 0.055)
        self.r      = random.randint(3, 9)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.28
        self.vx *= 0.97
        self.life -= self.decay
        return self.life > 0

    def draw(self, surf):
        if self.life <= 0:
            return
        r = max(1, int(self.r * self.life))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)


_SYS_FONT_CACHE = {}

def get_cached_sysfont(name, size, bold=False):
    key = (name, size, bold)
    if key not in _SYS_FONT_CACHE:
        try:
            _SYS_FONT_CACHE[key] = pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            _SYS_FONT_CACHE[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return _SYS_FONT_CACHE[key]


# ─── Onomatopeias de Combate (Visual SFX) ────────────────────────────────────
class VisualSFX:
    def __init__(self, x, y, text, color, size=28):
        self.x, self.y = float(x), float(y)
        self.text = text
        self.color = color
        self.size = size
        self.angle = random.uniform(-15, 15)
        self.life = 1.0
        self.decay = 0.024  # Dura cerca de 42 frames (~0.7s)
        self.scale = 0.5
        self.vy = random.uniform(-2.5, -4.5)

    def update(self):
        self.y += self.vy
        self.vy *= 0.94
        # Pop-in scaling
        self.scale = min(1.3, self.scale + 0.14)
        if self.scale > 1.0:
            self.scale = max(1.0, self.scale - 0.04)
        self.life -= self.decay
        return self.life > 0

    def draw(self, surf):
        if self.life <= 0:
            return
        alpha = int(255 * self.life)
        
        size_key = max(6, int(self.size * self.scale))
        # Usa fontes de impacto se disponíveis, senão Arial Negrito (usando o cache ultra-rápido)
        try:
            font = get_cached_sysfont("Impact", size_key)
        except Exception:
            font = get_cached_sysfont("Arial", size_key, bold=True)
            
        # Contorno preto para excelente contraste na câmera
        shadow = font.render(self.text, True, (0, 0, 0))
        main = font.render(self.text, True, self.color)
        
        shadow.set_alpha(alpha)
        main.set_alpha(alpha)
        
        if abs(self.angle) > 1:
            shadow = pygame.transform.rotate(shadow, self.angle)
            main = pygame.transform.rotate(main, self.angle)
            
        w, h = main.get_size()
        pos = (int(self.x - w//2), int(self.y - h//2))
        surf.blit(shadow, (pos[0] + 3, pos[1] + 3))
        surf.blit(main, pos)


class FruitHalf:
    def __init__(self, fruit, direction):
        info = FRUIT_TYPES.get(fruit.fruit_type, list(FRUIT_TYPES.values())[0])
        self.x, self.y = fruit.x, fruit.y
        self.r = fruit.radius
        self.color = info['color']
        self.inner  = info['inner']
        self.vx = fruit.vx + direction * random.uniform(4, 9)
        self.vy = fruit.vy - random.uniform(1, 4)
        self.side = direction
        self.angle = fruit.angle
        self.rot = direction * random.uniform(3, 8)
        self.life = 1.0
        self.fruit_type = fruit.fruit_type

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += GRAVITY
        self.angle += self.rot
        self.life -= 0.018
        return self.life > 0 and self.y < SCREEN_H + 150

    def draw(self, surf):
        cached_surf = get_fruit_half_surface(self.fruit_type, self.r, self.side)
        rotated_surf = pygame.transform.rotate(cached_surf, self.angle)
        rw, rh = rotated_surf.get_size()
        surf.blit(rotated_surf, (int(self.x - rw//2), int(self.y - rh//2)))


# ─── Fruta ─────────────────────────────────────────────────────────────────
class Fruit:
    def __init__(self, is_bomb=False):
        x_min = 120
        x_max = SCREEN_W - 120
        self.x = float(random.uniform(x_min, x_max))
        self.y = float(SCREEN_H + 70)
        
        # Velocidade vertical (vy) projetada para nunca ultrapassar o topo da tela
        self.vy = random.uniform(-22.0, -18.0)
        
        # Calcula o tempo necessário para a fruta atingir o pico da trajetória
        peak_time = -self.vy / GRAVITY
        
        # Define um alvo seguro na tela usando a fórmula de simetria parabólica
        # garantindo que tanto o início quanto o ponto final de queda estejam
        # estritamente dentro da tela jogável [x_min, x_max].
        target_min = (x_min + self.x) / 2.0
        target_max = (x_max + self.x) / 2.0
        target_x = random.uniform(target_min, target_max)
        self.vx = (target_x - self.x) / peak_time
        
        self.radius   = random.randint(38, 58)
        self.angle    = 0.0
        self.rot_speed = random.uniform(-5, 5)
        self.sliced   = False
        self.alive    = True
        self.is_bomb  = is_bomb
        self.wobble   = random.uniform(0, math.tau)
        self.entered_screen = False

        if not is_bomb:
            self.fruit_type = random.choice(list(FRUIT_TYPES.keys()))
        else:
            self.fruit_type = 'bomb'

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += GRAVITY
        self.angle += self.rot_speed
        self.wobble += 0.09
        if self.y < SCREEN_H:
            self.entered_screen = True
        if self.y > SCREEN_H + 140 or not (-250 < self.x < SCREEN_W + 250):
            self.alive = False
        return self.alive and not self.sliced

    def draw(self, surf):
        x, y, r = int(self.x), int(self.y), self.radius
        if self.is_bomb:
            # Desenha o corpo da bomba pré-renderizado e o pavio
            cached_surf = get_fruit_surface('bomb', r)
            rotated_surf = pygame.transform.rotate(cached_surf, self.angle)
            rw, rh = rotated_surf.get_size()
            bx, by = x - rw//2, y - rh//2
            surf.blit(rotated_surf, (bx, by))
            
            # Obtém a posição da centelha no pavio baseada na rotação da bomba
            offset = _BOMB_FUSE_TIP.get(('bomb', r), (0, 0))
            rad = math.radians(-self.angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            rx = int(offset[0] * cos_a - offset[1] * sin_a)
            ry = int(offset[0] * sin_a + offset[1] * cos_a)
            spark_x, spark_y = x + rx, y + ry
            
            # Centelha de fogo pulsante na ponta do pavio
            pulse = int(5 * (1.0 + 0.45 * math.sin(pygame.time.get_ticks() * 0.032)))
            s = pygame.Surface((pulse*6, pulse*6), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 100, 0, 80), (pulse*3, pulse*3), pulse*3)
            pygame.draw.circle(s, (255, 220, 0, 160), (pulse*3, pulse*3), pulse*2)
            surf.blit(s, (spark_x - pulse*3, spark_y - pulse*3))
            
            # LED vermelho pulsante piscando no centro
            flash = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.016))
            pygame.draw.circle(surf, (flash, 20, 20), (x, y), r//4)
            pygame.draw.circle(surf, (255, 255, 255), (x, y), r//8)
            
            # Texto "BOMB"
            font = get_cached_sysfont("Arial", 16, bold=True)
            lbl = font.render("BOMB", True, (255, 255, 255))
            surf.blit(lbl, (x - lbl.get_width()//2, y + r//3))
        else:
            # Desenha a fruta pré-renderizada e rotacionada de forma ultra-rápida
            cached_surf = get_fruit_surface(self.fruit_type, r)
            rotated_surf = pygame.transform.rotate(cached_surf, self.angle)
            rw, rh = rotated_surf.get_size()
            surf.blit(rotated_surf, (int(self.x - rw//2), int(self.y - rh//2)))


# ─── Rastro da lâmina ───────────────────────────────────────────────────────
class SliceTrail:
    def __init__(self):
        self.points = deque(maxlen=TRAIL_LEN)

    def add(self, x, y):
        self.points.append((x, y))

    def clear(self):
        self.points.clear()

    def velocity(self):
        pts = list(self.points)
        if len(pts) < 2:
            return 0
        return math.hypot(pts[-1][0]-pts[-2][0], pts[-1][1]-pts[-2][1])

    def segments(self):
        pts = list(self.points)
        for i in range(1, len(pts)):
            yield pts[i-1], pts[i]

    def draw(self, surf):
        pts = list(self.points)
        n = len(pts)
        if n < 2:
            return
        # Rastro com degradê de cor ultra-rápido via lookup-table pré-calculada
        for i in range(1, n):
            idx = int((i / n) * TRAIL_LEN)
            color = TRAIL_COLORS[min(TRAIL_LEN, max(0, idx))]
            w = max(1, int((i / n) * 9))
            pygame.draw.line(surf, color, pts[i-1], pts[i], w)
        # Indicador na ponta do dedo
        if pts:
            draw_glow_circle(surf, (0, 230, 255), pts[-1], 8, glow=8)


# ─── Combo display ───────────────────────────────────────────────────────────
class ComboDisplay:
    def __init__(self):
        self.value = 0
        self.timer = 0
        self.scale = 1.0
        self.font_big  = pygame.font.SysFont("Arial", 80, bold=True)
        self.font_sub  = pygame.font.SysFont("Arial", 32, bold=True)

    def trigger(self, combo):
        self.value = combo
        self.timer = 80
        self.scale = 1.6

    def update(self):
        if self.timer > 0:
            self.timer -= 1
            self.scale = max(1.0, self.scale - 0.025)

    def draw(self, surf):
        if self.timer > 0 and self.value >= 2:
            alpha = int(255 * self.timer / 80)
            txt = f"× {self.value}  COMBO!"
            font = get_cached_sysfont("Arial", int(80 * self.scale), bold=True)
            s = font.render(txt, True, (255, 215, 0))
            s.set_alpha(alpha)
            surf.blit(s, (SCREEN_W//2 - s.get_width()//2, SCREEN_H//3))


# ─── Jogo ───────────────────────────────────────────────────────────────────
class FruitNinjaGame:
    def __init__(self):
        self.high_score = 0
        self.reset()

    def reset(self):
        self.score        = 0
        self.lives        = INITIAL_LIVES
        self.fruits: list[Fruit]      = []
        self.halves: list[FruitHalf]  = []
        self.particles: list[Particle]= []
        self.combo        = 0
        self.combo_timer  = 0
        self.combo_disp   = ComboDisplay()
        self.spawn_timer  = 60
        self.started      = False
        self.game_over    = False
        self.level        = 1
        self.sliced_total = 0
        self.sfx: list[VisualSFX]     = []
        self.btn_restart  = None
        self.btn_menu     = None
        
        # Atributos para o Ranking Online (Firebase)
        self.player_name  = f"Jogador #{random.randint(100, 999)}"
        self.score_saved  = False
        self.score_uploading = False
        self.save_status  = "ENVIANDO PONTUAÇÃO E FOTO... 📸"
        self.btn_save     = None

    def save_score_to_firebase(self, latest_frame=None):
        if self.score_saved or self.score_uploading or self.score == 0:
            return
            
        self.score_uploading = True
        name = self.player_name.strip()
        if name == "":
            name = "ANONIMO"
            
        self.save_status = "ENVIANDO PONTUACAO..."
        
        # Gera a foto em base64 a partir do frame atual da câmera
        photo_b64 = ""
        if latest_frame is not None:
            try:
                h, w = latest_frame.shape[:2]
                sz = min(h, w)
                x0 = (w - sz) // 2
                y0 = (h - sz) // 2
                cropped = latest_frame[y0:y0+sz, x0:x0+sz]
                # Redimensionamos para 400x400 com qualidade JPEG 85 para excelente nitidez na galeria (~25kb)
                resized = cv2.resize(cropped, (400, 400), interpolation=cv2.INTER_AREA)
                success, encoded_img = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if success:
                    import base64
                    photo_b64 = base64.b64encode(encoded_img).decode('utf-8')
            except Exception as e:
                print(f"Erro ao processar foto: {e}")
        
        # Dispara a thread de upload para evitar lag/travamento
        t = threading.Thread(target=self._upload_thread, args=(name, self.score, photo_b64))
        t.daemon = True
        t.start()
        
    def _upload_thread(self, name, score, photo_b64):
        # Usamos a URL do Firebase RTDB do usuario
        url = "https://fruitninjavisionai-default-rtdb.firebaseio.com/ranking.json"
        
        # Gera uma semente única para a foto de avatar baseada no nome (caso precise de fallback)
        avatar_seed = f"{name}_{random.randint(100, 999)}"
        
        data = {
            "name": name,
            "score": score,
            "timestamp": int(time.time() * 1000),
            "avatar_seed": avatar_seed,
            "photo_base64": photo_b64
        }
        
        req_data = json.dumps(data).encode("utf-8")
        try:
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in (200, 201):
                    self.save_status = "SALVO COM SUCESSO! 🚀"
                    self.score_saved = True
                else:
                    self.save_status = f"ERRO DE STATUS: {response.status}"
                    self.score_uploading = False
        except Exception as e:
            print(f"Erro ao salvar no Firebase: {e}")
            self.save_status = "ERRO DE REDE/CONEXAO! ❌"
            self.score_uploading = False

    def _spawn_wave(self):
        is_bomb = random.random() < (0.10 + self.level * 0.01)
        count   = random.randint(1, min(3, 1 + self.level // 3))
        for i in range(count):
            f = Fruit(is_bomb=(is_bomb and i == 0))
            self.fruits.append(f)

    def update(self):
        if not self.started or self.game_over:
            return

        # Combo decay
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0
        self.combo_disp.update()

        # Spawn
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_wave()
            interval = max(24, 78 - self.level * 5)
            self.spawn_timer = interval

        # Update fruits — track missed ones
        missed = 0
        alive  = []
        for f in self.fruits:
            if f.update():
                alive.append(f)
            elif not f.sliced and not f.is_bomb:
                if f.entered_screen:
                    missed += 1
        self.fruits = alive

        if missed:
            self.lives = max(0, self.lives - missed)
            self.combo = 0
            if self.lives == 0:
                self.game_over = True
                self.high_score = max(self.high_score, self.score)

        # Update halves & particles
        self.halves    = [h for h in self.halves    if h.update()]
        self.particles = [p for p in self.particles if p.update()]
        self.sfx       = [s for s in self.sfx       if s.update()]

        # Level up
        new_level = min(10, 1 + self.sliced_total // 8)
        if new_level != self.level:
            self.level = new_level

    def slice_check(self, trail: SliceTrail):
        if trail.velocity() < SLICE_VEL_MIN:
            return
        pts = list(trail.points)
        if len(pts) < 2:
            return
        
        # Apenas os 2 segmentos mais recentes (frames atual e anterior) realizam o corte físico.
        # O restante do rastro (até 20 frames) permanece ativo apenas como feedback visual estético.
        # Isso evita colisões acidentais com frutas/bombas cruzando rastros antigos no ar.
        active_segments = []
        if len(pts) >= 2:
            active_segments.append((pts[-2], pts[-1]))
        if len(pts) >= 3:
            active_segments.append((pts[-3], pts[-2]))

        for seg_a, seg_b in active_segments:
            for f in self.fruits:
                if f.sliced:
                    continue
                if seg_circle_hit(seg_a, seg_b, (f.x, f.y), f.radius):
                    f.sliced = True
                    self._on_slice(f)

    def _on_slice(self, f: Fruit):
        if f.is_bomb:
            self.lives = 0
            self.game_over = True
            self.high_score = max(self.high_score, self.score)
            for _ in range(50):
                self.particles.append(Particle(f.x, f.y, (255, 100, 0)))
            for _ in range(20):
                self.particles.append(Particle(f.x, f.y, (255, 220, 60)))
            self.sfx.append(VisualSFX(f.x, f.y, "BOOM!", (255, 30, 30), size=55))
            return

        self.combo += 1
        self.combo_timer = 50
        pts = 10 * max(1, self.combo)
        self.score += pts
        self.sliced_total += 1

        if self.combo >= 2:
            self.combo_disp.trigger(self.combo)

        info = FRUIT_TYPES[f.fruit_type]

        # Chance de spawnar onomatopeias comuns (SPLASH, SLASH, CHOP, SLICED)
        if random.random() < 0.40:
            word = random.choice(["SPLASH!", "SLASH!", "CHOP!", "SLICED!"])
            self.sfx.append(VisualSFX(f.x, f.y, word, info['inner'], size=26))

        if self.combo >= 2:
            self.combo_disp.trigger(self.combo)
            combo_word = f"COMBO ×{self.combo}!" if self.combo < 4 else f"NINJA ×{self.combo}!"
            self.sfx.append(VisualSFX(f.x, f.y - 30, combo_word, (255, 215, 0), size=32))

        self.halves.append(FruitHalf(f, +1))
        self.halves.append(FruitHalf(f, -1))

        for _ in range(22):
            self.particles.append(Particle(f.x, f.y, info['inner']))
        for _ in range(8):
            self.particles.append(Particle(f.x, f.y, info['color']))

    def draw(self, surf, fonts):
        # Fruits
        for f in self.fruits:
            if not f.sliced:
                f.draw(surf)
        # Halves
        for h in self.halves:
            h.draw(surf)
        # Particles
        for p in self.particles:
            p.draw(surf)
        # SFX
        for s in self.sfx:
            s.draw(surf)
        # Combo
        self.combo_disp.draw(surf)
        # HUD
        self._draw_hud(surf, fonts)

    def _draw_hud(self, surf, fonts):
        # Desenha a barra superior pré-renderizada
        surf.blit(get_hud_bar(), (0, 0))

        # Vidas (círculos)
        for i in range(INITIAL_LIVES):
            c = (220, 40, 60) if i < self.lives else (60, 60, 60)
            pygame.draw.circle(surf, c, (38 + i * 52, 38), 20)
            pygame.draw.circle(surf, (0,0,0), (38 + i * 52, 38), 20, 2)
            
        lbl = get_vidas_label(fonts['small'])
        surf.blit(lbl, (20, 62))

        # Score (Cache dinâmico)
        if not hasattr(self, '_score_surf') or self._score_val != self.score:
            self._score_val = self.score
            self._score_surf = fonts['big'].render(str(self.score), True, (255, 215, 0))
            
        surf.blit(self._score_surf, (SCREEN_W - self._score_surf.get_width() - 18, 8))
        
        slbl = get_pontos_label(fonts['small'])
        surf.blit(slbl, (SCREEN_W - slbl.get_width() - 18, 60))

        # Level (Cache dinâmico)
        if not hasattr(self, '_level_surf') or self._level_val != self.level:
            self._level_val = self.level
            self._level_surf = fonts['label'].render(f"NÍVEL  {self.level}", True, (56, 189, 248))
            
        surf.blit(self._level_surf, (SCREEN_W//2 - self._level_surf.get_width()//2, 24))


# ─── Hand tracker ───────────────────────────────────────────────────────────
class HandTracker:
    def __init__(self, model_path):
        self.available = False
        self.cap = None
        self.landmarker = None
        self._ts = 0
        self.prev_x = None
        self.prev_y = None
        self._latest_frame = None
        self.latest_surf = None
        self.latest_tip = None
        self.start_snapshot = None
        self.end_snapshot = None
        
        self.lock = threading.Lock()
        self.running = False
        self.thread = None

        if not os.path.exists(model_path):
            print(f"[AVISO] Modelo não encontrado: {model_path}")
            return

        BaseOptions = mp.tasks.BaseOptions
        HL = mp.tasks.vision.HandLandmarker
        HLO = mp.tasks.vision.HandLandmarkerOptions
        RM = mp.tasks.vision.RunningMode

        with open(model_path, 'rb') as fh:
            model_bytes = fh.read()

        opts = HLO(
            base_options=BaseOptions(model_asset_buffer=model_bytes),
            running_mode=RM.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.55,
            min_hand_presence_confidence=0.55,
            min_tracking_confidence=0.50,
        )
        try:
            self.landmarker = HL.create_from_options(opts)
        except Exception as e:
            print(f"[AVISO] HandLandmarker falhou: {e}")
            return

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[AVISO] Câmera indisponível.")
            self.cap = None
            return

        # Captura em resolução otimizada de 640x360 para velocidade máxima
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  360)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Evita acúmulo de frames na fila da câmera
        self.available = True
        
        # Inicia a thread daemon de captura/inferência em segundo plano
        self.running = True
        self.thread = threading.Thread(target=self._thread_loop, name="HandTrackerThread")
        self.thread.daemon = True
        self.thread.start()

    @property
    def latest_frame(self):
        with self.lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    @latest_frame.setter
    def latest_frame(self, val):
        with self.lock:
            self._latest_frame = val

    def _is_valid_hand(self, lm):
        # Mão para o Fruit Ninja: Checa a estrutura rígida da palma (nunca dobra)
        # Landmark 0 = pulso, Landmark 5 = nó do indicador, Landmark 17 = nó do mínimo
        wrist = lm[0]
        idx_k = lm[5]
        pin_k = lm[17]
        plen = math.hypot(idx_k.x - wrist.x, idx_k.y - wrist.y)
        pw   = math.hypot(pin_k.x - idx_k.x,  pin_k.y - idx_k.y)
        
        # Mão saudável tem proporções de palma válidas e tamanho mínimo no frame.
        if plen < 0.015 or pw < 0.005:
            return False
        ratio = plen / max(pw, 0.001)
        return 0.15 <= ratio <= 8.0

    def _is_pointing_finger(self, lm):
        def dist(a, b):
            return math.hypot(a.x - b.x, a.y - b.y)
        
        # Para cada dedo, comparamos a distância nódulo-ponta com o comprimento do osso da base (MCP-PIP).
        # Indicador (5=MCP, 6=PIP, 8=Tip)
        idx_base = dist(lm[6], lm[5])
        idx_tip  = dist(lm[8], lm[5])
        
        # Médio (9=MCP, 10=PIP, 12=Tip)
        mid_base = dist(lm[10], lm[9])
        mid_tip  = dist(lm[12], lm[9])
        
        # Anelar (13=MCP, 14=PIP, 16=Tip)
        ring_base = dist(lm[14], lm[13])
        ring_tip  = dist(lm[16], lm[13])
        
        # O indicador deve estar estendido (distância ponta-nódulo > 1.15x o osso base)
        idx_extended = idx_tip > idx_base * 1.15
        
        # Aceitamos o gesto de apontar (indicador estendido, médio/anelar relativamente dobrados)
        # OU o gesto de mão aberta (golpe de caratê/chop, onde os outros dedos também estão estendidos).
        pointing = idx_extended and (mid_tip < mid_base * 1.45) and (ring_tip < ring_base * 1.45)
        open_hand = idx_extended and (mid_tip > mid_base * 1.15) and (ring_tip > ring_base * 1.15)
        
        return pointing or open_hand

    def _thread_loop(self):
        while self.running:
            if not self.available or self.cap is None:
                time.sleep(0.03)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.03)  # Dorme mais se falhar a câmera para não travar a CPU
                continue

            frame = cv2.flip(frame, 1)
            
            # Força o frame a estar em 640x360
            h, w = frame.shape[:2]
            if w != 640 or h != 360:
                frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_LINEAR)
                
            raw_frame_copy = frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            
            self._ts += 33333
            
            results = None
            if self.landmarker:
                try:
                    results = self.landmarker.detect_for_video(mp_img, self._ts)
                except Exception as e:
                    print(f"[ERRO] Falha na detecção do MediaPipe: {e}")

            tip = None
            if results and results.hand_landmarks:
                lm = results.hand_landmarks[0]
                if self._is_valid_hand(lm) and self._is_pointing_finger(lm):
                    t8 = lm[8]
                    raw_x = int(t8.x * SCREEN_W)
                    raw_y = int(t8.y * SCREEN_H)
                    
                    # Suavização exponencial thread-safe (peso aprimorado de 75% raw para corte cirúrgico e instantâneo)
                    with self.lock:
                        if self.prev_x is None:
                            self.prev_x, self.prev_y = raw_x, raw_y
                        else:
                            self.prev_x = int(self.prev_x * 0.25 + raw_x * 0.75)
                            self.prev_y = int(self.prev_y * 0.25 + raw_y * 0.75)
                        tip = (self.prev_x, self.prev_y)
                    
                    # Desenha o indicador visual da ponta do dedo de forma proporcional no frame 640x360
                    tx_frame = int(t8.x * 640)
                    ty_frame = int(t8.y * 360)
                    cv2.circle(frame, (tx_frame, ty_frame), 8, (0, 220, 200), -1)
                    cv2.circle(frame, (tx_frame, ty_frame), 10, (255, 255, 255), 2)
            else:
                with self.lock:
                    self.prev_x = None
                    self.prev_y = None

            # Redimensionamento rápido para exibição no Pygame (1280x720)
            disp = cv2.resize(frame, (SCREEN_W, SCREEN_H), interpolation=cv2.INTER_LINEAR)
            rgb_disp = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
            
            # Converter a imagem em superfície do Pygame na thread secundária sem duplicar memória e já convertida para o display nativo
            surf = pygame.image.frombuffer(rgb_disp, (SCREEN_W, SCREEN_H), 'RGB').convert()

            with self.lock:
                self._latest_frame = raw_frame_copy
                self.latest_surf = surf
                self.latest_tip = tip

            # cap.read() já bloqueia no driver. Usamos sleep mínimo de 1ms apenas para rendimento de CPU.
            time.sleep(0.001)

    def get_frame_and_tip(self):
        """Retorna instantaneamente (pygame_surface | None, (x,y) | None) sem bloquear."""
        if not self.available:
            return None, None
        with self.lock:
            return self.latest_surf, self.latest_tip

    def release(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.landmarker:
            self.landmarker.close()
        cv2.destroyAllWindows()


# ─── Fontes ─────────────────────────────────────────────────────────────────
def make_fonts():
    names = ["Segoe UI", "Arial", "Trebuchet MS"]
    def best(size, bold=False):
        for n in names:
            try:
                return pygame.font.SysFont(n, size, bold=bold)
            except Exception:
                pass
        return pygame.font.Font(None, size)
    return {
        'huge':  best(90, True),
        'big':   best(52, True),
        'title': best(38, True),
        'sub':   best(26, True),
        'label': best(20, True),
        'small': best(16),
    }


# ─── Telas especiais ─────────────────────────────────────────────────────────
_START_UI_SURFACE = None
_START_UI_HIGH_SCORE = -1

def get_start_ui_surface(fonts, high_score):
    global _START_UI_SURFACE, _START_UI_HIGH_SCORE
    if _START_UI_SURFACE is None or _START_UI_HIGH_SCORE != high_score:
        _START_UI_HIGH_SCORE = high_score
        ui_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        
        # Title shadow + main
        for off, col in [(4, (100, 0, 30)), (0, (255, 55, 100))]:
            t = fonts['huge'].render("FRUIT NINJA  🍉", True, col)
            ui_surf.blit(t, (SCREEN_W//2 - t.get_width()//2 + off, 80 + off))

        sub = fonts['sub'].render("Controle com o dedo indicador pela câmera!", True, (200,200,210))
        ui_surf.blit(sub, (SCREEN_W//2 - sub.get_width()//2, 195))

        fs_hint = fonts['small'].render("F / F11 → Alternar Tela Cheia", True, (120, 180, 255))
        ui_surf.blit(fs_hint, (SCREEN_W//2 - fs_hint.get_width()//2, 222))

        # Info box
        box = pygame.Rect(SCREEN_W//2 - 340, 240, 680, 215)
        pygame.draw.rect(ui_surf, (18, 22, 40), box, border_radius=14)
        pygame.draw.rect(ui_surf, (90, 40, 130), box, 2, border_radius=14)

        tips = [
            "🍉  Frutas sobem e caem — corte-as rápido com o dedo!",
            "💣  EVITE as BOMBAS — elas encerram o jogo na hora!",
            "⚡  Mova o dedo rapidamente para ativar a lâmina",
            "🔥  Corte várias frutas em sequência para COMBOS!",
            "❤   Você tem 3 vidas — cada fruta perdida custa 1 vida",
            f"🏆  Recorde:  {high_score} pontos",
        ]
        cy = 252
        for tip in tips:
            s = fonts['small'].render(tip, True, (170, 195, 225))
            ui_surf.blit(s, (SCREEN_W//2 - s.get_width()//2, cy))
            cy += 32

        # Glowing Start Fruit Area
        bt = fonts['sub'].render("👉  CORTE A MELANCIA PARA INICIAR  👈", True, (0, 230, 255))
        ui_surf.blit(bt, (SCREEN_W//2 - bt.get_width()//2, 620))

        if high_score == 0:
            cam_note = fonts['small'].render(
                "⚠  Se a câmera não detectar sua mão, aproxime-se e ilumine o ambiente", True, (160,160,90))
            ui_surf.blit(cam_note, (SCREEN_W//2 - cam_note.get_width()//2, 665))
            
        _START_UI_SURFACE = ui_surf
    return _START_UI_SURFACE


def draw_start_screen(surf, fonts, high_score, bg_surf=None):
    if bg_surf is not None:
        surf.blit(bg_surf, (0, 0))
        surf.blit(get_glass_overlay(), (0, 0))
    else:
        surf.blit(get_start_bg_gradient(), (0, 0))

    # Desenha toda a interface estática do menu com 1 único blit de alto desempenho
    surf.blit(get_start_ui_surface(fonts, high_score), (0, 0))


def draw_game_over(surf, fonts, game):
    surf.blit(get_gameover_overlay(), (0, 0))

    # Título deslocado levemente para cima para abrir espaço para o formulário
    go = fonts['huge'].render("FIM DE JOGO", True, (255, 60, 60))
    surf.blit(go, (SCREEN_W//2 - go.get_width()//2, 80))

    sc = fonts['big'].render(f"Pontuacao:  {game.score}", True, (255, 215, 0))
    surf.blit(sc, (SCREEN_W//2 - sc.get_width()//2, 190))

    hs_col = (0, 230, 120) if game.score >= game.high_score else (150, 150, 160)
    hs_txt = "NOVO RECORDE! 🏆" if game.score >= game.high_score else f"Recorde:  {game.high_score}"
    hs = fonts['sub'].render(hs_txt, True, hs_col)
    surf.blit(hs, (SCREEN_W//2 - hs.get_width()//2, 250))

    # ─── CAIXA DE NOME PARA RANKING ONLINE (FIREBASE) ───
    box_w, box_h = 560, 120
    box_x = SCREEN_W // 2 - box_w // 2
    box_y = 300
    box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
    
    # Desenha o fundo da caixa de entrada
    pygame.draw.rect(surf, (15, 20, 32), box_rect, border_radius=14)
    
    # Define o status text e a cor da borda com base no status do Firebase
    if game.score == 0:
        status_text = "NENHUMA FRUTA FOI CORTADA"
        border_col = (90, 105, 120)
    elif game.score_saved:
        status_text = "SALVO NO RANKING ONLINE! 🚀"
        border_col = (0, 230, 120)  # Verde se salvo
    elif "ERRO" in game.save_status:
        status_text = "ERRO DE CONEXÃO AO SALVAR! ❌"
        border_col = (255, 60, 80)  # Vermelho se falhar
    else:
        status_text = "ENVIANDO PONTUAÇÃO E FOTO... 📸"
        border_col = (255, 215, 0)  # Amarelo/Dourado se estiver enviando
        
    pygame.draw.rect(surf, border_col, box_rect, 2, border_radius=14)

    # Identificação do Jogador
    id_surf = fonts['small'].render("NINJA DETECTADO:", True, (150, 150, 160))
    surf.blit(id_surf, (box_x + 20, box_y + 16))

    name_surf = fonts['title'].render(game.player_name, True, (255, 255, 255))
    surf.blit(name_surf, (box_x + 20, box_y + 42))

    # Rótulo de Status
    status_surf = fonts['label'].render(status_text, True, border_col)
    surf.blit(status_surf, (box_x + 20, box_y + 82))

    # Dica de instrução
    hint_txt = "Sua pontuação e foto foram enviadas automaticamente para o site!"
    if game.score == 0:
        hint_txt = "Corte uma das frutas abaixo para iniciar uma nova partida!"
    hint_surf = fonts['small'].render(hint_txt, True, (170, 195, 225))
    surf.blit(hint_surf, (SCREEN_W//2 - hint_surf.get_width()//2, box_y + box_h + 15))



# ─── Loop principal ──────────────────────────────────────────────────────────
def main():
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Fruit Ninja Vision AI 🍉")
    clock  = pygame.time.Clock()
    fonts  = make_fonts()

    tracker = HandTracker(MODEL_PATH)
    game    = FruitNinjaGame()
    trail   = SliceTrail()
    lost_frames = 0

    # Special Start Fruit for the start screen
    start_fruit = Fruit(is_bomb=False)
    start_fruit.fruit_type = 'melancia'
    start_fruit.x = SCREEN_W // 2
    start_fruit.y = 530
    start_fruit.radius = 62
    start_fruit.rot_speed = 2.2

    running = True
    while running:
        clock.tick(FPS)

        # ── Eventos ─────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_f, pygame.K_F11):
                    pygame.display.toggle_fullscreen()
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and not game.started:
                    tracker.start_snapshot = tracker.latest_frame.copy() if tracker.latest_frame is not None else None
                    tracker.end_snapshot = None
                    game.reset()
                    game.started = True
                elif event.key == pygame.K_r and game.game_over:
                    tracker.start_snapshot = tracker.latest_frame.copy() if tracker.latest_frame is not None else None
                    tracker.end_snapshot = None
                    hs = game.high_score
                    game.reset()
                    game.high_score = hs
                    game.started    = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not game.started:
                    tracker.start_snapshot = tracker.latest_frame.copy() if tracker.latest_frame is not None else None
                    tracker.end_snapshot = None
                    game.reset()
                    game.started = True

        # ── Câmera + rastreamento ────────────────────────────────────────
        bg, tip = tracker.get_frame_and_tip()

        # ── Background + Rastro ──────────────────────────────────────────
        if tip:
            trail.add(*tip)
            lost_frames = 0
        else:
            lost_frames += 1
            if lost_frames > 6:
                trail.clear()
            elif len(trail.points) > 0:
                trail.points.popleft()

        # ── Lógica & render ─────────────────────────────────────────────
        if not game.started:
            # Draw start screen with glass background
            draw_start_screen(screen, fonts, game.high_score, bg_surf=bg)

            # Update and draw the spinning Start Fruit
            start_fruit.angle += start_fruit.rot_speed
            
            # Pulse glow circle around the start fruit to make it stand out
            pulse = 6 + int(math.sin(pygame.time.get_ticks() * 0.007) * 4)
            draw_glow_circle(screen, (255, 50, 100), (int(start_fruit.x), int(start_fruit.y)), start_fruit.radius + 4, glow=pulse)
            start_fruit.draw(screen)

            # Draw trail on top of the menu so they can slice the watermelon
            trail.draw(screen)

            # Update and draw background elements if they exist (halves/particles from menu actions)
            if game.halves or game.particles:
                game.halves = [h for h in game.halves if h.update()]
                game.particles = [p for p in game.particles if p.update()]
                for h in game.halves:
                    h.draw(screen)
                for p in game.particles:
                    p.draw(screen)

            # Check if start fruit is sliced
            if tip and trail.velocity() >= SLICE_VEL_MIN:
                for seg_a, seg_b in trail.segments():
                    if seg_circle_hit(seg_a, seg_b, (start_fruit.x, start_fruit.y), start_fruit.radius):
                        # Sliced! Play spectacular splash and start game
                        tracker.start_snapshot = tracker.latest_frame.copy() if tracker.latest_frame is not None else None
                        tracker.end_snapshot = None
                        game.reset()
                        game.started = True
                        
                        # Add split watermelon halves
                        game.halves.append(FruitHalf(start_fruit, +1))
                        game.halves.append(FruitHalf(start_fruit, -1))
                        
                        # Juice and rind particles
                        info = FRUIT_TYPES[start_fruit.fruit_type]
                        for _ in range(35):
                            game.particles.append(Particle(start_fruit.x, start_fruit.y, info['inner']))
                        for _ in range(15):
                            game.particles.append(Particle(start_fruit.x, start_fruit.y, info['color']))
                        break
        else:
            # Background
            if bg is not None:
                screen.blit(bg, (0, 0))
            else:
                screen.fill((10, 12, 22))

            # Verifica cortes antes do update (para usar trail atual)
            if not game.game_over:
                game.slice_check(trail)

            game.update()
            game.draw(screen, fonts)
            trail.draw(screen)

            if game.game_over:
                # Capture end snapshot at the exact moment Game Over triggers
                if tracker.end_snapshot is None and tracker.latest_frame is not None:
                    tracker.end_snapshot = tracker.latest_frame.copy()
                
                # Auto save to firebase if not already uploading/saved and score > 0
                if not game.score_saved and not game.score_uploading and game.score > 0:
                    # Choose a random snapshot between start_snapshot and end_snapshot
                    photos = []
                    if tracker.start_snapshot is not None:
                        photos.append(tracker.start_snapshot)
                    if tracker.end_snapshot is not None:
                        photos.append(tracker.end_snapshot)
                    
                    chosen_frame = None
                    if photos:
                        chosen_frame = random.choice(photos)
                    elif tracker.latest_frame is not None:
                        chosen_frame = tracker.latest_frame
                        
                    game.save_score_to_firebase(chosen_frame)

                # Desenha o menu interativo de Game Over por gestos
                draw_game_over(screen, fonts, game)
                
                # Layout fixo com 2 botões: REINICIAR (Morango) e MENU (Limão)
                game.btn_save = None
                target_re_x = SCREEN_W // 2 - 180
                target_me_x = SCREEN_W // 2 + 180
                target_y = 570
                
                if game.btn_restart is None:
                    game.btn_restart = Fruit(is_bomb=False)
                    game.btn_restart.fruit_type = 'morango'
                    game.btn_restart.x = target_re_x
                    game.btn_restart.y = target_y
                    game.btn_restart.radius = 48
                    game.btn_restart.rot_speed = 3.0
                else:
                    # Interpolação suave para nova posição
                    game.btn_restart.x = int(game.btn_restart.x * 0.88 + target_re_x * 0.12)
                    game.btn_restart.y = int(game.btn_restart.y * 0.88 + target_y * 0.12)
                    
                if game.btn_menu is None:
                    game.btn_menu = Fruit(is_bomb=False)
                    game.btn_menu.fruit_type = 'limao'
                    game.btn_menu.x = target_me_x
                    game.btn_menu.y = target_y
                    game.btn_menu.radius = 48
                    game.btn_menu.rot_speed = -2.5
                else:
                    # Interpolação suave para nova posição
                    game.btn_menu.x = int(game.btn_menu.x * 0.88 + target_me_x * 0.12)
                    game.btn_menu.y = int(game.btn_menu.y * 0.88 + target_y * 0.12)

                # Atualiza os ângulos das frutas dos botões
                if game.btn_restart:
                    game.btn_restart.angle += game.btn_restart.rot_speed
                if game.btn_menu:
                    game.btn_menu.angle += game.btn_menu.rot_speed

                # Desenha círculos com brilho neon ao redor das frutas de opção
                if game.btn_restart:
                    pulse_re = 5 + int(math.sin(pygame.time.get_ticks() * 0.008) * 3)
                    draw_glow_circle(screen, (220, 25, 55), (int(game.btn_restart.x), int(game.btn_restart.y)), game.btn_restart.radius + 2, glow=pulse_re)
                
                if game.btn_menu:
                    pulse_me = 5 + int(math.sin(pygame.time.get_ticks() * 0.008 + 2) * 3)
                    draw_glow_circle(screen, (200, 220, 20), (int(game.btn_menu.x), int(game.btn_menu.y)), game.btn_menu.radius + 2, glow=pulse_me)

                # Desenha as frutas dos botões
                if game.btn_restart:
                    game.btn_restart.draw(screen)
                if game.btn_menu:
                    game.btn_menu.draw(screen)

                # Rótulos de instrução sob as frutas
                if game.btn_restart:
                    lbl_re = get_restart_label(fonts['small'])
                    screen.blit(lbl_re, (game.btn_restart.x - lbl_re.get_width()//2, game.btn_restart.y + 55))
                
                if game.btn_menu:
                    lbl_me = get_menu_label(fonts['small'])
                    screen.blit(lbl_me, (game.btn_menu.x - lbl_me.get_width()//2, game.btn_menu.y + 55))

                # Atualiza e desenha partículas do menu se houverem
                if game.halves or game.particles:
                    game.halves = [h for h in game.halves if h.update()]
                    game.particles = [p for p in game.particles if p.update()]
                    for h in game.halves:
                        h.draw(screen)
                    for p in game.particles:
                        p.draw(screen)

                # Desenha o rastro do dedo por cima do Game Over para guiar o corte
                trail.draw(screen)

                # Verifica se o jogador fatiou alguma das opções por gestos
                if tip and trail.velocity() >= SLICE_VEL_MIN:
                    for seg_a, seg_b in trail.segments():
                        # Opção 1: REINICIAR (Morango)
                        if game.btn_restart and seg_circle_hit(seg_a, seg_b, (game.btn_restart.x, game.btn_restart.y), game.btn_restart.radius):
                            game.halves.append(FruitHalf(game.btn_restart, +1))
                            game.halves.append(FruitHalf(game.btn_restart, -1))
                            info = FRUIT_TYPES[game.btn_restart.fruit_type]
                            for _ in range(25):
                                game.particles.append(Particle(game.btn_restart.x, game.btn_restart.y, info['inner']))
                            for _ in range(10):
                                game.particles.append(Particle(game.btn_restart.x, game.btn_restart.y, info['color']))
                            
                            tracker.start_snapshot = tracker.latest_frame.copy() if tracker.latest_frame is not None else None
                            tracker.end_snapshot = None
                            hs = game.high_score
                            game.reset()
                            game.high_score = hs
                            game.started = True
                            game.btn_restart = None
                            game.btn_save = None
                            game.btn_menu = None
                            break
                        
                        # Opção 2: VOLTAR AO MENU (Limão)
                        elif game.btn_menu and seg_circle_hit(seg_a, seg_b, (game.btn_menu.x, game.btn_menu.y), game.btn_menu.radius):
                            game.halves.append(FruitHalf(game.btn_menu, +1))
                            game.halves.append(FruitHalf(game.btn_menu, -1))
                            info = FRUIT_TYPES[game.btn_menu.fruit_type]
                            for _ in range(25):
                                game.particles.append(Particle(game.btn_menu.x, game.btn_menu.y, info['inner']))
                            for _ in range(10):
                                game.particles.append(Particle(game.btn_menu.x, game.btn_menu.y, info['color']))
                            
                            tracker.start_snapshot = tracker.latest_frame.copy() if tracker.latest_frame is not None else None
                            tracker.end_snapshot = None
                            hs = game.high_score
                            game.reset()
                            game.high_score = hs
                            game.started = False
                            game.btn_restart = None
                            game.btn_save = None
                            game.btn_menu = None
                            break

        pygame.display.flip()

    tracker.release()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
