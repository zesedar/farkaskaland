from __future__ import annotations

from pathlib import Path
from collections import deque
import math
import random
import pygame

FPS = 60
PLAYER_SPEED = 300
SPRITE_HEIGHT = 120
JUMP_SPEED = 780
GRAVITY = 1500
MAX_FALL_SPEED = 1100

REFERENCE_STANCE_SOURCE_HEIGHT = 328
JUMP_SHEET_FILENAME = "wolf_jump_sheet.png"
JUMP_SHEET_COLUMNS = 4
JUMP_SHEET_ROWS = 2
JUMP_ASCEND_FRAME_TIME = 0.12
JUMP_DESCEND_FRAME_TIMES = [0.10, 0.38, 0.15, 0.14]

FRAME_FILE_PREFIX = "wolf_run_"
FRAME_FILE_EXTENSION = ".png"
FRAME_FILE_DIGITS = 4
TOTAL_FRAME_COUNT = 63
RUN_START_FRAME = 0
RUN_END_FRAME = 43
STOP_START_FRAME = 44
STOP_END_FRAME = 62
ANIMATION_FRAME_TIME = 0.07
FAST_STOP_FILE_START = 52
FAST_STOP_FILE_END = 59
FAST_STOP_FRAME_TIME = 0.002

GREEN_ALPHA_MIN_GREEN = 70
GREEN_ALPHA_DOMINANCE = 28

INTRO_TEXT = "Valami azt súgja nekem meg kell találnom a békémet..."
THORN_TEXT = "Néha csak úgy juthatunk tovább, ha megtaláljuk a legszűkebb járható ösvényt."
WINDOW_TITLE = "Little Wolf Journey"

OBSTACLE_CAMERA_REVEAL_SPEED = 230.0
OBSTACLE_CAMERA_REVEAL_EPSILON = 1.0


class WorldConfig:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.left_frame_x = max(55, int(width * 0.075))
        self.right_edge_x = int(width * 0.82)
        self.camera_smoothness = 4.8
        self.ground_top_y = int(height * 0.885)
        self.ground_cap_height = max(12, int(height * 0.022))


def is_transparency_green(r: int, g: int, b: int, a: int) -> bool:
    if a == 0:
        return False
    return g >= GREEN_ALPHA_MIN_GREEN and g >= r + GREEN_ALPHA_DOMINANCE and g >= b + GREEN_ALPHA_DOMINANCE


def remove_green_transparency(surface: pygame.Surface) -> pygame.Surface:
    surface = surface.convert_alpha()
    width, height = surface.get_size()
    surface.lock()
    try:
        for y in range(height):
            for x in range(width):
                r, g, b, a = surface.get_at((x, y))
                if is_transparency_green(r, g, b, a):
                    surface.set_at((x, y), (0, 0, 0, 0))
    finally:
        surface.unlock()
    return surface


def is_light_background(r: int, g: int, b: int, a: int) -> bool:
    if a == 0:
        return False
    return r >= 210 and g >= 210 and b >= 210


def remove_light_background_from_edges(surface: pygame.Surface) -> pygame.Surface:
    surface = surface.convert_alpha()
    width, height = surface.get_size()
    queue: deque[tuple[int, int]] = deque()
    visited: set[tuple[int, int]] = set()

    def add(x: int, y: int) -> None:
        if 0 <= x < width and 0 <= y < height and (x, y) not in visited:
            visited.add((x, y))
            queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    surface.lock()
    try:
        while queue:
            x, y = queue.popleft()
            r, g, b, a = surface.get_at((x, y))
            if not is_light_background(r, g, b, a):
                continue
            surface.set_at((x, y), (0, 0, 0, 0))
            add(x + 1, y)
            add(x - 1, y)
            add(x, y + 1)
            add(x, y - 1)
    finally:
        surface.unlock()
    return surface


def trim_transparent_padding(surface: pygame.Surface, padding: int = 6) -> pygame.Surface:
    rect = surface.get_bounding_rect(min_alpha=1)
    if rect.width <= 0 or rect.height <= 0:
        return surface
    rect = rect.inflate(padding * 2, padding * 2)
    rect.clamp_ip(surface.get_rect())
    cropped = pygame.Surface(rect.size, pygame.SRCALPHA)
    cropped.blit(surface, (0, 0), rect)
    return cropped


