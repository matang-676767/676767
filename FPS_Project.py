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


class Gun:
    """First-person gun drawn with canvas polygons."""

    def __init__(self):
        self.recoil = 0.0
        self.sway_x = 0.0
        self.muzzle_flash = 0

    def kick(self):
        self.recoil = 18.0
        self.muzzle_flash = 4

    def update(self, mouse_dx=0):
        self.recoil *= 0.72
        self.sway_x = self.sway_x * 0.82 + mouse_dx * 0.15
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1

    def draw(self, canvas):
        canvas.delete("gun")
        cx = WIDTH // 2 + self.sway_x
        base_y = HEIGHT - 40 + self.recoil * 0.4
        kick_back = self.recoil

        metal = "#4a4a52"
        dark = "#2a2a30"
        grip = "#1a1410"
        accent = "#3d3d48"

        # barrel
        canvas.create_rectangle(
            cx + 60 - kick_back, base_y - 118,
            cx + 200 - kick_back, base_y - 108,
            fill=dark, outline="#666", width=1, tags="gun",
        )
        # upper receiver
        canvas.create_polygon(
            cx - 10, base_y - 105,
            cx + 150 - kick_back * 0.5, base_y - 105,
            cx + 140 - kick_back * 0.5, base_y - 55,
            cx - 20, base_y - 55,
            fill=metal, outline="#666", tags="gun",
        )
        # handguard
        canvas.create_rectangle(
            cx + 30, base_y - 100,
            cx + 120 - kick_back * 0.3, base_y - 70,
            fill=accent, outline="#555", tags="gun",
        )
        # magazine
        canvas.create_polygon(
            cx + 10, base_y - 55,
            cx + 55, base_y - 55,
            cx + 45, base_y + 10,
            cx, base_y + 10,
            fill=grip, outline="#333", tags="gun",
        )
        # pistol grip
        canvas.create_polygon(
            cx - 35, base_y - 50,
            cx - 5, base_y - 50,
            cx + 5, base_y + 35,
            cx - 45, base_y + 35,
            fill=grip, outline="#333", tags="gun",
        )
        # stock
        canvas.create_polygon(
            cx - 120, base_y - 45,
            cx - 20, base_y - 45,
            cx - 25, base_y - 20,
            cx - 130, base_y - 20,
            fill=dark, outline="#555", tags="gun",
        )
        # scope
        canvas.create_rectangle(
            cx + 20, base_y - 125,
            cx + 90, base_y - 115,
            fill="#222", outline="#888", tags="gun",
        )
        canvas.create_oval(
            cx + 45, base_y - 118, cx + 65, base_y - 108,
            fill="#111", outline="#00c8ff", width=1, tags="gun",
        )
        # trigger guard
        canvas.create_arc(
            cx - 5, base_y - 30, cx + 30, base_y + 5,
            start=200, extent=140, style=tk.ARC, outline="#444", width=2, tags="gun",
        )

        if self.muzzle_flash > 0:
            flash_size = 20 + self.muzzle_flash * 8
            mx = cx + 200 - kick_back
            my = base_y - 113
            canvas.create_oval(
                mx - flash_size, my - flash_size // 2,
                mx + flash_size * 2, my + flash_size // 2,
                fill="#ffee88", outline="#ffaa00", tags="gun",
            )


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
            self.z = -17.5
        elif wall == "left":
            self.x = -9.5
            self.y = random.uniform(1.8, 5.5)
            self.z = random.uniform(-16, -4)
        else:
            self.x = 9.5
            self.y = random.uniform(1.8, 5.5)
            self.z = random.uniform(-16, -4)
        self.spawn_time = 0
        self.alive = True

    def set_spawn_time(self, t):
        self.spawn_time = t


