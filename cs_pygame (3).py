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
GOLD = (240, 200, 60)
AMMO_CRATE_COLOR = (210, 170, 60)
SHOP_BG = (25, 26, 30)


# ----------------------------------------------------------------------
# Walls / Map
# ----------------------------------------------------------------------
def generate_walls():
    """Randomized border + interior cover layout. Leaves a clear zone in the
    center so the player never spawns inside a wall."""
    walls = []
    border = 20
    walls.append(pygame.Rect(0, 0, WIDTH, border))
    walls.append(pygame.Rect(0, HEIGHT - border, WIDTH, border))
    walls.append(pygame.Rect(0, 0, border, HEIGHT))
    walls.append(pygame.Rect(WIDTH - border, 0, border, HEIGHT))

    center_clear = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 100, 200, 200)
    thickness = 30
    lengths = [100, 120, 140, 160, 180]

    placed = []
    target_pieces = random.randint(6, 10)
    attempts = 0
    while len(placed) < target_pieces and attempts < 300:
        attempts += 1
        length = random.choice(lengths)
        horizontal = random.choice([True, False])
        if horizontal:
            x = random.randint(70, WIDTH - 70 - length)
            y = random.randint(70, HEIGHT - 70 - thickness)
            rect = pygame.Rect(x, y, length, thickness)
        else:
            x = random.randint(70, WIDTH - 70 - thickness)
            y = random.randint(70, HEIGHT - 70 - length)
            rect = pygame.Rect(x, y, thickness, length)

        if rect.colliderect(center_clear):
            continue
        if any(rect.inflate(50, 50).colliderect(p) for p in placed):
            continue
        placed.append(rect)

    walls.extend(placed)
    return walls


WALLS = generate_walls()


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
        self.money = 50

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


class AmmoPickup:
    """A random ammo crate dropped each wave. Walk over it to collect."""
    def __init__(self, x, y, amount):
        self.x = x
        self.y = y
        self.amount = amount
        self.radius = 12
        self.bob = random.uniform(0, math.pi * 2)

    def rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                            self.radius * 2, self.radius * 2)

    def draw(self, surf):
        self.bob += 0.08
        offset = math.sin(self.bob) * 3
        r = pygame.Rect(self.x - 14, self.y - 10 + offset, 28, 20)
        pygame.draw.rect(surf, AMMO_CRATE_COLOR, r, border_radius=3)
        pygame.draw.rect(surf, BLACK, r, 2, border_radius=3)
        txt = font_small.render(str(self.amount), True, BLACK)
        surf.blit(txt, (self.x - txt.get_width() / 2, self.y - 9 + offset))


