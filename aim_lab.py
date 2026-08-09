import tkinter as tk
import random
import math
import time

WIDTH, HEIGHT = 1280, 720
ROUND_TIME = 60
TARGET_LIFETIME = 1200
SPAWN_DELAY = 350

BG = "#121218"
PANEL = "#1c1c26"
ACCENT = "#00c8ff"
TARGET_COLOR = "#ff4646"
TEXT = "#e6e6f0"
MUTED = "#78788c"
FOV = 620

# Room bounds (used by both rendering and player collision)
ROOM_X = 9.5          # +/- extent along X
ROOM_Z_NEAR = 2.0      # how far player can walk toward camera start (+Z)
ROOM_Z_FAR = -18.5     # back wall
PLAYER_RADIUS = 0.6    # keep player this far from walls
EYE_HEIGHT = 1.65
WALK_SPEED = 4.2        # units per second
BOB_SPEED = 9.0
BOB_AMOUNT = 0.045


class Gun3D:
    """Gun modeled as 3D points in camera-local space, projected through
    the same perspective camera as the world so it feels attached to the
    player instead of pasted flat on the screen."""

    # Each part: list of 3D points (x,y,z in camera-local space: +x right,
    # +y up, +z forward) and a fill color. Built roughly to resemble a
    # carbine held at the lower-right of view.
    PARTS = [
        # stock
        ("#2a2a30", [(0.16, -0.30, 0.55), (0.34, -0.30, 0.55),
                      (0.32, -0.20, 0.62), (0.14, -0.20, 0.62)]),
        # pistol grip
        ("#1a1410", [(0.30, -0.34, 0.66), (0.38, -0.34, 0.66),
                      (0.40, -0.14, 0.63), (0.28, -0.14, 0.63)]),
        # lower receiver / body
        ("#3a3a42", [(0.16, -0.20, 0.60), (0.44, -0.20, 0.60),
                      (0.42, -0.10, 0.66), (0.14, -0.10, 0.66)]),
        # magazine
        ("#1a1a1e", [(0.30, -0.34, 0.60), (0.40, -0.34, 0.60),
                      (0.38, -0.20, 0.60), (0.28, -0.20, 0.60)]),
        # upper receiver / handguard
        ("#4a4a52", [(0.14, -0.10, 0.66), (0.50, -0.10, 0.72),
                      (0.50, -0.02, 0.72), (0.14, -0.02, 0.66)]),
        # barrel
        ("#222226", [(0.44, -0.06, 0.74), (0.62, -0.06, 0.86),
                      (0.62, -0.02, 0.86), (0.44, -0.02, 0.74)]),
        # scope body
        ("#222", [(0.20, -0.01, 0.63), (0.34, -0.01, 0.66),
                   (0.34, 0.05, 0.66), (0.20, 0.05, 0.63)]),
    ]
    MUZZLE_LOCAL = (0.62, -0.03, 0.87)
    SCOPE_LENS_LOCAL = (0.27, 0.02, 0.645)

    def __init__(self):
        self.recoil = 0.0     # pushes gun back along its local forward axis
        self.sway_x = 0.0
        self.sway_y = 0.0
        self.bob_phase = 0.0
        self.muzzle_flash = 0

    def kick(self):
        self.recoil = 0.14

    def update(self, mouse_dx, mouse_dy, moving, dt):
        self.recoil *= 0.80
        self.sway_x = self.sway_x * 0.85 + (-mouse_dx) * 0.0006
        self.sway_y = self.sway_y * 0.85 + (mouse_dy) * 0.0004
        self.sway_x = max(-0.06, min(0.06, self.sway_x))
        self.sway_y = max(-0.05, min(0.05, self.sway_y))
        if moving:
            self.bob_phase += dt * BOB_SPEED
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1

    def _local_to_world(self, cam, lx, ly, lz):
        """Turn a camera-local offset (right, up, forward) into a world
        point sitting just in front of the camera, honoring yaw/pitch so
        the gun rotates naturally as the player looks around."""
        lz -= self.recoil
        lx += self.sway_x
        ly += self.sway_y + math.sin(self.bob_phase) * BOB_AMOUNT * 0.4

        cos_y, sin_y = math.cos(cam.yaw), math.sin(cam.yaw)
        cos_p, sin_p = math.cos(cam.pitch), math.sin(cam.pitch)

        # apply pitch first (rotate around local X axis), then yaw
        y1 = ly * cos_p + lz * sin_p
        z1 = -ly * sin_p + lz * cos_p
        x1 = lx

        wx = cam.px + x1 * cos_y + z1 * sin_y
        wz = cam.pz - x1 * sin_y + z1 * cos_y
        wy = cam.py + y1
        return wx, wy, wz

    def muzzle_world(self, cam):
        return self._local_to_world(cam, *self.MUZZLE_LOCAL)

    def draw(self, canvas, cam):
        canvas.delete("gun")
        drawn = []
        for color, pts in self.PARTS:
            proj = []
            depth = 0.0
            ok = True
            for lx, ly, lz in pts:
                wx, wy, wz = self._local_to_world(cam, lx, ly, lz)
                p = cam.project(wx, wy, wz)
                if p is None:
                    ok = False
                    break
                proj.extend((p[0], p[1]))
                depth += p[2]
            if ok:
                drawn.append((depth, proj, color))

        for depth, proj, color in sorted(drawn, key=lambda d: d[0]):
            canvas.create_polygon(proj, fill=color, outline="#111", tags="gun")

        # scope lens accent
        wx, wy, wz = self._local_to_world(cam, *self.SCOPE_LENS_LOCAL)
        p = cam.project(wx, wy, wz)
        if p:
            sx, sy, scale = p
            r = max(2, scale * 0.03)
            canvas.create_oval(sx - r, sy - r, sx + r, sy + r,
                                fill="#0a0a0a", outline=ACCENT, width=1, tags="gun")

        if self.muzzle_flash > 0:
            mx, my, mz = self.muzzle_world(cam)
            p = cam.project(mx, my, mz)
            if p:
                sx, sy, scale = p
                size = (10 + self.muzzle_flash * 6) * (scale / FOV) * 40
                canvas.create_oval(sx - size, sy - size * 0.6, sx + size * 1.6, sy + size * 0.6,
                                    fill="#ffee88", outline="#ffaa00", tags="gun")


