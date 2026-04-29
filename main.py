from __future__ import annotations

from pathlib import Path
from collections import deque
import random
import textwrap
import math
import pygame

FPS = 60
PLAYER_SPEED = 300
SPRITE_HEIGHT = 132
JUMP_SPEED = 820
GRAVITY = 1700
MAX_FALL_SPEED = 1250

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


class WorldConfig:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.left_frame_x = max(70, int(width * 0.10))
        self.right_edge_x = int(width * 0.82)
        # Nagyobb érték = gyorsabban, de még finoman éri utol a kamera a farkast.
        self.camera_smoothness = 5.8
        self.ground_top_y = int(height * 0.885)
        self.ground_cap_height = max(12, int(height * 0.022))
        self.ground_depth = height - self.ground_top_y


def is_transparency_green(r: int, g: int, b: int, a: int) -> bool:
    if a == 0:
        return False

    return (
        g >= GREEN_ALPHA_MIN_GREEN
        and g >= r + GREEN_ALPHA_DOMINANCE
        and g >= b + GREEN_ALPHA_DOMINANCE
    )


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


def load_sprite_sheet_grid(
    path: Path,
    columns: int,
    rows: int,
    target_height: int,
    reference_source_height: int,
) -> list[pygame.Surface]:
    if not path.exists():
        return []

    sheet = pygame.image.load(str(path)).convert_alpha()
    sheet_width, sheet_height = sheet.get_size()
    cell_width = sheet_width // columns
    cell_height = sheet_height // rows
    frames: list[pygame.Surface] = []

    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(
                column * cell_width + 1,
                row * cell_height + 1,
                cell_width - 2,
                cell_height - 2,
            )
            frame = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frame = remove_light_background_from_edges(frame)
            frame = trim_transparent_padding(frame, padding=2)
            scale = target_height / reference_source_height
            frames.append(scale_surface_by_factor(frame, scale))

    return frames


def load_image_sequence(
    folder: Path,
    prefix: str,
    extension: str,
    digits: int,
    frame_count: int,
    target_height: int,
) -> list[pygame.Surface]:
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
        raise FileNotFoundError(
            f"Hiányzó animációs fájl(ok) az assets mappából: {shown}{extra}"
        )

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
    current_line = words[0]

    for word in words[1:]:
        test_line = f"{current_line} {word}"
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def create_background_surface(config: WorldConfig) -> pygame.Surface:
    # A statikus háttér a mellékelt kép.
    # Tedd a main.py mellé image.png néven, vagy assets/static_background.png néven.
    candidates = [
        Path(__file__).parent / "image.png",
        Path(__file__).parent / "assets" / "static_background.png",
        Path("/mnt/data/image.png"),
        Path("/mnt/data/ghostwriter_images/context/6db1dec5-6c0a-59c9-8d3b-5a4f107cae9a.png"),
    ]

    background_source = next((path for path in candidates if path.exists()), None)
    if background_source is not None:
        image = pygame.image.load(str(background_source)).convert()
        return pygame.transform.smoothscale(image, (config.width, config.height))

    fallback = pygame.Surface((config.width, config.height))
    top_color = pygame.Color(12, 17, 78)
    middle_color = pygame.Color(76, 49, 182)
    bottom_color = pygame.Color(226, 119, 181)

    for y in range(config.height):
        t = y / max(1, config.height - 1)
        if t < 0.65:
            blend = t / 0.65
            color = top_color.lerp(middle_color, blend)
        else:
            blend = (t - 0.65) / 0.35
            color = middle_color.lerp(bottom_color, blend)
        pygame.draw.line(fallback, color, (0, y), (config.width, y))

    pygame.draw.circle(fallback, (245, 233, 202), (int(config.width * 0.18), int(config.height * 0.19)), int(config.height * 0.08))
    return fallback


