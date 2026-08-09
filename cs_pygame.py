"""
Counter-Strike style top-down shooter built with Pygame.

Controls:
    WASD        - Move
    Mouse       - Aim
    Left Click  - Shoot
    R           - Restart after death
    ESC         - Quit

Run:
    pip install pygame
    python cs_pygame.py
"""

import pygame
import random
import math
import sys

# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
pygame.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Py-Strike")
clock = pygame.time.Clock()
FPS = 60

font_small = pygame.font.SysFont("consolas", 20)
font_big = pygame.font.SysFont("consolas", 60, bold=True)
font_med = pygame.font.SysFont("consolas", 32, bold=True)

# Colors
BG_COLOR = (40, 42, 46)
FLOOR_COLOR = (58, 61, 66)
WALL_COLOR = (90, 90, 95)
PLAYER_COLOR = (80, 160, 255)
ENEMY_COLOR = (220, 70, 70)
BULLET_COLOR = (255, 230, 120)
ENEMY_BULLET_COLOR = (255, 130, 90)
WHITE = (240, 240, 240)
GREEN = (80, 220, 120)
RED = (220, 70, 70)
BLACK = (10, 10, 10)


# ----------------------------------------------------------------------
# Walls / Map
# ----------------------------------------------------------------------
def build_walls():
    walls = []
    border = 20
    walls.append(pygame.Rect(0, 0, WIDTH, border))
    walls.append(pygame.Rect(0, HEIGHT - border, WIDTH, border))
    walls.append(pygame.Rect(0, 0, border, HEIGHT))
    walls.append(pygame.Rect(WIDTH - border, 0, border, HEIGHT))

    # Some cover / map layout (like bombsite crates)
    walls.append(pygame.Rect(150, 150, 160, 30))
    walls.append(pygame.Rect(150, 150, 30, 140))
    walls.append(pygame.Rect(700, 520, 160, 30))
    walls.append(pygame.Rect(820, 380, 30, 170))
    walls.append(pygame.Rect(440, 300, 120, 30))
    walls.append(pygame.Rect(440, 300, 30, 120))
    walls.append(pygame.Rect(600, 120, 30, 160))
    walls.append(pygame.Rect(250, 480, 140, 30))
    return walls


WALLS = build_walls()


def collides_wall(rect):
    for w in WALLS:
        if rect.colliderect(w):
            return True
    return False


def line_hits_wall(x1, y1, x2, y2):
    """Cheap segment vs wall check by sampling points along the line."""
    dist = math.hypot(x2 - x1, y2 - y1)
    steps = max(1, int(dist / 8))
    for i in range(steps + 1):
        t = i / steps
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        for w in WALLS:
            if w.collidepoint(px, py):
                return True
    return False


# ----------------------------------------------------------------------
# Entities
# ----------------------------------------------------------------------
class Bullet:
    def __init__(self, x, y, angle, owner, speed=14, color=BULLET_COLOR, damage=20):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.owner = owner  # "player" or "enemy"
        self.color = color
        self.damage = damage
        self.radius = 4
        self.alive = True

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        if self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT:
            self.alive = False
            return
        for w in WALLS:
            if w.collidepoint(self.x, self.y):
                self.alive = False
                return

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 16
        self.speed = 4.2
        self.hp = 100
        self.max_hp = 100
        self.ammo = 12
        self.mag_size = 12
        self.reserve = 60
        self.reloading = False
        self.reload_timer = 0
        self.reload_time = 60
        self.fire_cooldown = 0
        self.fire_rate = 10  # frames between shots
        self.kills = 0
        self.angle = 0

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)

    def move(self, keys):
        dx = dy = 0
        if keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_s]:
            dy += 1
        if keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_d]:
            dx += 1
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed

        test_rect = pygame.Rect(new_x - self.radius, self.y - self.radius,
                                 self.radius * 2, self.radius * 2)
        if not collides_wall(test_rect):
            self.x = new_x
        test_rect = pygame.Rect(self.x - self.radius, new_y - self.radius,
                                 self.radius * 2, self.radius * 2)
        if not collides_wall(test_rect):
            self.y = new_y

    def update(self, mouse_pos):
        self.angle = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                needed = self.mag_size - self.ammo
                take = min(needed, self.reserve)
                self.ammo += take
                self.reserve -= take
                self.reloading = False

    def try_shoot(self, bullets):
        if self.reloading or self.fire_cooldown > 0 or self.ammo <= 0:
            return
        self.ammo -= 1
        self.fire_cooldown = self.fire_rate
        spread = random.uniform(-0.03, 0.03)
        bx = self.x + math.cos(self.angle) * (self.radius + 5)
        by = self.y + math.sin(self.angle) * (self.radius + 5)
        bullets.append(Bullet(bx, by, self.angle + spread, "player"))

    def try_reload(self):
        if not self.reloading and self.ammo < self.mag_size and self.reserve > 0:
            self.reloading = True
            self.reload_timer = self.reload_time

    def draw(self, surf):
        pygame.draw.circle(surf, PLAYER_COLOR, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, BLACK, (int(self.x), int(self.y)), self.radius, 2)
        # gun barrel
        gx = self.x + math.cos(self.angle) * (self.radius + 14)
        gy = self.y + math.sin(self.angle) * (self.radius + 14)
        pygame.draw.line(surf, WHITE, (self.x, self.y), (gx, gy), 4)


