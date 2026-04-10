import pygame
import random
import sys
import math
import json
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Инициализация Pygame
pygame.init()
pygame.mixer.init()

# Константы
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 25
FPS = 60  # Базовый FPS для плавности
GAME_FPS = 12  # Скорость игры
GRID_WIDTH = WINDOW_WIDTH // CELL_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // CELL_SIZE

# Цветовые схемы
COLOR_SCHEMES = {
    'classic': {
        'bg_primary': (15, 20, 30),
        'bg_secondary': (25, 35, 50),
        'grid': (35, 45, 65),
        'snake_head': (100, 255, 100),
        'snake_mid': (50, 200, 50),
        'snake_tail': (30, 150, 30),
        'food': (255, 80, 80),
        'food_glow': (255, 150, 150),
        'bonus_gold': (255, 215, 0),
        'bonus_time': (100, 200, 255),
        'bonus_shield': (150, 100, 255),
        'text': (240, 240, 240),
        'accent': (100, 200, 255),
        'combo': (255, 100, 200)
    },
    'neon': {
        'bg_primary': (5, 10, 20),
        'bg_secondary': (15, 25, 45),
        'grid': (50, 80, 120),
        'snake_head': (0, 255, 255),
        'snake_mid': (0, 200, 200),
        'snake_tail': (0, 150, 150),
        'food': (255, 0, 128),
        'food_glow': (255, 100, 180),
        'bonus_gold': (255, 255, 0),
        'bonus_time': (0, 255, 128),
        'bonus_shield': (128, 0, 255),
        'text': (200, 255, 255),
        'accent': (0, 255, 200),
        'combo': (255, 0, 255)
    },
    'dark': {
        'bg_primary': (10, 10, 15),
        'bg_secondary': (20, 20, 30),
        'grid': (40, 40, 55),
        'snake_head': (255, 200, 100),
        'snake_mid': (255, 150, 50),
        'snake_tail': (255, 100, 0),
        'food': (100, 255, 100),
        'food_glow': (150, 255, 150),
        'bonus_gold': (255, 215, 0),
        'bonus_time': (100, 150, 255),
        'bonus_shield': (200, 100, 255),
        'text': (255, 255, 255),
        'accent': (255, 150, 100),
        'combo': (255, 100, 100)
    }
}

# Активная цветовая схема
CURRENT_SCHEME = 'classic'
colors = COLOR_SCHEMES[CURRENT_SCHEME]

# Направления
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


class BonusType(Enum):
    GOLD = "gold"  # Двойные очки
    TIME = "time"  # Замедление времени
    SHIELD = "shield"  # Защита от одного столкновения
    SPEED = "speed"  # Ускорение


@dataclass
class Bonus:
    type: BonusType
    position: Tuple[int, int]
    spawn_time: float
    duration: float = 10.0  # Время существования бонуса на поле
    
    @property
    def color(self):
        if self.type == BonusType.GOLD:
            return colors['bonus_gold']
        elif self.type == BonusType.TIME:
            return colors['bonus_time']
        elif self.type == BonusType.SHIELD:
            return colors['bonus_shield']
        else:  # SPEED
            return (255, 165, 0)


@dataclass
class Particle:
    """Частицы для эффектов"""
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: int
    max_life: int
    size: float
    particle_type: str = "normal"  # normal, spark, glow, trail
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        
        # Гравитация для некоторых типов
        if self.particle_type == "spark":
            self.vy += 0.1
        elif self.particle_type == "glow":
            self.size *= 0.95
        
        # Трение
        self.vx *= 0.98
        self.vy *= 0.98
        
        if self.particle_type == "trail":
            self.size = max(0.5, self.size * 0.9)
        else:
            self.size = max(1, int(self.size * (self.life / self.max_life)))
    
    def draw(self, surface):
        if self.life <= 0 or self.size < 0.5:
            return
            
        alpha = int(255 * (self.life / self.max_life))
        
        if self.particle_type == "trail":
            alpha //= 2
            
        color = (*self.color[:3], min(alpha, 255))
        size = int(self.size)
        
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        
        if self.particle_type == "spark":
            # Искры - квадратные
            pygame.draw.rect(s, color, (0, 0, size * 2, size * 2))
        elif self.particle_type == "glow":
            # Светящиеся - с градиентом
            for i in range(size, 0, -1):
                a = int(alpha * (i / size))
                c = (*self.color[:3], a)
                pygame.draw.circle(s, c, (size, size), i)
        else:
            # Обычные - круглые
            pygame.draw.circle(s, color, (size, size), size)
            
        surface.blit(s, (int(self.x - size), int(self.y - size)))