def create_ground_tile(config: WorldConfig, tile_width: int = 256) -> pygame.Surface:
    tile_height = config.height - config.ground_top_y + 16
    surface = pygame.Surface((tile_width, tile_height), pygame.SRCALPHA)

    grass_top = (121, 190, 190)
    grass_mid = (55, 113, 133)
    grass_shadow = (19, 44, 74)
    dirt_top = (42, 24, 89)
    dirt_mid = (27, 18, 68)
    dirt_bottom = (15, 9, 42)
    stone_color = (61, 40, 109)
    stone_shadow = (26, 17, 62)
    edge_glow = (86, 204, 210)
    flower = (140, 232, 255)
    leaf = (119, 204, 157)

    cap_h = config.ground_cap_height
    pygame.draw.rect(surface, grass_top, (0, 0, tile_width, cap_h + 2), border_radius=10)
    pygame.draw.rect(surface, grass_mid, (0, cap_h - 2, tile_width, 10), border_radius=6)
    pygame.draw.line(surface, edge_glow, (0, 2), (tile_width, 2), 2)
    pygame.draw.line(surface, grass_shadow, (0, cap_h + 4), (tile_width, cap_h + 4), 4)

    dirt_rect = pygame.Rect(0, cap_h + 5, tile_width, tile_height - cap_h - 5)
    pygame.draw.rect(surface, dirt_top, dirt_rect)
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

    ear1 = [(int(width * 0.59), int(height * 0.27)), (int(width * 0.62), int(height * 0.11)), (int(width * 0.68), int(height * 0.26))]
    ear2 = [(int(width * 0.67), int(height * 0.28)), (int(width * 0.70), int(height * 0.12)), (int(width * 0.76), int(height * 0.29))]
    pygame.draw.polygon(surf, dark, ear1)
    pygame.draw.polygon(surf, dark, ear2)

    chest = pygame.Rect(int(width * 0.47), int(height * 0.39), int(width * 0.18), int(height * 0.23))
    pygame.draw.ellipse(surf, light, chest)
    tail = [(int(width * 0.18), int(height * 0.47)), (int(width * 0.02), int(height * 0.34)), (int(width * 0.12), int(height * 0.58))]
    pygame.draw.polygon(surf, dark, tail)

    offset = int(6 * leg_phase)
    legs = [
        (int(width * 0.31), int(height * 0.57), -offset),
        (int(width * 0.42), int(height * 0.58), offset),
        (int(width * 0.54), int(height * 0.57), offset),
        (int(width * 0.63), int(height * 0.57), -offset),
    ]
    for x, y, dx in legs:
        pygame.draw.line(surf, dark, (x, y), (x + dx, int(height * 0.90)), 6)
        pygame.draw.line(surf, light, (x + 2, y + 2), (x + dx + 2, int(height * 0.90)), 2)

    pygame.draw.circle(surf, glow, (int(width * 0.72), int(height * 0.34)), 3)
    pygame.draw.line(surf, dark, (int(width * 0.76), int(height * 0.37)), (int(width * 0.84), int(height * 0.41)), 3)
    return surf