def scale_surface_to_height(surface: pygame.Surface, target_height: int) -> pygame.Surface:
    scale = target_height / surface.get_height()
    new_width = max(1, int(surface.get_width() * scale))
    return pygame.transform.smoothscale(surface, (new_width, target_height))


def scale_surface_by_factor(surface: pygame.Surface, scale: float) -> pygame.Surface:
    new_width = max(1, int(surface.get_width() * scale))
    new_height = max(1, int(surface.get_height() * scale))
    return pygame.transform.smoothscale(surface, (new_width, new_height))


def load_frame_file(path: Path, target_height: int) -> pygame.Surface:
    frame = pygame.image.load(str(path)).convert_alpha()
    frame = remove_green_transparency(frame)
    return scale_surface_to_height(frame, target_height)


def load_sprite_sheet_grid(path: Path, columns: int, rows: int, target_height: int, reference_source_height: int) -> list[pygame.Surface]:
    if not path.exists():
        return []
    sheet = pygame.image.load(str(path)).convert_alpha()
    sheet_width, sheet_height = sheet.get_size()
    cell_width = sheet_width // columns
    cell_height = sheet_height // rows
    frames: list[pygame.Surface] = []
    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(column * cell_width + 1, row * cell_height + 1, cell_width - 2, cell_height - 2)
            frame = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frame = remove_light_background_from_edges(frame)
            frame = trim_transparent_padding(frame, padding=2)
            frames.append(scale_surface_by_factor(frame, target_height / reference_source_height))
    return frames


def load_image_sequence(folder: Path, prefix: str, extension: str, digits: int, frame_count: int, target_height: int) -> list[pygame.Surface]:
    frames: list[pygame.Surface] = []
    missing_files: list[str] = []
    for file_number in range(1, frame_count + 1):
        filename = f"{prefix}{file_number:0{digits}d}{extension}"
        path = folder / filename
        if not path.exists():
            missing_files.append(filename)
            continue
        frames.append(load_frame_file(path, target_height))
    if missing_files:
        shown = ", ".join(missing_files[:8])
        extra = "" if len(missing_files) <= 8 else f" ... +{len(missing_files) - 8} további"
        raise FileNotFoundError(f"Hiányzó animációs fájl(ok) az assets mappából: {shown}{extra}")
    return frames


def get_frame_index_from_timer(animation_timer: float, frame_times: list[float]) -> int:
    elapsed = 0.0
    for frame_index, frame_time in enumerate(frame_times):
        elapsed += frame_time
        if animation_timer < elapsed:
            return frame_index
    return len(frame_times) - 1


def create_stop_frame_times() -> list[float]:
    frame_times: list[float] = []
    for logical_frame in range(STOP_START_FRAME, STOP_END_FRAME + 1):
        file_number = logical_frame + 1
        if FAST_STOP_FILE_START <= file_number <= FAST_STOP_FILE_END:
            frame_times.append(FAST_STOP_FRAME_TIME)
        else:
            frame_times.append(ANIMATION_FRAME_TIME)
    return frame_times


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        test = f"{line} {word}"
        if font.size(test)[0] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def create_placeholder_frame(width: int, height: int, leg_phase: float = 0.0) -> pygame.Surface:
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    dark = (27, 34, 51)
    fur = (85, 93, 112)
    light = (172, 180, 196)
    glow = (109, 207, 222)
    body = pygame.Rect(int(width * 0.18), int(height * 0.38), int(width * 0.48), int(height * 0.25))
    head = pygame.Rect(int(width * 0.55), int(height * 0.25), int(width * 0.24), int(height * 0.20))
    pygame.draw.ellipse(surf, fur, body)
    pygame.draw.ellipse(surf, dark, body, 2)
    pygame.draw.ellipse(surf, fur, head)
    pygame.draw.ellipse(surf, dark, head, 2)
    pygame.draw.polygon(surf, dark, [(int(width * 0.59), int(height * 0.27)), (int(width * 0.62), int(height * 0.11)), (int(width * 0.68), int(height * 0.26))])
    pygame.draw.polygon(surf, dark, [(int(width * 0.67), int(height * 0.28)), (int(width * 0.70), int(height * 0.12)), (int(width * 0.76), int(height * 0.29))])
    pygame.draw.ellipse(surf, light, pygame.Rect(int(width * 0.47), int(height * 0.39), int(width * 0.18), int(height * 0.23)))
    pygame.draw.polygon(surf, dark, [(int(width * 0.18), int(height * 0.47)), (int(width * 0.02), int(height * 0.34)), (int(width * 0.12), int(height * 0.58))])
    offset = int(6 * leg_phase)
    for x, y, dx in [
        (int(width * 0.31), int(height * 0.57), -offset),
        (int(width * 0.42), int(height * 0.58), offset),
        (int(width * 0.54), int(height * 0.57), offset),
        (int(width * 0.63), int(height * 0.57), -offset),
    ]:
        pygame.draw.line(surf, dark, (x, y), (x + dx, int(height * 0.90)), 6)
        pygame.draw.line(surf, light, (x + 2, y + 2), (x + dx + 2, int(height * 0.90)), 2)
    pygame.draw.circle(surf, glow, (int(width * 0.72), int(height * 0.34)), 3)
    pygame.draw.line(surf, dark, (int(width * 0.76), int(height * 0.37)), (int(width * 0.84), int(height * 0.41)), 3)
    return surf