class Target2D:
    RADIUS = 28

    def __init__(self, canvas):
        self.canvas = canvas
        margin = self.RADIUS + 20
        self.x = random.randint(margin, WIDTH - margin)
        self.y = random.randint(margin + 60, HEIGHT - margin - 120)
        self.spawn_time = 0
        self.alive = True
        self.outer = canvas.create_oval(
            self.x - self.RADIUS, self.y - self.RADIUS,
            self.x + self.RADIUS, self.y + self.RADIUS,
            fill=TARGET_COLOR, outline="white", width=2,
        )
        inner_r = max(4, int(self.RADIUS * 0.35))
        self.inner = canvas.create_oval(
            self.x - inner_r, self.y - inner_r,
            self.x + inner_r, self.y + inner_r,
            fill="white", outline="",
        )

    def set_spawn_time(self, t):
        self.spawn_time = t

    def contains(self, mx, my):
        return math.hypot(mx - self.x, my - self.y) <= self.RADIUS

    def destroy(self):
        self.canvas.delete(self.outer)
        self.canvas.delete(self.inner)
        self.alive = False

    def update_color(self, life_ratio):
        if not self.alive:
            return
        r = int(255 * life_ratio + 255 * (1 - life_ratio))
        g = int(70 * life_ratio + 200 * (1 - life_ratio))
        b = int(70 * life_ratio + 60 * (1 - life_ratio))
        self.canvas.itemconfig(self.outer, fill=f"#{r:02x}{g:02x}{b:02x}")