def create_placeholder_wolf_frames(target_height: int) -> tuple[list[pygame.Surface], list[pygame.Surface], list[pygame.Surface]]:
    width = int(target_height * 1.5)
    run_frames = [create_placeholder_frame(width, target_height, leg_phase=phase) for phase in (-1.0, -0.35, 0.35, 1.0)]
    stop_frame = create_placeholder_frame(width, target_height, leg_phase=0.0)
    stop_frames = [stop_frame for _ in range(STOP_END_FRAME - STOP_START_FRAME + 1)]
    jump_frames = []
    for stretch in (1.0, 1.05, 1.1, 1.08, 1.0, 0.95, 0.92, 0.98):
        surf = create_placeholder_frame(width, target_height, leg_phase=0.0)
        new_height = max(1, int(target_height * stretch))
        new_width = max(1, int(surf.get_width() * (0.92 if stretch > 1 else 1.03)))
        jump_frames.append(pygame.transform.smoothscale(surf, (new_width, new_height)))
    return run_frames, stop_frames, jump_frames


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

        text_surfaces = [self.font.render(line, True, (234, 235, 255)) for line in lines]
        text_height = sum(surface.get_height() for surface in text_surfaces)
        text_height += max(0, len(text_surfaces) - 1) * line_spacing
        hint_surface = self.hint_font.render("Enter - tovább", True, (176, 198, 245))

        box_height = padding_y * 2 + text_height + hint_surface.get_height() + line_spacing + 10
        box_rect = pygame.Rect(0, 0, box_width, box_height)
        box_rect.center = (self.config.width // 2, self.config.height // 2)

        shadow = box_rect.move(0, 8)
        shadow_surf = pygame.Surface(shadow.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 90), shadow_surf.get_rect(), border_radius=22)
        screen.blit(shadow_surf, shadow.topleft)

        panel = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 20, 54, 220), panel.get_rect(), border_radius=22)
        pygame.draw.rect(panel, (109, 133, 228, 235), panel.get_rect(), 2, border_radius=22)
        inner = panel.get_rect().inflate(-14, -14)
        pygame.draw.rect(panel, (40, 48, 102, 85), inner, 1, border_radius=18)
        screen.blit(panel, box_rect.topleft)

        current_y = box_rect.y + padding_y
        for surface in text_surfaces:
            text_rect = surface.get_rect(centerx=box_rect.centerx, y=current_y)
            screen.blit(surface, text_rect)
            current_y += surface.get_height() + line_spacing

        hint_rect = hint_surface.get_rect(centerx=box_rect.centerx, bottom=box_rect.bottom - padding_y + 2)
        screen.blit(hint_surface, hint_rect)


