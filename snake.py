import pygame
import random
import sys
import math

# Инициализация Pygame
pygame.init()

# Константы
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 25
FPS = 12
GRID_WIDTH = WINDOW_WIDTH // CELL_SIZE
GRID_HEIGHT = WINDOW_HEIGHT // CELL_SIZE

# Цвета
BG_COLOR = (15, 20, 30)
GRID_COLOR = (25, 35, 50)
SNAKE_HEAD_COLOR = (100, 255, 100)
SNAKE_BODY_COLOR = (50, 200, 50)
SNAKE_GRADIENT_END = (30, 150, 30)
FOOD_COLOR = (255, 80, 80)
FOOD_GLOW_COLOR = (255, 150, 150)
TEXT_COLOR = (240, 240, 240)
SCORE_BG_COLOR = (30, 40, 50, 200)
GAME_OVER_BG_COLOR = (0, 0, 0, 220)
ACCENT_COLOR = (100, 200, 255)

# Направления
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

class Particle:
    """Частицы для эффектов"""
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.life = random.randint(20, 40)
        self.max_life = self.life
        self.size = random.randint(3, 6)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(1, int(self.size * (self.life / self.max_life)))
    
    def draw(self, surface):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            color = (*self.color[:3], alpha)
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (self.size, self.size), self.size)
            surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))