class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 16
        self.speed = 1.8
        self.hp = 60
        self.max_hp = 60
        self.fire_cooldown = random.randint(20, 60)
        self.state_timer = 0
        self.strafe_dir = random.choice([-1, 1])
        self.alive = True

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)

    def update(self, player, bullets):
        dist = math.hypot(player.x - self.x, player.y - self.y)
        angle_to_player = math.atan2(player.y - self.y, player.x - self.x)
        can_see = not line_hits_wall(self.x, self.y, player.x, player.y)

        # Movement: approach until mid range, then strafe
        if can_see:
            if dist > 260:
                dx = math.cos(angle_to_player) * self.speed
                dy = math.sin(angle_to_player) * self.speed
            elif dist < 140:
                dx = -math.cos(angle_to_player) * self.speed
                dy = -math.sin(angle_to_player) * self.speed
            else:
                perp = angle_to_player + math.pi / 2
                dx = math.cos(perp) * self.speed * self.strafe_dir
                dy = math.sin(perp) * self.speed * self.strafe_dir
        else:
            dx = math.cos(angle_to_player) * self.speed * 0.6
            dy = math.sin(angle_to_player) * self.speed * 0.6

        self.state_timer -= 1
        if self.state_timer <= 0:
            self.strafe_dir = random.choice([-1, 1])
            self.state_timer = random.randint(40, 100)

        new_x = self.x + dx
        new_y = self.y + dy
        test_rect = pygame.Rect(new_x - self.radius, self.y - self.radius,
                                 self.radius * 2, self.radius * 2)
        if not collides_wall(test_rect):
            self.x = new_x
        test_rect = pygame.Rect(self.x - self.radius, new_y - self.radius,
                                 self.radius * 2, self.radius * 2)
        if not collides_wall(test_rect):
            self.y = new_y

        # keep on screen
        self.x = max(30, min(WIDTH - 30, self.x))
        self.y = max(30, min(HEIGHT - 30, self.y))

        # Shooting
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        elif can_see and dist < 500:
            self.fire_cooldown = random.randint(45, 90)
            spread = random.uniform(-0.09, 0.09)
            bx = self.x + math.cos(angle_to_player) * (self.radius + 5)
            by = self.y + math.sin(angle_to_player) * (self.radius + 5)
            bullets.append(Bullet(bx, by, angle_to_player + spread, "enemy",
                                   speed=10, color=ENEMY_BULLET_COLOR, damage=8))

    def draw(self, surf):
        pygame.draw.circle(surf, ENEMY_COLOR, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, BLACK, (int(self.x), int(self.y)), self.radius, 2)
        # health bar
        bar_w = 34
        hp_ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surf, BLACK, (self.x - bar_w / 2, self.y - self.radius - 12, bar_w, 6))
        pygame.draw.rect(surf, RED, (self.x - bar_w / 2, self.y - self.radius - 12, bar_w * hp_ratio, 6))


# ----------------------------------------------------------------------
# Spawning
# ----------------------------------------------------------------------
def spawn_enemy():
    for _ in range(30):
        x = random.randint(60, WIDTH - 60)
        y = random.randint(60, HEIGHT - 60)
        r = pygame.Rect(x - 16, y - 16, 32, 32)
        if not collides_wall(r) and math.hypot(x - player.x, y - player.y) > 220:
            return Enemy(x, y)
    return Enemy(WIDTH - 60, 60)


def draw_map(surf):
    surf.fill(FLOOR_COLOR)
    for w in WALLS:
        pygame.draw.rect(surf, WALL_COLOR, w)
        pygame.draw.rect(surf, BLACK, w, 1)