@dataclass
class SnakeSegment:
    """Для плавной интерполяции положения сегментов"""
    x: float
    y: float
    target_x: float
    target_y: float


class Snake:
    def __init__(self):
        self.reset()
        self.interpolation_factor = 0.3  # Плавность движения
        self.shield_active = False
        self.shield_timer = 0
        self.trail_particles = []
    
    def reset(self):
        start_x = GRID_WIDTH // 2 * CELL_SIZE
        start_y = GRID_HEIGHT // 2 * CELL_SIZE
        self.body = [(start_x, start_y), 
                     (start_x - CELL_SIZE, start_y), 
                     (start_x - 2 * CELL_SIZE, start_y)]
        self.smooth_body = [SnakeSegment(float(x), float(y), float(x), float(y)) 
                           for x, y in self.body]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.grow = False
        self.speed_boost = False
        self.shield_active = False
        self.shield_timer = 0
        self.move_counter = 0
    
    def set_next_direction(self, new_direction):
        # Запрещаем разворот на 180 градусов
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.next_direction = new_direction
    
    def update_direction(self):
        self.direction = self.next_direction
    
    def move(self):
        head_x, head_y = self.body[0]
        dir_x, dir_y = self.direction
        new_head = (head_x + dir_x * CELL_SIZE, head_y + dir_y * CELL_SIZE)
        
        self.body.insert(0, new_head)
        self.smooth_body.insert(0, SnakeSegment(
            float(head_x), float(head_y),
            float(new_head[0]), float(new_head[1])
        ))
        
        if not self.grow:
            self.body.pop()
            self.smooth_body.pop()
        else:
            self.grow = False
        
        self.move_counter += 1
        
        # Генерация следовых частиц
        if self.move_counter % 3 == 0 and len(self.body) > 3:
            tail = self.body[-1]
            self.trail_particles.append(Particle(
                x=tail[0] + CELL_SIZE // 2,
                y=tail[1] + CELL_SIZE // 2,
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(-0.5, 0.5),
                color=colors['snake_tail'],
                life=15,
                max_life=15,
                size=random.randint(3, 5),
                particle_type="trail"
            ))
    
    def update_smooth_positions(self):
        """Плавная интерполяция позиций сегментов"""
        for i, segment in enumerate(self.smooth_body):
            if i < len(self.body):
                target_x, target_y = self.body[i]
                segment.target_x = float(target_x)
                segment.target_y = float(target_y)
                
                # Интерполяция к целевой позиции
                segment.x += (segment.target_x - segment.x) * self.interpolation_factor
                segment.y += (segment.target_y - segment.y) * self.interpolation_factor
    
    def check_collision(self):
        head = self.body[0]
        
        # Проверка столкновения со стенами
        if (head[0] < 0 or head[0] >= WINDOW_WIDTH or 
            head[1] < 0 or head[1] >= WINDOW_HEIGHT):
            if self.shield_active:
                self.shield_active = False
                self.shield_timer = 0
                return False  # Щит спасает от столкновения
            return True
        
        # Проверка столкновения с собой
        if head in self.body[1:]:
            if self.shield_active:
                self.shield_active = False
                self.shield_timer = 0
                return False
            return True
        
        return False
    
    def activate_shield(self, duration: int = 300):  # duration в кадрах
        self.shield_active = True
        self.shield_timer = duration
    
    def update_shield(self):
        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False
    
    def get_color_for_segment(self, index, total_length):
        """Градиентный цвет для сегментов змейки"""
        ratio = index / max(1, total_length - 1)
        r = int(colors['snake_head'][0] * (1 - ratio) + colors['snake_tail'][0] * ratio)
        g = int(colors['snake_head'][1] * (1 - ratio) + colors['snake_tail'][1] * ratio)
        b = int(colors['snake_head'][2] * (1 - ratio) + colors['snake_tail'][2] * ratio)
        return (r, g, b)
    
    def draw(self, surface):
        self.update_smooth_positions()
        total_length = len(self.smooth_body)
        
        # Рисуем щит если активен
        if self.shield_active:
            head = self.smooth_body[0]
            shield_radius = CELL_SIZE // 2 + 8 + int(math.sin(pygame.time.get_ticks() / 100) * 3)
            shield_surface = pygame.Surface((shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)
            shield_alpha = int(150 + math.sin(pygame.time.get_ticks() / 50) * 50)
            pygame.draw.circle(shield_surface, (*colors['bonus_shield'], shield_alpha), 
                             (shield_radius, shield_radius), shield_radius, 3)
            surface.blit(shield_surface, 
                        (int(head.x) - shield_radius + CELL_SIZE // 2, 
                         int(head.y) - shield_radius + CELL_SIZE // 2))
        
        for i, segment in enumerate(self.smooth_body):
            color = self.get_color_for_segment(i, total_length)
            
            # Позиция для отрисовки
            draw_x = int(segment.x)
            draw_y = int(segment.y)
            
            # Рисуем сегмент с закругленными углами и тенью
            rect = pygame.Rect(draw_x + 2, draw_y + 2, CELL_SIZE - 4, CELL_SIZE - 4)
            
            # Тень
            shadow_rect = pygame.Rect(draw_x + 4, draw_y + 4, CELL_SIZE - 4, CELL_SIZE - 4)
            shadow_surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surface, (0, 0, 0, 80), shadow_rect, border_radius=6)
            surface.blit(shadow_surface, (draw_x, draw_y))
            
            # Основной сегмент
            if i == 0:
                # Голова
                pygame.draw.rect(surface, color, rect, border_radius=8)
                
                # Глаза с анимацией
                eye_blink = abs(math.sin(pygame.time.get_ticks() / 200)) > 0.1
                
                if self.direction == RIGHT:
                    eye1_pos = (draw_x + CELL_SIZE - 8, draw_y + 6)
                    eye2_pos = (draw_x + CELL_SIZE - 8, draw_y + CELL_SIZE - 10)
                elif self.direction == LEFT:
                    eye1_pos = (draw_x + 4, draw_y + 6)
                    eye2_pos = (draw_x + 4, draw_y + CELL_SIZE - 10)
                elif self.direction == UP:
                    eye1_pos = (draw_x + 6, draw_y + 4)
                    eye2_pos = (draw_x + CELL_SIZE - 10, draw_y + 4)
                else:  # DOWN
                    eye1_pos = (draw_x + 6, draw_y + CELL_SIZE - 8)
                    eye2_pos = (draw_x + CELL_SIZE - 10, draw_y + CELL_SIZE - 8)
                
                if eye_blink:
                    pygame.draw.circle(surface, (255, 255, 255), eye1_pos, 4)
                    pygame.draw.circle(surface, (255, 255, 255), eye2_pos, 4)
                    pygame.draw.circle(surface, (0, 0, 0), eye1_pos, 2)
                    pygame.draw.circle(surface, (0, 0, 0), eye2_pos, 2)
                else:
                    # Моргающие глаза - узкие линии
                    eye_size = 1 if self.direction in [LEFT, RIGHT] else 2
                    pygame.draw.ellipse(surface, (255, 255, 255), 
                                      (eye1_pos[0] - 3, eye1_pos[1] - eye_size, 6, eye_size * 2))
                    pygame.draw.ellipse(surface, (255, 255, 255), 
                                      (eye2_pos[0] - 3, eye2_pos[1] - eye_size, 6, eye_size * 2))
            else:
                # Тело
                pygame.draw.rect(surface, color, rect, border_radius=6)
            
            # Блик на каждом сегменте
            highlight_pos = (draw_x + CELL_SIZE // 3, draw_y + CELL_SIZE // 3)
            highlight_size = CELL_SIZE // 4
            highlight_surface = pygame.Surface((highlight_size * 2, highlight_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(highlight_surface, (255, 255, 255, 80), 
                             (highlight_size, highlight_size), highlight_size)
            surface.blit(highlight_surface, highlight_pos)
        
        # Рисуем следовые частицы
        for particle in self.trail_particles[:]:
            particle.update()
            particle.draw(surface)
            if particle.life <= 0:
                self.trail_particles.remove(particle)

class Food:
    def __init__(self):
        self.position = (0, 0)
        self.pulse = 0
        self.pulse_speed = 0.15
        self.randomize_position([])
        self.is_bonus = False
        self.bonus_type = None
    
    def randomize_position(self, snake_body):
        while True:
            x = random.randint(0, GRID_WIDTH - 1) * CELL_SIZE
            y = random.randint(0, GRID_HEIGHT - 1) * CELL_SIZE
            self.position = (x, y)
            
            # Проверяем, что еда не появилась на змейке
            if self.position not in snake_body:
                break
    
    def spawn_bonus(self, snake_body):
        """Создание бонуса"""
        self.is_bonus = True
        bonus_types = [BonusType.GOLD, BonusType.TIME, BonusType.SHIELD, BonusType.SPEED]
        weights = [0.4, 0.25, 0.2, 0.15]  # Вероятности появления
        self.bonus_type = random.choices(bonus_types, weights)[0]
        self.randomize_position(snake_body)
    
    def update(self):
        self.pulse += self.pulse_speed
        if self.pulse > math.pi * 2:
            self.pulse = 0
    
    def get_pulse_scale(self):
        return 1 + math.sin(self.pulse) * 0.2
    
    def draw(self, surface):
        center_x = self.position[0] + CELL_SIZE // 2
        center_y = self.position[1] + CELL_SIZE // 2
        base_radius = CELL_SIZE // 2 - 3
        
        # Пульсирующий эффект
        scale = self.get_pulse_scale()
        radius = int(base_radius * scale)
        
        if self.is_bonus and self.bonus_type:
            # Отрисовка бонуса
            bonus_color = colors[f'bonus_{self.bonus_type.value}'] if self.bonus_type != BonusType.SPEED else (255, 165, 0)
            
            # Вращающийся эффект для бонуса
            rotation = pygame.time.get_ticks() / 500
            for i in range(3):
                angle = rotation + i * (math.pi * 2 / 3)
                orb_x = center_x + math.cos(angle) * (radius + 5)
                orb_y = center_y + math.sin(angle) * (radius + 5)
                orb_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(orb_surface, (*bonus_color, 180), (5, 5), 5)
                surface.blit(orb_surface, (int(orb_x) - 5, int(orb_y) - 5))
            
            # Центральная иконка бонуса
            pygame.draw.circle(surface, bonus_color, (center_x, center_y), radius)
            
            # Символ бонуса в центре
            font = pygame.font.Font(None, 24)
            if self.bonus_type == BonusType.GOLD:
                symbol = font.render('2X', True, (255, 255, 255))
            elif self.bonus_type == BonusType.TIME:
                symbol = font.render('SLOW', True, (255, 255, 255))
            elif self.bonus_type == BonusType.SHIELD:
                symbol = font.render('🛡', True, (255, 255, 255))
            else:
                symbol = font.render('>>>', True, (255, 255, 255))
            
            symbol_rect = symbol.get_rect(center=(center_x, center_y))
            surface.blit(symbol, symbol_rect)
        else:
            # Обычная еда (яблоко)
            # Внешнее свечение
            glow_radius = radius + 10
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_alpha = int(120 * (1 + math.sin(self.pulse)) / 2)
            
            # Градиентное свечение
            for i in range(glow_radius, 0, -2):
                a = int(glow_alpha * (i / glow_radius))
                c = (*colors['food_glow'], a)
                pygame.draw.circle(glow_surface, c, (glow_radius, glow_radius), i)
            
            surface.blit(glow_surface, (center_x - glow_radius, center_y - glow_radius))
            
            # Основная часть еды (яблоко)
            apple_gradient = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for i in range(radius, 0, -1):
                ratio = i / radius
                r = int(colors['food'][0] * ratio + 255 * (1 - ratio))
                g = int(colors['food'][1] * ratio + 200 * (1 - ratio))
                b = int(colors['food'][2] * ratio + 200 * (1 - ratio))
                pygame.draw.circle(apple_gradient, (r, g, b), (radius, radius), i)
            surface.blit(apple_gradient, (center_x - radius, center_y - radius))
            
            # Блик
            highlight_pos = (center_x - radius // 3, center_y - radius // 3)
            pygame.draw.circle(surface, (255, 220, 220), highlight_pos, radius // 3)
            
            # Черенок
            stem_start = (center_x, center_y - radius + 2)
            stem_end = (center_x + 3, center_y - radius - 6)
            pygame.draw.line(surface, (100, 150, 50), stem_start, stem_end, 3)
            
            # Листик с анимацией
            leaf_angle = math.sin(pygame.time.get_ticks() / 300) * 0.2
            leaf_center = (stem_end[0] + 5, stem_end[1] - 3)
            leaf_surface = pygame.Surface((12, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(leaf_surface, (100, 180, 50), (0, 0, 12, 8))
            rotated_leaf = pygame.transform.rotate(leaf_surface, math.degrees(leaf_angle))
            surface.blit(rotated_leaf, (int(leaf_center[0] - 6), int(leaf_center[1] - 4)))

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Змейка - Enhanced Edition')
        self.clock = pygame.time.Clock()
        
        # Шрифты
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)
        
        self.snake = Snake()
        self.food = Food()
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.particles = []
        self.level = 1
        self.foods_eaten = 0
        
        # Бонусы и эффекты
        self.bonuses = []  # Активные бонусы
        self.bonus_spawn_timer = 0
        self.double_score_active = False
        self.double_score_timer = 0
        self.slow_motion_active = False
        self.slow_motion_timer = 0
        self.combo_count = 0
        self.combo_timer = 0
        
        # Загрузка звуков (опционально)
        self.sounds_enabled = True
        try:
            # Генерируем простые звуки
            self.eat_sound = self.generate_sound(440, 0.1)  # A4
            self.bonus_sound = self.generate_sound(880, 0.2)  # A5
            self.level_up_sound = self.generate_sound(660, 0.3)  # E5
            self.eat_sound.set_volume(0.3)
            self.bonus_sound.set_volume(0.4)
            self.level_up_sound.set_volume(0.4)
        except:
            self.sounds_enabled = False
    
    def generate_sound(self, frequency, duration):
        """Генерация простого звука"""
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = bytearray(n_samples * 2)
        for i in range(n_samples):
            value = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate) * (1 - i / n_samples))
            buf[i * 2] = value & 0xFF
            buf[i * 2 + 1] = (value >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))
    
    def create_particles(self, x, y, color, count=15, particle_type="normal"):
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y, 
                vx=random.uniform(-3, 3), 
                vy=random.uniform(-3, 3),
                color=color,
                life=random.randint(20, 40),
                max_life=40,
                size=random.randint(3, 6),
                particle_type=particle_type
            ))
    
    def spawn_bonus(self):
        """Спавн бонуса"""
        if random.random() < 0.3:  # 30% шанс
            self.food.spawn_bonus(self.snake.body)
            self.create_particles(
                self.food.position[0] + CELL_SIZE // 2,
                self.food.position[1] + CELL_SIZE // 2,
                colors['bonus_gold'],
                25,
                "glow"
            )
    
    def apply_bonus(self, bonus_type):
        """Применение эффекта бонуса"""
        if bonus_type == BonusType.GOLD:
            self.double_score_active = True
            self.double_score_timer = 300  # 5 секунд при 60 FPS
        elif bonus_type == BonusType.TIME:
            self.slow_motion_active = True
            self.slow_motion_timer = 300
        elif bonus_type == BonusType.SHIELD:
            self.snake.activate_shield(300)
        elif bonus_type == BonusType.SPEED:
            # Мгновенное ускорение без последствий
            self.score += 50
    
    def update_bonuses(self):
        """Обновление таймеров бонусов"""
        if self.double_score_active:
            self.double_score_timer -= 1
            if self.double_score_timer <= 0:
                self.double_score_active = False
        
        if self.slow_motion_active:
            self.slow_motion_timer -= 1
            if self.slow_motion_timer <= 0:
                self.slow_motion_active = False
        
        # Обновление щита змейки
        self.snake.update_shield()
        
        # Комбо таймер
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer <= 0:
                self.combo_count = 0
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_SPACE:
                        self.restart()
                    elif event.key == pygame.K_ESCAPE:
                        return False
                    elif event.key == pygame.K_1:
                        self.change_color_scheme('classic')
                    elif event.key == pygame.K_2:
                        self.change_color_scheme('neon')
                    elif event.key == pygame.K_3:
                        self.change_color_scheme('dark')
                else:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.snake.set_next_direction(UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.snake.set_next_direction(DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.snake.set_next_direction(LEFT)
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        self.snake.set_next_direction(RIGHT)
                    elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                        self.snake.speed_boost = True
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    self.snake.speed_boost = False
        
        return True
    
    def change_color_scheme(self, scheme_name):
        """Смена цветовой схемы"""
        global CURRENT_SCHEME, colors
        CURRENT_SCHEME = scheme_name
        colors = COLOR_SCHEMES[scheme_name]
    
    def update(self):
        if self.game_over:
            # Обновляем частицы даже в game over
            for particle in self.particles[:]:
                particle.update()
                if particle.life <= 0:
                    self.particles.remove(particle)
            return
        
        # Обновляем направление перед движением
        self.snake.update_direction()
        
        # Регулировка скорости с учетом замедления времени
        if self.slow_motion_active:
            current_fps = GAME_FPS * 0.7
        elif self.snake.speed_boost:
            current_fps = GAME_FPS * 1.5
        else:
            current_fps = GAME_FPS
        
        self.clock.tick(int(current_fps))
        
        self.snake.move()
        self.food.update()
        self.update_bonuses()
        
        # Обновляем частицы
        for particle in self.particles[:]:
            particle.update()
            if particle.life <= 0:
                self.particles.remove(particle)
        
        # Проверка столкновений
        if self.snake.check_collision():
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
            self.create_particles(
                self.snake.body[0][0] + CELL_SIZE // 2,
                self.snake.body[0][1] + CELL_SIZE // 2,
                colors['food'],
                50,
                "spark"
            )
            return
        
        # Проверка поедания еды
        if self.snake.body[0] == self.food.position:
            self.snake.grow = True
            
            # Комбо система
            if self.combo_timer > 0:
                self.combo_count += 1
            else:
                self.combo_count = 1
            self.combo_timer = 120  # 2 секунды на комбо
            
            # Подсчет очков с учетом бонусов
            base_points = 10 * self.level
            multiplier = 1
            if self.double_score_active:
                multiplier *= 2
            if self.combo_count >= 5:
                multiplier *= 2
            
            points = base_points * multiplier
            self.score += points
            self.foods_eaten += 1
            
            # Создаем эффект частиц
            center_x = self.food.position[0] + CELL_SIZE // 2
            center_y = self.food.position[1] + CELL_SIZE // 2
            
            if self.food.is_bonus:
                # Бонусные частицы
                bonus_color = colors[f'bonus_{self.food.bonus_type.value}'] if self.food.bonus_type != BonusType.SPEED else (255, 165, 0)
                self.create_particles(center_x, center_y, bonus_color, 30, "glow")
                self.apply_bonus(self.food.bonus_type)
                if self.sounds_enabled:
                    try:
                        self.bonus_sound.play()
                    except:
                        pass
                self.food.is_bonus = False
                self.food.bonus_type = None
            else:
                # Обычные частицы
                self.create_particles(center_x, center_y, colors['food'], 20, "normal")
                if self.sounds_enabled:
                    try:
                        self.eat_sound.play()
                    except:
                        pass
            
            # Повышение уровня каждые 5 съеденных яблок
            if self.foods_eaten % 5 == 0:
                self.level += 1
                if self.sounds_enabled:
                    try:
                        self.level_up_sound.play()
                    except:
                        pass
                # Эффект повышения уровня
                self.create_particles(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2, colors['accent'], 40, "glow")
            
            # Шанс спавна бонуса после каждой 3-й обычной еды
            if not self.food.is_bonus and self.foods_eaten % 3 == 0:
                self.spawn_bonus()
            else:
                self.food.randomize_position(self.snake.body)
    
    def draw_grid(self):
        """Рисуем фоновую сетку с эффектом параллакса"""
        # Анимированная сетка
        offset = (pygame.time.get_ticks() / 50) % CELL_SIZE
        
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            alpha = int(80 + math.sin((x / CELL_SIZE) + pygame.time.get_ticks() / 1000) * 20)
            color = (*colors['grid'][:3], alpha)
            surface = pygame.Surface((1, WINDOW_HEIGHT), pygame.SRCALPHA)
            surface.fill(color)
            self.screen.blit(surface, (x, 0))
        
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            alpha = int(80 + math.sin((y / CELL_SIZE) + pygame.time.get_ticks() / 1000) * 20)
            color = (*colors['grid'][:3], alpha)
            surface = pygame.Surface((WINDOW_WIDTH, 1), pygame.SRCALPHA)
            surface.fill(color)
            self.screen.blit(surface, (0, y))
    
    def draw_ui(self):
        """Рисуем интерфейс"""
        # Панель счета с градиентом
        score_bg = pygame.Surface((220, 70), pygame.SRCALPHA)
        gradient_colors = [
            (*colors['bg_secondary'], 200),
            (*colors['bg_secondary'], 150)
        ]
        for i in range(70):
            ratio = i / 70
            r = int(gradient_colors[0][0] * (1 - ratio) + gradient_colors[1][0] * ratio)
            g = int(gradient_colors[0][1] * (1 - ratio) + gradient_colors[1][1] * ratio)
            b = int(gradient_colors[0][2] * (1 - ratio) + gradient_colors[1][2] * ratio)
            a = int(gradient_colors[0][3] * (1 - ratio) + gradient_colors[1][3] * ratio)
            pygame.draw.line(score_bg, (r, g, b, a), (0, i), (220, i))
        
        self.screen.blit(score_bg, (10, 10))
        
        # Счет
        score_text = self.font_small.render(f'Счет: {self.score}', True, colors['text'])
        self.screen.blit(score_text, (20, 20))
        
        # Уровень с подсветкой
        level_color = colors['accent'] if self.level > 1 else colors['text']
        level_text = self.font_small.render(f'Уровень: {self.level}', True, level_color)
        self.screen.blit(level_text, (20, 45))
        
        # Индикаторы активных бонусов
        bonus_y = 70
        if self.double_score_active:
            bonus_text = self.font_small.render(f'2X: {self.double_score_timer // 60}с', True, colors['bonus_gold'])
            self.screen.blit(bonus_text, (20, bonus_y))
            bonus_y += 25
        
        if self.slow_motion_active:
            bonus_text = self.font_small.render(f'SLOW: {self.slow_motion_timer // 60}с', True, colors['bonus_time'])
            self.screen.blit(bonus_text, (20, bonus_y))
            bonus_y += 25
        
        if self.snake.shield_active:
            bonus_text = self.font_small.render(f'ЩИТ: {self.snake.shield_timer // 60}с', True, colors['bonus_shield'])
            self.screen.blit(bonus_text, (20, bonus_y))
        
        # Комбо индикатор
        if self.combo_count >= 3:
            combo_color = colors['combo']
            combo_text = self.font_medium.render(f'COMBO x{self.combo_count}!', True, combo_color)
            combo_rect = combo_text.get_rect(center=(WINDOW_WIDTH // 2, 40))
            
            # Пульсирующий эффект для комбо
            scale = 1 + math.sin(pygame.time.get_ticks() / 100) * 0.1
            combo_text = pygame.transform.scale(combo_text, 
                (int(combo_text.get_width() * scale), int(combo_text.get_height() * scale)))
            combo_rect = combo_text.get_rect(center=(WINDOW_WIDTH // 2, 40))
            self.screen.blit(combo_text, combo_rect)
        
        # Рекорд
        high_score_text = self.font_small.render(f'Рекорд: {self.high_score}', True, colors['text'])
        self.screen.blit(high_score_text, (WINDOW_WIDTH - 180, 20))
        
        # Подсказки
        hint_y = WINDOW_HEIGHT - 80
        hint_text = self.font_small.render('SHIFT - ускорение | 1,2,3 - цвета | ESC - выход', True, (100, 100, 100))
        self.screen.blit(hint_text, (WINDOW_WIDTH // 2 - hint_text.get_width() // 2, hint_y))
    
    def draw_game_over(self):
        """Рисуем экран проигрыша с анимацией"""
        # Затемнение экрана с пульсацией
        pulse = abs(math.sin(pygame.time.get_ticks() / 500)) * 50
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(200 + pulse)))
        self.screen.blit(overlay, (0, 0))
        
        # Текст Game Over с тенью
        game_over_text = self.font_large.render('GAME OVER', True, colors['food'])
        shadow_text = self.font_large.render('GAME OVER', True, (0, 0, 0))
        
        text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2 + 3, WINDOW_HEIGHT // 2 - 77))
        self.screen.blit(shadow_text, text_rect)
        
        text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80))
        self.screen.blit(game_over_text, text_rect)
        
        # Финальный счет
        score_text = self.font_medium.render(f'Счет: {self.score}', True, colors['text'])
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
        self.screen.blit(score_text, score_rect)
        
        # Рекорд
        if self.score >= self.high_score and self.score > 0:
            record_text = self.font_medium.render('НОВЫЙ РЕКОРД!', True, colors['accent'])
            # Эффект свечения для нового рекорда
            glow = abs(math.sin(pygame.time.get_ticks() / 200)) * 100
            record_glow = self.font_medium.render('НОВЫЙ РЕКОРД!', True, (255, 255, 255))
            for i in range(3, 0, -1):
                glow_surf = pygame.Surface((record_glow.get_width() + i * 2, record_glow.get_height() + i * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*colors['accent'], int(50 / i)), 
                                 (glow_surf.get_width() // 2, glow_surf.get_height() // 2), i * 5)
        else:
            record_text = self.font_medium.render(f'Рекорд: {self.high_score}', True, colors['text'])
        
        record_rect = record_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
        self.screen.blit(record_text, record_rect)
        
        # Инструкция
        restart_text = self.font_small.render('Нажмите ПРОБЕЛ для рестарта', True, colors['text'])
        restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 90))
        self.screen.blit(restart_text, restart_rect)
        
        escape_text = self.font_small.render('ESC для выхода', True, (150, 150, 150))
        escape_rect = escape_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 130))
        self.screen.blit(escape_text, escape_rect)
        
        # Подсказка о смене темы
        theme_text = self.font_small.render('1, 2, 3 - сменить цветовую схему', True, (100, 100, 100))
        theme_rect = theme_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 170))
        self.screen.blit(theme_text, theme_rect)
    
    def draw(self):
        self.screen.fill(colors['bg_primary'])
        
        # Рисуем сетку
        self.draw_grid()
        
        self.food.draw(self.screen)
        self.snake.draw(self.screen)
        
        # Рисуем частицы
        for particle in self.particles:
            particle.draw(self.screen)
        
        # Рисуем интерфейс
        self.draw_ui()
        
        if self.game_over:
            self.draw_game_over()
        
        pygame.display.flip()
    
    def restart(self):
        self.snake.reset()
        self.food = Food()
        self.score = 0
        self.level = 1
        self.foods_eaten = 0
        self.game_over = False
        self.particles = []
        self.double_score_active = False
        self.slow_motion_active = False
        self.combo_count = 0
        self.combo_timer = 0
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            # Базовый FPS для плавности UI
            if not self.snake.speed_boost:
                self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = Game()
    game.run()