def create_placeholder_wolf_frames(target_height: int) -> tuple[list[pygame.Surface], list[pygame.Surface], list[pygame.Surface]]:
    width = int(target_height * 1.5)
    run_frames = [create_placeholder_frame(width, target_height, phase) for phase in (-1.0, -0.35, 0.35, 1.0)]
    stop_frame = create_placeholder_frame(width, target_height, 0.0)
    stop_frames = [stop_frame for _ in range(STOP_END_FRAME - STOP_START_FRAME + 1)]
    jump_frames = [create_placeholder_frame(width, target_height, 0.0) for _ in range(8)]
    return run_frames, stop_frames, jump_frames


class StaticBackground:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.background = self._load_background()
        self.ground_tile = self._create_ground_tile()

    def _load_background(self) -> pygame.Surface:
        candidates = [Path(__file__).parent / "assets" / "hatter.png", Path("/mnt/data/assets/hatter.png")]
        source = next((path for path in candidates if path.exists()), None)
        if source is not None:
            image = pygame.image.load(str(source)).convert()
            return pygame.transform.smoothscale(image, (self.config.width, self.config.height))
        fallback = pygame.Surface((self.config.width, self.config.height))
        top = pygame.Color(12, 17, 78)
        middle = pygame.Color(76, 49, 182)
        bottom = pygame.Color(226, 119, 181)
        for y in range(self.config.height):
            t = y / max(1, self.config.height - 1)
            color = top.lerp(middle, t / 0.65) if t < 0.65 else middle.lerp(bottom, (t - 0.65) / 0.35)
            pygame.draw.line(fallback, color, (0, y), (self.config.width, y))
        return fallback

    def _create_ground_tile(self, tile_width: int = 256) -> pygame.Surface:
        tile_height = self.config.height - self.config.ground_top_y + 18
        surface = pygame.Surface((tile_width, tile_height), pygame.SRCALPHA)
        cap_h = self.config.ground_cap_height
        grass_top = (121, 190, 190)
        grass_mid = (55, 113, 133)
        grass_shadow = (19, 44, 74)
        dirt_top = (42, 24, 89)
        dirt_mid = (27, 18, 68)
        dirt_bottom = (15, 9, 42)
        stone_color = (61, 40, 109)
        stone_shadow = (26, 17, 62)
        edge_glow = (86, 204, 210)
        leaf = (119, 204, 157)
        flower = (140, 232, 255)
        pygame.draw.rect(surface, grass_top, (0, 0, tile_width, cap_h + 2), border_radius=10)
        pygame.draw.rect(surface, grass_mid, (0, cap_h - 2, tile_width, 10), border_radius=6)
        pygame.draw.line(surface, edge_glow, (0, 2), (tile_width, 2), 2)
        pygame.draw.line(surface, grass_shadow, (0, cap_h + 4), (tile_width, cap_h + 4), 4)
        pygame.draw.rect(surface, dirt_top, (0, cap_h + 5, tile_width, tile_height - cap_h - 5))
        pygame.draw.rect(surface, dirt_mid, (0, cap_h + 28, tile_width, tile_height - cap_h - 28))
        pygame.draw.rect(surface, dirt_bottom, (0, cap_h + 55, tile_width, tile_height - cap_h - 55))
        rng = random.Random(43)
        for _ in range(18):
            radius = rng.randint(18, 34)
            x = rng.randint(-10, tile_width + 10)
            y = rng.randint(cap_h + 26, tile_height + 10)
            pygame.draw.circle(surface, stone_color, (x, y), radius)
            pygame.draw.circle(surface, stone_shadow, (x - radius // 3, y - radius // 5), max(8, radius // 2), 2)
        for tuft_x in (20, 62, 104, 170, 214):
            blade_h = rng.randint(10, 20)
            pygame.draw.line(surface, leaf, (tuft_x, cap_h + 1), (tuft_x - 4, cap_h - blade_h), 3)
            pygame.draw.line(surface, leaf, (tuft_x + 4, cap_h + 1), (tuft_x + 6, cap_h - blade_h + 3), 3)
            pygame.draw.line(surface, leaf, (tuft_x + 1, cap_h + 1), (tuft_x + 1, cap_h - blade_h - 2), 3)
        for flower_x in (48, 132, 196):
            pygame.draw.circle(surface, flower, (flower_x, cap_h - 2), 2)
            pygame.draw.circle(surface, flower, (flower_x + 5, cap_h - 1), 2)
        return surface

    def draw_sky(self, screen: pygame.Surface) -> None:
        screen.blit(self.background, (0, 0))

    def draw_ground(self, screen: pygame.Surface, camera_x: float) -> None:
        tile_width = self.ground_tile.get_width()
        start_x = -int(camera_x % tile_width) - tile_width
        y = self.config.ground_top_y - 2
        for x in range(start_x, self.config.width + tile_width, tile_width):
            screen.blit(self.ground_tile, (x, y))


class DialogueBox:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.active = False
        self.text = ""
        self.font = pygame.font.SysFont("arial", max(26, int(config.height * 0.036)))
        self.hint_font = pygame.font.SysFont("arial", max(18, int(config.height * 0.024)))

    def show(self, text: str) -> None:
        self.text = text
        self.active = True

    def hide(self) -> None:
        self.active = False

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        box_width = int(self.config.width * 0.54)
        padding_x = int(self.config.width * 0.025)
        padding_y = int(self.config.height * 0.026)
        line_spacing = max(8, int(self.config.height * 0.012))
        lines = wrap_text(self.text, self.font, box_width - padding_x * 2)
        rendered = [self.font.render(line, True, (234, 235, 255)) for line in lines]
        hint = self.hint_font.render("Enter - tovább", True, (176, 198, 245))
        text_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1) * line_spacing
        box_height = padding_y * 2 + text_h + hint.get_height() + line_spacing + 10
        box_rect = pygame.Rect(0, 0, box_width, box_height)
        box_rect.center = (self.config.width // 2, self.config.height // 2)
        shadow = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=22)
        screen.blit(shadow, box_rect.move(0, 8).topleft)
        panel = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 20, 54, 220), panel.get_rect(), border_radius=22)
        pygame.draw.rect(panel, (109, 133, 228, 235), panel.get_rect(), 2, border_radius=22)
        screen.blit(panel, box_rect.topleft)
        current_y = box_rect.y + padding_y
        for surface in rendered:
            text_rect = surface.get_rect(centerx=box_rect.centerx, y=current_y)
            screen.blit(surface, text_rect)
            current_y += surface.get_height() + line_spacing
        hint_rect = hint.get_rect(centerx=box_rect.centerx, bottom=box_rect.bottom - padding_y + 2)
        screen.blit(hint, hint_rect)