class Target3D:
    RADIUS = 0.55

    def __init__(self):
        wall = random.choice(["back", "left", "right"])
        if wall == "back":
            self.x = random.uniform(-7, 7)
            self.y = random.uniform(1.8, 5.5)
            self.z = ROOM_Z_FAR + 1.0
        elif wall == "left":
            self.x = -ROOM_X + 0.5
            self.y = random.uniform(1.8, 5.5)
            self.z = random.uniform(ROOM_Z_FAR + 2, -4)
        else:
            self.x = ROOM_X - 0.5
            self.y = random.uniform(1.8, 5.5)
            self.z = random.uniform(ROOM_Z_FAR + 2, -4)
        self.spawn_time = 0
        self.alive = True

    def set_spawn_time(self, t):
        self.spawn_time = t


class Camera3D:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = 0.0
        self.px, self.py, self.pz = 0.0, EYE_HEIGHT, 0.0
        self.bob_phase = 0.0

    def rotate(self, dx, dy):
        self.yaw += dx * 0.003
        self.pitch = max(-1.2, min(1.2, self.pitch + dy * 0.003))

    def forward_vec(self):
        return math.sin(self.yaw), -math.cos(self.yaw)

    def right_vec(self):
        return math.cos(self.yaw), math.sin(self.yaw)

    def move(self, forward, strafe, dt):
        """forward/strafe are -1..1 input axes. Moves the camera and
        clamps it inside the room, keeping a margin from the walls."""
        if forward == 0 and strafe == 0:
            return False
        fx, fz = self.forward_vec()
        rx, rz = self.right_vec()
        dx = (fx * forward + rx * strafe)
        dz = (fz * forward + rz * strafe)
        norm = math.hypot(dx, dz)
        if norm > 0:
            dx, dz = dx / norm, dz / norm
        new_x = self.px + dx * WALK_SPEED * dt
        new_z = self.pz + dz * WALK_SPEED * dt
        new_x = max(-ROOM_X + PLAYER_RADIUS, min(ROOM_X - PLAYER_RADIUS, new_x))
        new_z = max(ROOM_Z_FAR + PLAYER_RADIUS, min(ROOM_Z_NEAR - PLAYER_RADIUS, new_z))
        self.px, self.pz = new_x, new_z
        self.bob_phase += dt * BOB_SPEED
        self.py = EYE_HEIGHT + math.sin(self.bob_phase) * BOB_AMOUNT
        return True

    def settle_bob(self, dt):
        # ease head height back to resting when not moving
        target = EYE_HEIGHT
        self.py += (target - self.py) * min(1.0, dt * 6)

    def project(self, x, y, z):
        dx, dy, dz = x - self.px, y - self.py, z - self.pz
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        rx = dx * cos_y + dz * sin_y
        rz = -dx * sin_y + dz * cos_y
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        ry = dy * cos_p - rz * sin_p
        rz = dy * sin_p + rz * cos_p
        if rz <= 0.05:
            return None
        sx = WIDTH / 2 + (rx / rz) * FOV
        sy = HEIGHT / 2 - (ry / rz) * FOV
        scale = FOV / rz
        return sx, sy, scale

    def screen_hit(self, target):
        proj = self.project(target.x, target.y, target.z)
        if proj is None:
            return False
        sx, sy, scale = proj
        screen_r = target.RADIUS * scale
        return math.hypot(sx - WIDTH / 2, sy - HEIGHT / 2) <= screen_r