# ----------------------------------------------------------------------
# Spawning
# ----------------------------------------------------------------------
def spawn_pickup():
    for _ in range(30):
        x = random.randint(60, WIDTH - 60)
        y = random.randint(60, HEIGHT - 60)
        r = pygame.Rect(x - 14, y - 14, 28, 28)
        if not collides_wall(r):
            amount = random.choice([10, 15, 20, 25, 30])
            return AmmoPickup(x, y, amount)
    return AmmoPickup(WIDTH // 2, HEIGHT // 2, 15)


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

    # Kills / wave / money
    k_text = font_small.render(f"Kills: {player.kills}    Wave: {wave}", True, WHITE)
    surf.blit(k_text, (20, 20))
    m_text = font_small.render(f"${player.money}", True, GOLD)
    surf.blit(m_text, (20, 46))

    # crosshair helper text
    reload_hint = font_small.render("R: Reload", True, (170, 170, 170))
    surf.blit(reload_hint, (WIDTH - reload_hint.get_width() - 25, HEIGHT - 75))


def draw_crosshair(surf, pos):
    x, y = pos
    pygame.draw.line(surf, WHITE, (x - 10, y), (x - 3, y), 2)
    pygame.draw.line(surf, WHITE, (x + 3, y), (x + 10, y), 2)
    pygame.draw.line(surf, WHITE, (x, y - 10), (x, y - 3), 2)
    pygame.draw.line(surf, WHITE, (x, y + 3), (x, y + 10), 2)


SHOP_ITEMS = [
    {"key": "1", "name": "Buy 30 Ammo", "cost": 25},
    {"key": "2", "name": "Heal 50 HP", "cost": 30},
    {"key": "3", "name": "+1 Mag Size (perm)", "cost": 120},
    {"key": "4", "name": "Faster Fire Rate", "cost": 150},
]


def draw_shop(surf, player, wave):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surf.blit(overlay, (0, 0))

    title = font_big.render(f"WAVE {wave - 1} CLEARED", True, GREEN)
    surf.blit(title, (WIDTH / 2 - title.get_width() / 2, 90))

    sub = font_small.render(f"You have ${player.money}", True, GOLD)
    surf.blit(sub, (WIDTH / 2 - sub.get_width() / 2, 160))

    box_w, box_h = 480, 260
    box_x, box_y = WIDTH / 2 - box_w / 2, 220
    pygame.draw.rect(surf, SHOP_BG, (box_x, box_y, box_w, box_h), border_radius=8)
    pygame.draw.rect(surf, WHITE, (box_x, box_y, box_w, box_h), 2, border_radius=8)

    y = box_y + 25
    for item in SHOP_ITEMS:
        line = font_small.render(
            f"[{item['key']}]  {item['name']}  -  ${item['cost']}", True, WHITE)
        surf.blit(line, (box_x + 25, y))
        y += 42

    hint = font_med.render("ENTER: Next Wave", True, GREEN)
    surf.blit(hint, (WIDTH / 2 - hint.get_width() / 2, box_y + box_h + 25))


def reset_game():
    global player, enemies, bullets, pickups, wave, game_over, spawn_timer, shop_open, WALLS
    WALLS = generate_walls()
    player = Player(WIDTH // 2, HEIGHT // 2)
    enemies = []
    bullets = []
    pickups = []
    wave = 1
    game_over = False
    spawn_timer = 0
    shop_open = False
    for _ in range(3):
        enemies.append(spawn_enemy())


def start_next_wave():
    """Called when the player leaves the shop: new map, enemies, ammo, and a heal."""
    global wave, WALLS
    wave += 1
    WALLS = generate_walls()

    # re-place the player if the new layout put a wall on top of them
    if collides_wall(player.rect()):
        player.x, player.y = WIDTH // 2, HEIGHT // 2

    bullets.clear()
    pickups.clear()

    for _ in range(2 + wave):
        enemies.append(spawn_enemy())
    # random ammo crates for this wave
    for _ in range(random.randint(2, 3 + wave // 3)):
        pickups.append(spawn_pickup())
    # heal a bit every wave, free of charge
    player.hp = min(player.max_hp, player.hp + 25)


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
player = None
enemies = []
bullets = []
pickups = []
wave = 1
game_over = False
spawn_timer = 0
shop_open = False
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
                elif not shop_open:
                    player.try_reload()

            if shop_open:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    shop_open = False
                    start_next_wave()
                elif event.key == pygame.K_1 and player.money >= 25:
                    player.money -= 25
                    player.reserve += 30
                elif event.key == pygame.K_2 and player.money >= 30:
                    player.money -= 30
                    player.hp = min(player.max_hp, player.hp + 50)
                elif event.key == pygame.K_3 and player.money >= 120:
                    player.money -= 120
                    player.mag_size += 1
                    player.ammo += 1
                elif event.key == pygame.K_4 and player.money >= 150:
                    player.money -= 150
                    player.fire_rate = max(3, player.fire_rate - 2)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            shooting_held = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            shooting_held = False

    if not game_over and not shop_open:
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

        # ammo pickup collection
        for p in pickups[:]:
            if player.rect().colliderect(p.rect()):
                player.reserve += p.amount
                pickups.remove(p)

        if player.hp <= 0:
            game_over = True

        # wave cleared -> open shop instead of instantly spawning next wave
        if len(enemies) == 0 and not shop_open:
            shop_open = True

    # ---------------- draw ----------------
    draw_map(screen)
    for w_ in WALLS[4:]:
        pass  # walls already drawn in draw_map

    for p in pickups:
        p.draw(screen)
    for b in bullets:
        b.draw(screen)
    for e in enemies:
        e.draw(screen)
    if player.hp > 0:
        player.draw(screen)

    draw_hud(screen, player, wave)
    draw_crosshair(screen, mouse_pos)

    if shop_open and not game_over:
        draw_shop(screen, player, wave)

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