class Camera3D:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = 0.0
        self.px, self.py, self.pz = 0.0, 1.65, 0.0

    def rotate(self, dx, dy):
        self.yaw += dx * 0.003
        self.pitch = max(-1.2, min(1.2, self.pitch + dy * 0.003))

    def project(self, x, y, z):
        dx, dy, dz = x - self.px, y - self.py, z - self.pz
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        rx = dx * cos_y + dz * sin_y
        rz = -dx * sin_y + dz * cos_y
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        ry = dy * cos_p - rz * sin_p
        rz = dy * sin_p + rz * cos_p
        if rz <= 0.15:
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
    WALL_Z_NEAR = 2
    WALL_Z_FAR = -20
    WALL_X = 10
    CEILING_Y = 7
    FLOOR_Y = 0

    @staticmethod
    def draw(canvas, cam):
        canvas.delete("world")
        quads = [
            ([(-9, 0, -19), (9, 0, -19), (9, 0, 2), (-9, 0, 2)], "#1a1a22"),
            ([(-9, 7, -19), (9, 7, -19), (9, 7, 2), (-9, 7, 2)], "#14141a"),
            ([(-9, 0, -19), (9, 0, -19), (9, 7, -19), (-9, 7, -19)], "#252530"),
            ([(-10, 0, -19), (-10, 0, 2), (-10, 7, 2), (-10, 7, -19)], "#1e1e28"),
            ([(10, 0, -19), (10, 0, 2), (10, 7, 2), (10, 7, -19)], "#1e1e28"),
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

        for _ in range(5):
            z = -3 - _ * 3.5
            pts = []
            depth = 0
            ok = True
            for x in (-9, 9):
                p = cam.project(x, 0.02, z)
                if p is None:
                    ok = False
                    break
                pts.extend(p[:2])
                depth += p[2]
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
        self.gun = Gun()
        self.camera = Camera3D()
        self.hits = self.misses = self.shots = 0
        self.start_time = self.last_spawn = 0
        self.timer_job = None
        self.last_mx = WIDTH // 2
        self.last_my = HEIGHT // 2
        self.prev_motion_x = WIDTH // 2
        self.prev_motion_y = HEIGHT // 2

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.root.bind("<Escape>", self.on_escape)

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
        self.gun = Gun()

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
        self.canvas.create_text(920, 330, text="FPS room · look & shoot", fill=TEXT, font=("Consolas", 16))
        self.canvas.create_text(920, 370, text="Move mouse to aim · center crosshair", fill=MUTED, font=("Consolas", 14))
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
        self.gun = Gun()
        self.last_mx = WIDTH // 2
        self.last_my = HEIGHT // 2
        self.prev_motion_x = WIDTH // 2
        self.prev_motion_y = HEIGHT // 2

    def start_game(self, mode):
        self.mode = mode
        self.clear_canvas()
        self.reset_session()
        self.state = "playing"
        self.root.config(cursor="none")
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

    def render_2d(self, mx, my):
        self.canvas.delete("play")
        for t in self.targets:
            if t.alive:
                now = int(time.time() * 1000)
                life = max(0, TARGET_LIFETIME - (now - t.spawn_time))
                t.update_color(life / TARGET_LIFETIME)
        self.gun.update(mx - self.last_mx)
        self.gun.draw(self.canvas)
        self.draw_crosshair_mouse(mx, my)

    def render_3d(self, mouse_dx):
        World3D.draw(self.canvas, self.camera)
        now = int(time.time() * 1000)
        for t in self.targets:
            if t.alive:
                life = max(0, TARGET_LIFETIME - (now - t.spawn_time))
                World3D.draw_target(self.canvas, self.camera, t, life / TARGET_LIFETIME)
        self.gun.update(mouse_dx)
        self.gun.draw(self.canvas)
        self.draw_crosshair_center()

    def game_loop(self):
        if self.state != "playing":
            return

        now = int(time.time() * 1000)
        if self.time_remaining() <= 0:
            self.show_results()
            return

        mx = self.root.winfo_pointerx() - self.root.winfo_rootx()
        my = self.root.winfo_pointery() - self.root.winfo_rooty()
        mouse_dx = mx - self.last_mx

        for t in self.targets:
            if t.alive and now - t.spawn_time >= TARGET_LIFETIME:
                if hasattr(t, "destroy"):
                    t.destroy()
                else:
                    t.alive = False
                self.misses += 1

        self.targets = [t for t in self.targets if t.alive]
        if not self.targets and now - self.last_spawn >= SPAWN_DELAY:
            self.spawn_target()

        if self.mode == "2d":
            self.render_2d(mx, my)
        else:
            self.render_3d(mouse_dx)

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

    def on_escape(self, _event=None):
        if self.state == "playing":
            self.show_menu()
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AimLab().run()