class World3D:
    @staticmethod
    def draw(canvas, cam):
        canvas.delete("world")
        quads = [
            ([(-ROOM_X, 0, ROOM_Z_FAR), (ROOM_X, 0, ROOM_Z_FAR), (ROOM_X, 0, ROOM_Z_NEAR), (-ROOM_X, 0, ROOM_Z_NEAR)], "#1a1a22"),
            ([(-ROOM_X, 7, ROOM_Z_FAR), (ROOM_X, 7, ROOM_Z_FAR), (ROOM_X, 7, ROOM_Z_NEAR), (-ROOM_X, 7, ROOM_Z_NEAR)], "#14141a"),
            ([(-ROOM_X, 0, ROOM_Z_FAR), (ROOM_X, 0, ROOM_Z_FAR), (ROOM_X, 7, ROOM_Z_FAR), (-ROOM_X, 7, ROOM_Z_FAR)], "#252530"),
            ([(-ROOM_X - 0.5, 0, ROOM_Z_FAR), (-ROOM_X - 0.5, 0, ROOM_Z_NEAR), (-ROOM_X - 0.5, 7, ROOM_Z_NEAR), (-ROOM_X - 0.5, 7, ROOM_Z_FAR)], "#1e1e28"),
            ([(ROOM_X + 0.5, 0, ROOM_Z_FAR), (ROOM_X + 0.5, 0, ROOM_Z_NEAR), (ROOM_X + 0.5, 7, ROOM_Z_NEAR), (ROOM_X + 0.5, 7, ROOM_Z_FAR)], "#1e1e28"),
        ]
        drawn = []
        for corners, color in quads:
            pts = []
            depth = 0
            ok = True
            for x, y, z in corners:
                p = cam.project(x, y, z)
                if p is None:
                    ok = False
                    break
                pts.extend(p[:2])
                depth += p[2]
            if ok and len(pts) == 8:
                drawn.append((depth, pts, color))

        for i in range(6):
            z = ROOM_Z_NEAR - 3 - i * 3.5
            pts = []
            ok = True
            for x in (-ROOM_X, ROOM_X):
                p = cam.project(x, 0.02, z)
                if p is None:
                    ok = False
                    break
                pts.extend(p[:2])
            if ok:
                canvas.create_line(pts[0], pts[1], pts[2], pts[3], fill="#2a2a35", tags="world")

        for depth, pts, color in sorted(drawn, key=lambda q: -q[0]):
            canvas.create_polygon(pts, fill=color, outline="#333", tags="world")

    @staticmethod
    def draw_target(canvas, cam, target, life_ratio):
        if not target.alive:
            return
        proj = cam.project(target.x, target.y, target.z)
        if proj is None:
            return
        sx, sy, scale = proj
        radius = max(6, int(target.RADIUS * scale))
        red = int(255 * life_ratio + 255 * (1 - life_ratio))
        green = int(70 * life_ratio + 200 * (1 - life_ratio))
        blue = int(70 * life_ratio + 60 * (1 - life_ratio))
        color = f"#{red:02x}{green:02x}{blue:02x}"
        canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius,
                           fill=color, outline="white", width=2, tags="world")
        ir = max(3, radius // 3)
        canvas.create_oval(sx - ir, sy - ir, sx + ir, sy + ir, fill="white", outline="", tags="world")


class AimLab:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aim Lab — 2D / 3D")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.state = "menu"
        self.mode = None
        self.targets = []
        self.gun = Gun3D()
        self.camera = Camera3D()
        self.hits = self.misses = self.shots = 0
        self.start_time = self.last_spawn = 0
        self.timer_job = None
        self.last_mx = WIDTH // 2
        self.last_my = HEIGHT // 2
        self.prev_motion_x = WIDTH // 2
        self.prev_motion_y = HEIGHT // 2
        self.last_frame_time = time.time()

        self.keys_down = set()

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.root.bind("<Escape>", self.on_escape)
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)

        self.show_menu()

    def clear_canvas(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        for t in self.targets:
            if hasattr(t, "destroy") and t.alive:
                t.destroy()
        self.targets = []
        self.canvas.delete("all")
        self.gun = Gun3D()
        self.keys_down = set()

    def show_menu(self):
        self.state = "menu"
        self.mode = None
        self.clear_canvas()
        self.root.config(cursor="arrow")

        self.canvas.create_text(WIDTH // 2, 100, text="AIM LAB", fill=ACCENT, font=("Consolas", 52, "bold"))
        self.canvas.create_text(WIDTH // 2, 155, text="Choose your training mode", fill=MUTED, font=("Consolas", 20))

        # 2D panel
        self.canvas.create_rectangle(140, 220, 580, 520, fill=PANEL, outline=ACCENT, width=2)
        self.canvas.create_text(360, 270, text="2D MODE", fill=ACCENT, font=("Consolas", 32, "bold"))
        self.canvas.create_text(360, 330, text="Flat targets · free aim", fill=TEXT, font=("Consolas", 16))
        self.canvas.create_text(360, 370, text="Crosshair follows mouse", fill=MUTED, font=("Consolas", 14))
        self.canvas.create_text(360, 460, text="[ CLICK HERE ]", fill=ACCENT, font=("Consolas", 18, "bold"))
        self.menu_2d = (140, 220, 580, 520)

        # 3D panel
        self.canvas.create_rectangle(700, 220, 1140, 520, fill=PANEL, outline="#ff6b35", width=2)
        self.canvas.create_text(920, 270, text="3D MODE", fill="#ff6b35", font=("Consolas", 32, "bold"))
        self.canvas.create_text(920, 330, text="FPS room · walk & shoot", fill=TEXT, font=("Consolas", 16))
        self.canvas.create_text(920, 370, text="WASD to move · mouse to look", fill=MUTED, font=("Consolas", 14))
        self.canvas.create_text(920, 460, text="[ CLICK HERE ]", fill="#ff6b35", font=("Consolas", 18, "bold"))
        self.menu_3d = (700, 220, 1140, 520)

        self.canvas.create_text(WIDTH // 2, HEIGHT - 50, text=f"{ROUND_TIME}s rounds  ·  ESC to quit",
                                fill=MUTED, font=("Consolas", 16))

    def reset_session(self):
        self.hits = self.misses = self.shots = 0
        now = int(time.time() * 1000)
        self.start_time = now
        self.last_spawn = now - SPAWN_DELAY
        self.camera = Camera3D()
        self.gun = Gun3D()
        self.last_mx = WIDTH // 2
        self.last_my = HEIGHT // 2
        self.prev_motion_x = WIDTH // 2
        self.prev_motion_y = HEIGHT // 2
        self.last_frame_time = time.time()
        self.keys_down = set()

    def start_game(self, mode):
        self.mode = mode
        self.clear_canvas()
        self.reset_session()
        self.state = "playing"
        self.root.config(cursor="none")
        self.root.focus_set()
        self.spawn_target()
        self.game_loop()

    def time_remaining(self):
        return max(0, ROUND_TIME - (int(time.time() * 1000) - self.start_time) / 1000)

    def accuracy(self):
        return 100.0 if self.shots == 0 else (self.hits / self.shots) * 100

    def draw_hud(self):
        self.canvas.delete("hud")
        self.canvas.create_rectangle(0, 0, WIDTH, 52, fill=PANEL, outline="", tags="hud")
        time_left = self.time_remaining()
        mins, secs = int(time_left // 60), int(time_left % 60)
        timer_color = ACCENT if time_left > 10 else "#ff5a5a"
        mode_label = "2D" if self.mode == "2d" else "3D"
        items = [
            (f"{mode_label}  {mins:02d}:{secs:02d}", timer_color, 20),
            (f"HITS {self.hits}", TEXT, 260),
            (f"ACC {self.accuracy():.0f}%", TEXT, 480),
            (f"SCORE {self.hits * 100 + int(self.accuracy())}", ACCENT, 760),
        ]
        for text, color, x in items:
            self.canvas.create_text(x, 26, text=text, fill=color, font=("Consolas", 18), anchor="w", tags="hud")
        if self.mode == "3d":
            self.canvas.create_text(WIDTH - 20, 26, text="WASD move", fill=MUTED,
                                    font=("Consolas", 14), anchor="e", tags="hud")

    def draw_crosshair_center(self):
        self.canvas.delete("crosshair")
        cx, cy = WIDTH // 2, HEIGHT // 2
        size, gap = 12, 5
        for x1, y1, x2, y2 in [
            (cx - size, cy, cx - gap, cy), (cx + gap, cy, cx + size, cy),
            (cx, cy - size, cx, cy - gap), (cx, cy + gap, cx, cy + size),
        ]:
            self.canvas.create_line(x1, y1, x2, y2, fill="white", width=2, tags="crosshair")
        self.canvas.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="white", outline="", tags="crosshair")

    def draw_crosshair_mouse(self, mx, my):
        self.canvas.delete("crosshair")
        size, gap = 14, 6
        for x1, y1, x2, y2 in [
            (mx - size, my, mx - gap, my), (mx + gap, my, mx + size, my),
            (mx, my - size, mx, my - gap), (mx, my + gap, mx, my + size),
        ]:
            self.canvas.create_line(x1, y1, x2, y2, fill="white", width=2, tags="crosshair")
        self.canvas.create_oval(mx - 3, my - 3, mx + 3, my + 3, outline="white", tags="crosshair")

    def spawn_target(self):
        self.targets = [t for t in self.targets if t.alive]
        if self.targets:
            return
        if self.mode == "2d":
            t = Target2D(self.canvas)
        else:
            t = Target3D()
        t.set_spawn_time(int(time.time() * 1000))
        self.targets.append(t)
        self.last_spawn = int(time.time() * 1000)

    def flash(self, color, tag):
        self.canvas.delete(tag)
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill=color, stipple="gray25", tags=tag)
        self.root.after(80, lambda: self.canvas.delete(tag))

    def shoot_2d(self, mx, my):
        self.shots += 1
        self.gun.kick()
        hit = False
        for t in self.targets:
            if t.alive and t.contains(mx, my):
                t.destroy()
                self.hits += 1
                hit = True
                self.flash("#55cc88", "hit_flash")
                break
        if not hit:
            self.misses += 1
            self.flash("#cc5555", "miss_flash")
        self.targets = [t for t in self.targets if t.alive]
        if not self.targets:
            self.spawn_target()

    def shoot_3d(self):
        self.shots += 1
        self.gun.kick()
        hit = False
        for t in self.targets:
            if t.alive and self.camera.screen_hit(t):
                t.alive = False
                self.hits += 1
                hit = True
                self.flash("#55cc88", "hit_flash")
                break
        if not hit:
            self.misses += 1
            self.flash("#cc5555", "miss_flash")
        self.targets = [t for t in self.targets if t.alive]
        if not self.targets:
            self.spawn_target()

    def render_2d(self, mx, my, dt):
        self.canvas.delete("play")
        for t in self.targets:
            if t.alive:
                now = int(time.time() * 1000)
                life = max(0, TARGET_LIFETIME - (now - t.spawn_time))
                t.update_color(life / TARGET_LIFETIME)
        # Simple flat gun sits fixed bottom-right; reuse crosshair for aim.
        self.gun.recoil *= 0.72
        self.draw_crosshair_mouse(mx, my)

    def render_3d(self, mouse_dx, mouse_dy, moving, dt):
        World3D.draw(self.canvas, self.camera)
        now = int(time.time() * 1000)
        for t in self.targets:
            if t.alive:
                life = max(0, TARGET_LIFETIME - (now - t.spawn_time))
                World3D.draw_target(self.canvas, self.camera, t, life / TARGET_LIFETIME)
        self.gun.update(mouse_dx, mouse_dy, moving, dt)
        self.gun.draw(self.canvas, self.camera)
        self.draw_crosshair_center()

    def _movement_axes(self):
        forward = 0
        strafe = 0
        if "w" in self.keys_down:
            forward += 1
        if "s" in self.keys_down:
            forward -= 1
        if "d" in self.keys_down:
            strafe += 1
        if "a" in self.keys_down:
            strafe -= 1
        return forward, strafe

    def game_loop(self):
        if self.state != "playing":
            return

        now_ms = int(time.time() * 1000)
        now = time.time()
        dt = max(0.0, min(0.05, now - self.last_frame_time))
        self.last_frame_time = now

        if self.time_remaining() <= 0:
            self.show_results()
            return

        mx = self.root.winfo_pointerx() - self.root.winfo_rootx()
        my = self.root.winfo_pointery() - self.root.winfo_rooty()
        mouse_dx = mx - self.last_mx
        mouse_dy = my - self.last_my

        for t in self.targets:
            if t.alive and now_ms - t.spawn_time >= TARGET_LIFETIME:
                if hasattr(t, "destroy"):
                    t.destroy()
                else:
                    t.alive = False
                self.misses += 1

        self.targets = [t for t in self.targets if t.alive]
        if not self.targets and now_ms - self.last_spawn >= SPAWN_DELAY:
            self.spawn_target()

        if self.mode == "2d":
            self.render_2d(mx, my, dt)
        else:
            forward, strafe = self._movement_axes()
            moved = self.camera.move(forward, strafe, dt)
            if not moved:
                self.camera.settle_bob(dt)
            self.render_3d(mouse_dx, mouse_dy, moved, dt)

        self.last_mx, self.last_my = mx, my
        self.draw_hud()
        self.timer_job = self.root.after(16, self.game_loop)

    def show_results(self):
        self.state = "results"
        self.clear_canvas()
        self.root.config(cursor="arrow")
        mode_name = "2D" if self.mode == "2d" else "3D"
        self.canvas.create_text(WIDTH // 2, 100, text=f"{mode_name} ROUND COMPLETE",
                                fill=ACCENT, font=("Consolas", 38, "bold"))
        score = self.hits * 100 + int(self.accuracy())
        stats = [("Score", str(score), ACCENT), ("Hits", str(self.hits), TEXT),
                 ("Misses", str(self.misses), TEXT), ("Accuracy", f"{self.accuracy():.1f}%", TEXT)]
        px, py, pw = WIDTH // 2 - 210, 180, 420
        self.canvas.create_rectangle(px, py, px + pw, py + 260, fill=PANEL, outline=ACCENT, width=2)
        y = py + 35
        for label, val, color in stats:
            self.canvas.create_text(px + 35, y, text=label, fill=MUTED, font=("Consolas", 20), anchor="w")
            self.canvas.create_text(px + pw - 35, y, text=val, fill=color, font=("Consolas", 20), anchor="e")
            y += 50
        self.canvas.create_text(WIDTH // 2, HEIGHT - 55,
                                text="CLICK to replay  ·  ESC for mode select", fill=MUTED, font=("Consolas", 16))

    def on_click(self, event):
        if self.state == "menu":
            x1, y1, x2, y2 = self.menu_2d
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.start_game("2d")
            x1, y1, x2, y2 = self.menu_3d
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.start_game("3d")
        elif self.state == "playing":
            if self.mode == "2d":
                self.shoot_2d(event.x, event.y)
            else:
                self.shoot_3d()
        elif self.state == "results":
            self.start_game(self.mode)

    def on_motion(self, event):
        if self.state == "playing" and self.mode == "3d":
            dx = event.x - self.prev_motion_x
            dy = event.y - self.prev_motion_y
            if dx or dy:
                self.camera.rotate(dx, dy)
            self.prev_motion_x = event.x
            self.prev_motion_y = event.y

    def on_key_down(self, event):
        key = event.keysym.lower()
        if key in ("w", "a", "s", "d"):
            self.keys_down.add(key)

    def on_key_up(self, event):
        key = event.keysym.lower()
        self.keys_down.discard(key)

    def on_escape(self, _event=None):
        if self.state == "playing":
            self.show_menu()
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AimLab().run()