class ThornBush:
    def __init__(self, world_x: float, ground_y: int, scale: float = 1.0) -> None:
        self.world_x = world_x
        self.ground_y = ground_y
        self.trigger_distance = 460
        self.stop_distance = 420
        self.surface = self._create_surface(scale)

    def _create_surface(self, scale: float) -> pygame.Surface:
        width = int(620 * scale)
        height = int(300 * scale)
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        rng = random.Random(901)
        branch_dark = (24, 16, 52)
        branch_mid = (43, 28, 84)
        thorn = (146, 163, 255)
        thorn_shadow = (73, 47, 126)
        leaf = (36, 68, 84)
        leaf_glow = (94, 111, 174)
        haze = (104, 66, 165, 55)
        for i in range(8):
            pygame.draw.ellipse(surface, haze, (int(width * 0.07) + i * 30, int(height * 0.30) + (i % 3) * 8, int(width * 0.75), int(height * 0.45)))
        bases = [(int(width * 0.18), int(height * 0.82)), (int(width * 0.33), int(height * 0.84)), (int(width * 0.50), int(height * 0.85)), (int(width * 0.67), int(height * 0.84)), (int(width * 0.82), int(height * 0.80))]
        for base_x, base_y in bases:
            points = [(base_x, base_y)]
            x, y = base_x, base_y
            for _ in range(rng.randint(5, 8)):
                x += rng.randint(-60, 60)
                y -= rng.randint(20, 40)
                points.append((x, y))
            pygame.draw.lines(surface, branch_dark, False, points, 12)
            pygame.draw.lines(surface, branch_mid, False, points, 6)
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                for direction in (-1, 1):
                    length = rng.randint(16, 32)
                    pygame.draw.polygon(surface, thorn_shadow, [(mid_x, mid_y), (mid_x + direction * length, mid_y - rng.randint(8, 16)), (mid_x + direction * (length // 2), mid_y + 7)])
        for _ in range(26):
            cx = rng.randint(40, width - 40)
            cy = rng.randint(int(height * 0.25), int(height * 0.82))
            radius = rng.randint(20, 36)
            pygame.draw.circle(surface, leaf, (cx, cy), radius)
            pygame.draw.circle(surface, leaf_glow, (cx - radius // 4, cy - radius // 4), max(8, radius // 2), 2)
        return surface

    @property
    def left_edge(self) -> float:
        return self.world_x

    def trigger_x(self) -> float:
        return self.left_edge - self.trigger_distance

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        screen_x = int(self.world_x - camera_x)
        rect = self.surface.get_rect(bottomleft=(screen_x, self.ground_y + 18))
        screen.blit(self.surface, rect)


class Player:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        asset_dir = Path(__file__).parent / "assets"
        self.stop_frame_times = create_stop_frame_times()
        try:
            frames = load_image_sequence(asset_dir, FRAME_FILE_PREFIX, FRAME_FILE_EXTENSION, FRAME_FILE_DIGITS, TOTAL_FRAME_COUNT, SPRITE_HEIGHT)
            self.run_frames = frames[RUN_START_FRAME : RUN_END_FRAME + 1]
            self.stop_frames = frames[STOP_START_FRAME : STOP_END_FRAME + 1]
            self.jump_frames = load_sprite_sheet_grid(asset_dir / JUMP_SHEET_FILENAME, JUMP_SHEET_COLUMNS, JUMP_SHEET_ROWS, SPRITE_HEIGHT, REFERENCE_STANCE_SOURCE_HEIGHT)
            if not self.jump_frames:
                self.jump_frames = [self.run_frames[0], self.run_frames[len(self.run_frames) // 4], self.run_frames[len(self.run_frames) // 2], self.run_frames[-1]]
        except Exception:
            self.run_frames, self.stop_frames, self.jump_frames = create_placeholder_wolf_frames(SPRITE_HEIGHT)
        self.world_x = float(self.config.left_frame_x + 140)
        self.y = float(self.config.ground_top_y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing_right = True
        self.on_ground = True
        self.movement_pressed = False
        self.was_movement_pressed = False
        self.jump_pressed_last_frame = False
        self.animation_state = "idle"
        self.animation_timer = 0.0
        self.jump_phase = "up"
        self.jump_phase_timer = 0.0
        self.collision_half_width = 38

    def start_animation(self, state: str) -> None:
        if self.animation_state != state:
            self.animation_state = state
            self.animation_timer = 0.0

    def set_jump_phase(self, phase: str) -> None:
        if self.jump_phase != phase:
            self.jump_phase = phase
            self.jump_phase_timer = 0.0

    def handle_input(self, dt: float, obstacle_left_edge: float | None, controls_enabled: bool) -> None:
        keys = pygame.key.get_pressed()
        moving_left = controls_enabled and (keys[pygame.K_LEFT] or keys[pygame.K_a])
        moving_right = controls_enabled and (keys[pygame.K_RIGHT] or keys[pygame.K_d])
        jump_pressed = controls_enabled and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP])
        horizontal_input = int(moving_right) - int(moving_left)
        self.movement_pressed = horizontal_input != 0
        self.vx = horizontal_input * PLAYER_SPEED
        if horizontal_input < 0:
            self.facing_right = False
        elif horizontal_input > 0:
            self.facing_right = True
        if jump_pressed and not self.jump_pressed_last_frame and self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False
            self.jump_phase = "up"
            self.jump_phase_timer = 0.0
            self.start_animation("jump")
        self.jump_pressed_last_frame = jump_pressed
        next_world_x = max(float(self.config.left_frame_x), self.world_x + self.vx * dt)
        if obstacle_left_edge is not None:
            next_world_x = min(next_world_x, obstacle_left_edge - self.collision_half_width)
        self.world_x = next_world_x

    def update_physics(self, dt: float) -> None:
        if self.on_ground:
            return
        self.vy = min(MAX_FALL_SPEED, self.vy + GRAVITY * dt)
        self.y += self.vy * dt
        if self.y >= self.config.ground_top_y:
            self.y = float(self.config.ground_top_y)
            self.vy = 0.0
            self.on_ground = True

    def update_animation(self, dt: float) -> None:
        if not self.on_ground:
            self.start_animation("jump")
            self.set_jump_phase("up" if self.vy < 0 else "down")
            self.animation_timer += dt
            self.jump_phase_timer += dt
            self.was_movement_pressed = self.movement_pressed
            return
        if self.animation_state == "jump":
            self.start_animation("run" if self.movement_pressed else "idle")
        if self.movement_pressed:
            self.start_animation("run")
            self.animation_timer += dt
        else:
            if self.was_movement_pressed:
                self.start_animation("stop")
            if self.animation_state == "stop":
                self.animation_timer += dt
                stop_duration = sum(self.stop_frame_times)
                if self.animation_timer >= stop_duration:
                    self.animation_timer = stop_duration
                    self.animation_state = "idle"
        self.was_movement_pressed = self.movement_pressed

    def current_jump_image(self) -> pygame.Surface:
        frame_count = len(self.jump_frames)
        if frame_count <= 4:
            return self.jump_frames[min(int(self.animation_timer / 0.13), frame_count - 1)]
        ascend_count = frame_count // 2
        descend_count = frame_count - ascend_count
        if self.jump_phase == "up":
            frame_index = min(int(self.jump_phase_timer / JUMP_ASCEND_FRAME_TIME), ascend_count - 1)
        else:
            times = JUMP_DESCEND_FRAME_TIMES[:descend_count]
            if len(times) < descend_count:
                times += [JUMP_DESCEND_FRAME_TIMES[-1]] * (descend_count - len(times))
            frame_index = ascend_count + get_frame_index_from_timer(self.jump_phase_timer, times)
        return self.jump_frames[frame_index]

    def current_image(self) -> pygame.Surface:
        if self.animation_state == "jump":
            image = self.current_jump_image()
        elif self.animation_state == "run":
            image = self.run_frames[int(self.animation_timer / ANIMATION_FRAME_TIME) % len(self.run_frames)]
        elif self.animation_state == "stop":
            image = self.stop_frames[get_frame_index_from_timer(self.animation_timer, self.stop_frame_times)]
        else:
            image = self.stop_frames[-1]
        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)
        return image

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        screen_x = int(self.world_x - camera_x)
        height_above_ground = max(0.0, self.config.ground_top_y - self.y)
        shadow_scale = max(0.42, 1.0 - height_above_ground / 270.0)
        shadow_rect = pygame.Rect(0, 0, int(96 * shadow_scale), int(16 * shadow_scale))
        shadow_rect.center = (screen_x, self.config.ground_top_y + 8)
        pygame.draw.ellipse(screen, (33, 27, 72), shadow_rect)
        image = self.current_image()
        rect = image.get_rect(midbottom=(screen_x, int(self.y)))
        screen.blit(image, rect)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        info = pygame.display.Info()
        self.config = WorldConfig(max(960, info.current_w), max(540, info.current_h))
        self.screen = pygame.display.set_mode((self.config.width, self.config.height), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.background = StaticBackground(self.config)
        self.player = Player(self.config)
        self.dialogue = DialogueBox(self.config)
        self.bush = ThornBush(world_x=2500, ground_y=self.config.ground_top_y, scale=max(1.0, self.config.height / 700))
        self.camera_x = 0.0
        self.cinematic_camera_active = False
        self.cinematic_camera_target_x = 0.0
        self.pending_obstacle_text = ""
        self.bush_event_triggered = False
        self.debug_font = pygame.font.SysFont("arial", max(18, int(self.config.height * 0.024)))
        self.running = True
        self.dialogue.show(INTRO_TEXT)

    def controls_enabled(self) -> bool:
        return not self.dialogue.active and not self.cinematic_camera_active

    def obstacle_left_edge(self) -> float | None:
        return self.bush.left_edge if self.bush_event_triggered else None

    def start_obstacle_reveal(self, obstacle_left_edge: float, stop_distance: float, text: str) -> None:
        """Közös, újrahasználható akadály-megjelenítés minden nagy akadályhoz."""
        self.player.world_x = obstacle_left_edge - stop_distance
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.cinematic_camera_active = True
        self.cinematic_camera_target_x = max(0.0, self.player.world_x - self.config.left_frame_x)
        self.pending_obstacle_text = text
        if self.dialogue.active:
            self.dialogue.hide()

    def trigger_bush_event(self) -> None:
        self.bush_event_triggered = True
        self.start_obstacle_reveal(self.bush.left_edge, self.bush.stop_distance, THORN_TEXT)

    def update_cinematic_camera(self, dt: float) -> bool:
        if not self.cinematic_camera_active:
            return False
        distance = self.cinematic_camera_target_x - self.camera_x
        step = OBSTACLE_CAMERA_REVEAL_SPEED * dt
        if abs(distance) <= step + OBSTACLE_CAMERA_REVEAL_EPSILON:
            self.camera_x = self.cinematic_camera_target_x
            self.cinematic_camera_active = False
            if self.pending_obstacle_text:
                self.dialogue.show(self.pending_obstacle_text)
                self.pending_obstacle_text = ""
        else:
            self.camera_x += math.copysign(step, distance)
        return True

    def update_camera(self, dt: float) -> None:
        if self.update_cinematic_camera(dt):
            return
        if self.dialogue.active:
            return
        screen_x = self.player.world_x - self.camera_x
        target_camera_x = self.camera_x
        if screen_x > self.config.right_edge_x:
            target_camera_x = self.player.world_x - self.config.center_x
        elif screen_x < self.config.left_frame_x and self.camera_x > 0:
            target_camera_x = self.player.world_x - self.config.left_frame_x
        target_camera_x = max(0.0, target_camera_x)
        smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
        self.camera_x += (target_camera_x - self.camera_x) * smooth_factor

    def draw_help(self) -> None:
        text = "Mozgás: A/D vagy ←/→    Ugrás: Space / W / ↑    Enter: üzenet bezárása    Esc: kilépés"
        surface = self.debug_font.render(text, True, (226, 232, 255))
        bg = pygame.Surface((surface.get_width() + 22, surface.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 12, 34, 110), bg.get_rect(), border_radius=14)
        self.screen.blit(bg, (18, 18))
        self.screen.blit(surface, (29, 25))

    def draw(self) -> None:
        self.background.draw_sky(self.screen)
        self.bush.draw(self.screen, self.camera_x)
        self.background.draw_ground(self.screen, self.camera_x)
        self.player.draw(self.screen, self.camera_x)
        self.draw_help()
        self.dialogue.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_RETURN and self.dialogue.active:
                        self.dialogue.hide()
            if not self.bush_event_triggered and self.player.world_x >= self.bush.trigger_x():
                self.trigger_bush_event()
            self.player.handle_input(dt, self.obstacle_left_edge(), self.controls_enabled())
            self.player.update_physics(dt)
            self.player.update_animation(dt)
            self.update_camera(dt)
            self.draw()
        pygame.quit()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