class Snake:
    def __init__(self):
        self.reset()
    
    def reset(self):
        start_x = GRID_WIDTH // 2 * CELL_SIZE
        start_y = GRID_HEIGHT // 2 * CELL_SIZE
        self.body = [(start_x, start_y), 
                     (start_x - CELL_SIZE, start_y), 
                     (start_x - 2 * CELL_SIZE, start_y)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.grow = False
        self.speed_boost = False
    
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
        
        if not self.grow:
            self.body.pop()
        else:
            self.grow = False
    
    def check_collision(self):
        head = self.body[0]
        
        # Проверка столкновения со стенами
        if (head[0] < 0 or head[0] >= WINDOW_WIDTH or 
            head[1] < 0 or head[1] >= WINDOW_HEIGHT):
            return True
        
        # Проверка столкновения с собой
        if head in self.body[1:]:
            return True
        
        return False
    
    def get_color_for_segment(self, index, total_length):
        """Градиентный цвет для сегментов змейки"""
        ratio = index / max(1, total_length - 1)
        r = int(SNAKE_HEAD_COLOR[0] * (1 - ratio) + SNAKE_GRADIENT_END[0] * ratio)
        g = int(SNAKE_HEAD_COLOR[1] * (1 - ratio) + SNAKE_GRADIENT_END[1] * ratio)
        b = int(SNAKE_HEAD_COLOR[2] * (1 - ratio) + SNAKE_GRADIENT_END[2] * ratio)
        return (r, g, b)
    
    def draw(self, surface):
        total_length = len(self.body)
        for i, segment in enumerate(self.body):
            color = self.get_color_for_segment(i, total_length)
            
            # Рисуем сегмент с закругленными углами
            rect = pygame.Rect(segment[0] + 2, segment[1] + 2, CELL_SIZE - 4, CELL_SIZE - 4)
            
            # Для головы рисуем глаза
            if i == 0:
                pygame.draw.rect(surface, color, rect, border_radius=8)
                
                # Глаза
                eye_offset_x = 0
                eye_offset_y = 0
                if self.direction == RIGHT:
                    eye_offset_x = 4
                    eye1_pos = (segment[0] + CELL_SIZE - 8, segment[1] + 6)
                    eye2_pos = (segment[0] + CELL_SIZE - 8, segment[1] + CELL_SIZE - 10)
                elif self.direction == LEFT:
                    eye_offset_x = -4
                    eye1_pos = (segment[0] + 4, segment[1] + 6)
                    eye2_pos = (segment[0] + 4, segment[1] + CELL_SIZE - 10)
                elif self.direction == UP:
                    eye_offset_y = -4
                    eye1_pos = (segment[0] + 6, segment[1] + 4)
                    eye2_pos = (segment[0] + CELL_SIZE - 10, segment[1] + 4)
                else:  # DOWN
                    eye_offset_y = 4
                    eye1_pos = (segment[0] + 6, segment[1] + CELL_SIZE - 8)
                    eye2_pos = (segment[0] + CELL_SIZE - 10, segment[1] + CELL_SIZE - 8)
                
                pygame.draw.circle(surface, (255, 255, 255), eye1_pos, 4)
                pygame.draw.circle(surface, (255, 255, 255), eye2_pos, 4)
                pygame.draw.circle(surface, (0, 0, 0), eye1_pos, 2)
                pygame.draw.circle(surface, (0, 0, 0), eye2_pos, 2)
            else:
                pygame.draw.rect(surface, color, rect, border_radius=6)
            
            # Блик на каждом сегменте
            highlight_rect = pygame.Rect(segment[0] + 4, segment[1] + 4, CELL_SIZE // 3, CELL_SIZE // 3)
            highlight_surface = pygame.Surface((CELL_SIZE // 3, CELL_SIZE // 3), pygame.SRCALPHA)
            pygame.draw.circle(highlight_surface, (255, 255, 255, 60), (CELL_SIZE // 6, CELL_SIZE // 6), CELL_SIZE // 6)
            surface.blit(highlight_surface, (segment[0] + 4, segment[1] + 4))

class Food:
    def __init__(self):
        self.position = (0, 0)
        self.pulse = 0
        self.pulse_speed = 0.1
        self.randomize_position([])
    
    def randomize_position(self, snake_body):
        while True:
            x = random.randint(0, GRID_WIDTH - 1) * CELL_SIZE
            y = random.randint(0, GRID_HEIGHT - 1) * CELL_SIZE
            self.position = (x, y)
            
            # Проверяем, что еда не появилась на змейке
            if self.position not in snake_body:
                break
    
    def update(self):
        self.pulse += self.pulse_speed
        if self.pulse > math.pi * 2:
            self.pulse = 0
    
    def get_pulse_scale(self):
        return 1 + math.sin(self.pulse) * 0.15
    
    def draw(self, surface):
        center_x = self.position[0] + CELL_SIZE // 2
        center_y = self.position[1] + CELL_SIZE // 2
        base_radius = CELL_SIZE // 2 - 3
        
        # Пульсирующий эффект
        scale = self.get_pulse_scale()
        radius = int(base_radius * scale)
        
        # Внешнее свечение
        glow_radius = radius + 8
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_alpha = int(100 * (1 + math.sin(self.pulse)) / 2)
        pygame.draw.circle(glow_surface, (*FOOD_GLOW_COLOR, glow_alpha), (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (center_x - glow_radius, center_y - glow_radius))
        
        # Основная часть еды (яблоко)
        pygame.draw.circle(surface, FOOD_COLOR, (center_x, center_y), radius)
        
        # Блик
        highlight_pos = (center_x - radius // 3, center_y - radius // 3)
        pygame.draw.circle(surface, (255, 200, 200), highlight_pos, radius // 3)
        
        # Черенок
        stem_start = (center_x, center_y - radius + 2)
        stem_end = (center_x + 3, center_y - radius - 5)
        pygame.draw.line(surface, (100, 150, 50), stem_start, stem_end, 2)
        
        # Листик
        leaf_center = (stem_end[0] + 4, stem_end[1] - 2)
        pygame.draw.ellipse(surface, (100, 180, 50), 
                          (leaf_center[0] - 4, leaf_center[1] - 3, 8, 6))

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
        
        # Загрузка звуков (опционально)
        self.sounds_enabled = True
        try:
            self.eat_sound = pygame.mixer.Sound(buffer=bytes([128] * 44100))
            self.eat_sound.set_volume(0.3)
        except:
            self.sounds_enabled = False
    
    def create_particles(self, x, y, color, count=15):
        for _ in range(count):
            self.particles.append(Particle(x, y, color))
    
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
        
        # Регулировка скорости
        current_fps = FPS * 1.5 if self.snake.speed_boost else FPS
        self.clock.tick(current_fps)
        
        self.snake.move()
        self.food.update()
        
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
            return
        
        # Проверка поедания еды
        if self.snake.body[0] == self.food.position:
            self.snake.grow = True
            points = 10 * self.level
            self.score += points
            self.foods_eaten += 1
            
            # Создаем эффект частиц
            center_x = self.food.position[0] + CELL_SIZE // 2
            center_y = self.food.position[1] + CELL_SIZE // 2
            self.create_particles(center_x, center_y, FOOD_COLOR, 20)
            
            # Воспроизводим звук
            if self.sounds_enabled:
                try:
                    self.eat_sound.play()
                except:
                    pass
            
            # Повышение уровня каждые 5 съеденных яблок
            if self.foods_eaten % 5 == 0:
                self.level += 1
            
            self.food.randomize_position(self.snake.body)
    
    def draw_grid(self):
        """Рисуем фоновую сетку"""
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))
    
    def draw_ui(self):
        """Рисуем интерфейс"""
        # Панель счета
        score_bg = pygame.Surface((200, 50), pygame.SRCALPHA)
        score_bg.fill(SCORE_BG_COLOR)
        self.screen.blit(score_bg, (10, 10))
        
        score_text = self.font_small.render(f'Счет: {self.score}', True, TEXT_COLOR)
        self.screen.blit(score_text, (20, 20))
        
        # Уровень
        level_text = self.font_small.render(f'Уровень: {self.level}', True, ACCENT_COLOR)
        self.screen.blit(level_text, (20, 50))
        
        # Рекорд
        high_score_text = self.font_small.render(f'Рекорд: {self.high_score}', True, TEXT_COLOR)
        self.screen.blit(high_score_text, (WINDOW_WIDTH - 180, 20))
        
        # Подсказка про ускорение
        boost_text = self.font_small.render('SHIFT - ускорение', True, (150, 150, 150))
        self.screen.blit(boost_text, (WINDOW_WIDTH - 180, 50))
    
    def draw_game_over(self):
        """Рисуем экран проигрыша"""
        # Затемнение экрана
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_BG_COLOR)
        self.screen.blit(overlay, (0, 0))
        
        # Текст Game Over
        game_over_text = self.font_large.render('GAME OVER', True, FOOD_COLOR)
        text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80))
        self.screen.blit(game_over_text, text_rect)
        
        # Финальный счет
        score_text = self.font_medium.render(f'Счет: {self.score}', True, TEXT_COLOR)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20))
        self.screen.blit(score_text, score_rect)
        
        # Рекорд
        if self.score >= self.high_score and self.score > 0:
            record_text = self.font_medium.render('НОВЫЙ РЕКОРД!', True, ACCENT_COLOR)
        else:
            record_text = self.font_medium.render(f'Рекорд: {self.high_score}', True, TEXT_COLOR)
        record_rect = record_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30))
        self.screen.blit(record_text, record_rect)
        
        # Инструкция
        restart_text = self.font_small.render('Нажмите ПРОБЕЛ для рестарта', True, TEXT_COLOR)
        restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 90))
        self.screen.blit(restart_text, restart_rect)
        
        escape_text = self.font_small.render('ESC для выхода', True, (150, 150, 150))
        escape_rect = escape_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 130))
        self.screen.blit(escape_text, escape_rect)
    
    def draw(self):
        self.screen.fill(BG_COLOR)
        
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
        self.food.randomize_position([])
        self.score = 0
        self.level = 1
        self.foods_eaten = 0
        self.game_over = False
        self.particles = []
    
    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            if not self.snake.speed_boost:
                self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = Game()
    game.run()