class ThornBush:
    def __init__(self, world_x: float, ground_y: int, scale: float = 1.0) -> None:
        self.world_x = world_x
        self.ground_y = ground_y
        self.surface = self._create_surface(scale)
        self.width = self.surface.get_width()
        self.height = self.surface.get_height()
        self.trigger_distance = 430
        self.stop_distance = 420

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
            haze_rect = pygame.Rect(int(width * 0.07) + i * 30, int(height * 0.30) + (i % 3) * 8, int(width * 0.75), int(height * 0.45))
            pygame.draw.ellipse(surface, haze, haze_rect)

        bases = [
            (int(width * 0.18), int(height * 0.82)),
            (int(width * 0.33), int(height * 0.84)),
            (int(width * 0.50), int(height * 0.85)),
            (int(width * 0.67), int(height * 0.84)),
            (int(width * 0.82), int(height * 0.80)),
        ]

        for base_x, base_y in bases:
            points = [(base_x, base_y)]
            current_x = base_x
            current_y = base_y
            for _ in range(rng.randint(5, 8)):
                current_x += rng.randint(-60, 60)
                current_y -= rng.randint(20, 40)
                points.append((current_x, current_y))

            pygame.draw.lines(surface, branch_dark, False, points, 12)
            pygame.draw.lines(surface, branch_mid, False, points, 6)

            for x1, y1, x2, y2 in zip((p[0] for p in points), (p[1] for p in points), (p[0] for p in points[1:]), (p[1] for p in points[1:])):
                mid_x = (x1 + x2) // 2
                mid_y = (y1 + y2) // 2
                for direction in (-1, 1):
                    thorn_length = rng.randint(16, 32)
                    thorn_base = (mid_x, mid_y)
                    thorn_tip = (mid_x + direction * thorn_length, mid_y - rng.randint(8, 16))
                    thorn_side = (mid_x + direction * (thorn_length // 2), mid_y + 7)
                    pygame.draw.polygon(surface, thorn_shadow, [thorn_base, thorn_tip, thorn_side])
                    pygame.draw.polygon(surface, thorn, [thorn_base, thorn_tip, thorn_side], 1)

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
        bottom_y = self.ground_y + 18
        rect = self.surface.get_rect(bottomleft=(screen_x, bottom_y))
        screen.blit(self.surface, rect)


class Player:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        asset_dir = Path(__file__).parent / "assets"
        self.stop_frame_times = create_stop_frame_times()

        try:
            frames = load_image_sequence(
                folder=asset_dir,
                prefix=FRAME_FILE_PREFIX,
                extension=FRAME_FILE_EXTENSION,
                digits=FRAME_FILE_DIGITS,
                frame_count=TOTAL_FRAME_COUNT,
                target_height=SPRITE_HEIGHT,
            )
            needed_frame_count = STOP_END_FRAME + 1
            if len(frames) < needed_frame_count:
                raise ValueError(
                    f"Csak {len(frames)} képkocka lett betöltve. Legalább {needed_frame_count} kell."
                )
            self.run_frames = frames[RUN_START_FRAME : RUN_END_FRAME + 1]
            self.stop_frames = frames[STOP_START_FRAME : STOP_END_FRAME + 1]
            self.jump_frames = load_sprite_sheet_grid(
                path=asset_dir / JUMP_SHEET_FILENAME,
                columns=JUMP_SHEET_COLUMNS,
                rows=JUMP_SHEET_ROWS,
                target_height=SPRITE_HEIGHT,
                reference_source_height=REFERENCE_STANCE_SOURCE_HEIGHT,
            )
            if not self.jump_frames:
                self.jump_frames = [
                    self.run_frames[0],
                    self.run_frames[len(self.run_frames) // 4],
                    self.run_frames[len(self.run_frames) // 2],
                    self.run_frames[-1],
                ]
        except Exception:
            self.run_frames, self.stop_frames, self.jump_frames = create_placeholder_wolf_frames(SPRITE_HEIGHT)

        self.world_x = float(max(120, int(config.width * 0.16)))
        self.y = float(config.ground_top_y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing_right = True
        self.on_ground = True
        self.jump_pressed_last_frame = False
        self.movement_pressed = False
        self.was_movement_pressed = False
        self.animation_state = "idle"
        self.animation_timer = 0.0
        self.jump_phase = "up"
        self.jump_phase_timer = 0.0
        self.collision_half_width = 38

    def get_current_width(self) -> int:
        return self.current_image().get_width()

    def start_animation(self, state: str) -> None:
        if self.animation_state != state:
            self.animation_state = state
            self.animation_timer = 0.0

    def set_jump_phase(self, phase: str) -> None:
        if self.jump_phase != phase:
            self.jump_phase = phase
            self.jump_phase_timer = 0.0

    def current_jump_image(self) -> pygame.Surface:
        frame_count = len(self.jump_frames)
        if frame_count <= 4:
            frame_index = min(int(self.animation_timer / 0.13), frame_count - 1)
            return self.jump_frames[frame_index]

        ascend_count = frame_count // 2
        descend_count = frame_count - ascend_count

        if self.jump_phase == "up":
            local_index = min(int(self.jump_phase_timer / JUMP_ASCEND_FRAME_TIME), ascend_count - 1)
            frame_index = local_index
        else:
            descend_frame_times = JUMP_DESCEND_FRAME_TIMES[:descend_count]
            if len(descend_frame_times) < descend_count:
                descend_frame_times += [JUMP_DESCEND_FRAME_TIMES[-1]] * (descend_count - len(descend_frame_times))
            local_index = get_frame_index_from_timer(self.jump_phase_timer, descend_frame_times)
            frame_index = ascend_count + local_index

        return self.jump_frames[frame_index]

    def current_image(self) -> pygame.Surface:
        if self.animation_state == "jump":
            image = self.current_jump_image()
        elif self.animation_state == "run":
            frame_index = int(self.animation_timer / ANIMATION_FRAME_TIME) % len(self.run_frames)
            image = self.run_frames[frame_index]
        elif self.animation_state == "stop":
            frame_index = get_frame_index_from_timer(self.animation_timer, self.stop_frame_times)
            image = self.stop_frames[frame_index]
        else:
            image = self.stop_frames[-1]

        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)
        return image

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

        next_world_x = self.world_x + self.vx * dt

        # Balra is lehet haladni, de a világ legelején a farkas nem mehet ki
        # a képernyő bal szélén túl.
        min_x = float(self.config.left_frame_x)
        next_world_x = max(min_x, next_world_x)

        if obstacle_left_edge is not None:
            max_x = obstacle_left_edge - self.collision_half_width
            next_world_x = min(next_world_x, max_x)

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
            if self.vy < 0:
                self.set_jump_phase("up")
            else:
                self.set_jump_phase("down")
            self.animation_timer += dt
            self.jump_phase_timer += dt
            self.was_movement_pressed = self.movement_pressed
            return

        if self.animation_state == "jump":
            if self.movement_pressed:
                self.start_animation("run")
            else:
                self.start_animation("idle")

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

        self.background = create_background_surface(self.config)
        self.ground_tile = create_ground_tile(self.config)
        self.player = Player(self.config)
        self.dialogue = DialogueBox(self.config)
        self.bush = ThornBush(world_x=2500, ground_y=self.config.ground_top_y, scale=max(1.0, self.config.height / 700))

        self.camera_x = 0.0
        self.bush_event_triggered = False
        self.debug_font = pygame.font.SysFont("arial", max(18, int(self.config.height * 0.024)))
        self.running = True

        self.dialogue.show(INTRO_TEXT)

    def controls_enabled(self) -> bool:
        return not self.dialogue.active

    def obstacle_left_edge(self) -> float | None:
        return self.bush.left_edge if self.bush_event_triggered else None

    def trigger_bush_event(self) -> None:
        self.bush_event_triggered = True
        self.player.world_x = self.bush.left_edge - self.bush.stop_distance
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.camera_x = max(0.0, self.player.world_x - self.config.left_frame_x)
        self.dialogue.show(THORN_TEXT)

    def update_camera(self, dt: float) -> None:
        if self.dialogue.active and self.bush_event_triggered:
            target_camera_x = max(0.0, self.player.world_x - self.config.left_frame_x)
        else:
            # Folyamatos, simított kamera: jobbra és balra is követi a farkast,
            # de a pálya elején nem görget negatív irányba.
            target_camera_x = max(0.0, self.player.world_x - self.config.center_x)

        smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
        self.camera_x += (target_camera_x - self.camera_x) * smooth_factor

    def draw_ground(self) -> None:
        tile_width = self.ground_tile.get_width()
        start_x = -int(self.camera_x % tile_width) - tile_width
        y = self.config.ground_top_y - 2
        for x in range(start_x, self.config.width + tile_width, tile_width):
            self.screen.blit(self.ground_tile, (x, y))

    def draw_help(self) -> None:
        text = "Mozgás: A/D vagy ←/→    Ugrás: Space / W / ↑    Enter: üzenet bezárása    Esc: kilépés"
        surface = self.debug_font.render(text, True, (226, 232, 255))
        bg = pygame.Surface((surface.get_width() + 22, surface.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 12, 34, 110), bg.get_rect(), border_radius=14)
        self.screen.blit(bg, (18, 18))
        self.screen.blit(surface, (29, 25))

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        self.bush.draw(self.screen, self.camera_x)
        self.draw_ground()
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

            if (
                not self.bush_event_triggered
                and self.player.world_x >= self.bush.trigger_x()
            ):
                self.trigger_bush_event()

            self.player.handle_input(
                dt,
                obstacle_left_edge=self.obstacle_left_edge(),
                controls_enabled=self.controls_enabled(),
            )
            self.player.update_physics(dt)
            self.player.update_animation(dt)
            self.update_camera(dt)
            self.draw()

        pygame.quit()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