def draw_hud(surf, player, wave):
    # Health bar
    pygame.draw.rect(surf, BLACK, (20, HEIGHT - 50, 210, 26))
    hp_ratio = max(0, player.hp / player.max_hp)
    color = GREEN if hp_ratio > 0.3 else RED
    pygame.draw.rect(surf, color, (23, HEIGHT - 47, 204 * hp_ratio, 20))
    hp_text = font_small.render(f"HP {max(0, int(player.hp))}/{player.max_hp}", True, WHITE)
    surf.blit(hp_text, (28, HEIGHT - 46))

    # Ammo
    ammo_str = "RELOADING..." if player.reloading else f"{player.ammo} / {player.reserve}"
    ammo_text = font_med.render(ammo_str, True, WHITE)
    surf.blit(ammo_text, (WIDTH - ammo_text.get_width() - 25, HEIGHT - 48))

    # Kills / wave
    k_text = font_small.render(f"Kills: {player.kills}    Wave: {wave}", True, WHITE)
    surf.blit(k_text, (20, 20))

    # crosshair helper text
    reload_hint = font_small.render("R: Reload", True, (170, 170, 170))
    surf.blit(reload_hint, (WIDTH - reload_hint.get_width() - 25, HEIGHT - 75))


def draw_crosshair(surf, pos):
    x, y = pos
    pygame.draw.line(surf, WHITE, (x - 10, y), (x - 3, y), 2)
    pygame.draw.line(surf, WHITE, (x + 3, y), (x + 10, y), 2)
    pygame.draw.line(surf, WHITE, (x, y - 10), (x, y - 3), 2)
    pygame.draw.line(surf, WHITE, (x, y + 3), (x, y + 10), 2)


def reset_game():
    global player, enemies, bullets, wave, game_over, spawn_timer
    player = Player(WIDTH // 2, HEIGHT // 2)
    enemies = []
    bullets = []
    wave = 1
    game_over = False
    spawn_timer = 0
    for _ in range(3):
        enemies.append(spawn_enemy())


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
player = None
enemies = []
bullets = []
wave = 1
game_over = False
spawn_timer = 0
reset_game()

pygame.mouse.set_visible(False)
shooting_held = False

running = True
while running:
    clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r:
                if game_over:
                    reset_game()
                else:
                    player.try_reload()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            shooting_held = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            shooting_held = False

    if not game_over:
        keys = pygame.key.get_pressed()
        player.move(keys)
        player.update(mouse_pos)

        if shooting_held:
            player.try_shoot(bullets)

        for e in enemies:
            e.update(player, bullets)

        for b in bullets:
            b.update()

        # bullet collisions
        for b in bullets[:]:
            if not b.alive:
                bullets.remove(b)
                continue
            if b.owner == "player":
                for e in enemies[:]:
                    if e.rect().collidepoint(b.x, b.y):
                        e.hp -= b.damage
                        b.alive = False
                        if e.hp <= 0:
                            enemies.remove(e)
                            player.kills += 1
                        break
            elif b.owner == "enemy":
                if player.rect().collidepoint(b.x, b.y):
                    player.hp -= b.damage
                    b.alive = False

        bullets = [b for b in bullets if b.alive]

        if player.hp <= 0:
            game_over = True

        # next wave
        if len(enemies) == 0:
            wave += 1
            for _ in range(2 + wave):
                enemies.append(spawn_enemy())

    # ---------------- draw ----------------
    draw_map(screen)
    for w_ in WALLS[4:]:
        pass  # walls already drawn in draw_map

    for b in bullets:
        b.draw(screen)
    for e in enemies:
        e.draw(screen)
    if player.hp > 0:
        player.draw(screen)

    draw_hud(screen, player, wave)
    draw_crosshair(screen, mouse_pos)

    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        go_text = font_big.render("YOU DIED", True, RED)
        screen.blit(go_text, (WIDTH / 2 - go_text.get_width() / 2, HEIGHT / 2 - 80))
        stat_text = font_med.render(f"Kills: {player.kills}   Wave reached: {wave}", True, WHITE)
        screen.blit(stat_text, (WIDTH / 2 - stat_text.get_width() / 2, HEIGHT / 2))
        hint_text = font_small.render("Press R to restart, ESC to quit", True, (200, 200, 200))
        screen.blit(hint_text, (WIDTH / 2 - hint_text.get_width() / 2, HEIGHT / 2 + 60))

    pygame.display.flip()

pygame.quit()
sys.exit()
