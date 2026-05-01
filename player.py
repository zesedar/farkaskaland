"""A farkas játékos osztálya és a sprite-betöltő/feldolgozó segédfüggvények."""
from __future__ import annotations

from collections import deque
from pathlib import Path

import pygame

from constants import (
    ANIMATION_FRAME_TIME,
    FAST_STOP_FILE_END,
    FAST_STOP_FILE_START,
    FAST_STOP_FRAME_TIME,
    FRAME_FILE_DIGITS,
    FRAME_FILE_EXTENSION,
    FRAME_FILE_PREFIX,
    GRAVITY,
    GREEN_ALPHA_DOMINANCE,
    GREEN_ALPHA_MIN_GREEN,
    HOWL_DURATION,
    HOWL_FOLDER_NAME,
    HOWL_FRAME_COUNT,
    HOWL_FRAME_PREFIX,
    HOWL_FRAME_TIME,
    HOWL_SOUND_FILENAME,
    HOWL_SOUND_VOLUME,
    HOWL_SCALE,
    JUMP_ASCEND_FRAME_TIME,
    JUMP_DESCEND_FRAME_TIMES,
    JUMP_SHEET_COLUMNS,
    JUMP_SHEET_FILENAME,
    JUMP_SHEET_ROWS,
    JUMP_SPEED,
    MAX_FALL_SPEED,
    PLAYER_SPEED,
    REFERENCE_STANCE_SOURCE_HEIGHT,
    RUN_END_FRAME,
    RUN_START_FRAME,
    SITTING_FRAME_FILENAME,
    SPRITE_HEIGHT,
    STOP_END_FRAME,
    STOP_START_FRAME,
    TOTAL_FRAME_COUNT,
)
from world_config import WorldConfig


# ---------------------------------------------------------------------------
# Kép-feldolgozás: zöld háttér transzparenssé alakítása, világos peremek
# eltávolítása, transzparens padding levágása. Ezeket a sprite-loaderek
# használják.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sprite-betöltés
# ---------------------------------------------------------------------------

def load_frame_file(path: Path, target_height: int) -> pygame.Surface:
    frame = pygame.image.load(str(path)).convert_alpha()
    frame = remove_green_transparency(frame)
    return scale_surface_to_height(frame, target_height)


def load_sprite_sheet_grid(path: Path, columns: int, rows: int, target_height: int,
                           reference_source_height: int) -> list[pygame.Surface]:
    if not path.exists():
        return []
    sheet = pygame.image.load(str(path)).convert_alpha()
    sheet_width, sheet_height = sheet.get_size()
    cell_width = sheet_width // columns
    cell_height = sheet_height // rows
    frames: list[pygame.Surface] = []
    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(column * cell_width + 1, row * cell_height + 1,
                               cell_width - 2, cell_height - 2)
            frame = pygame.Surface(rect.size, pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frame = remove_light_background_from_edges(frame)
            frame = trim_transparent_padding(frame, padding=2)
            frames.append(scale_surface_by_factor(frame, target_height / reference_source_height))
    return frames


def load_image_sequence(folder: Path, prefix: str, extension: str, digits: int,
                        frame_count: int, target_height: int) -> list[pygame.Surface]:
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


def load_transparent_image_sequence(folder: Path, prefix: str, extension: str,
                                    frame_count: int, target_height: int) -> list[pygame.Surface]:
    """Átlátszó hátterű, számozott képsorozat betöltése.

    Az üvöltés képei a feladat szerint assets/uvolt/uvolt1.png ... uvolt5.png
    neveken vannak, ezért itt nincs 0-val kitöltött sorszám. A teljesen
    transzparens széleket levágjuk, hogy az animáció ne legyen túl kicsi, ha a
    PNG-k nagyobb vászonra vannak mentve.
    """
    frames: list[pygame.Surface] = []
    for file_number in range(1, frame_count + 1):
        path = folder / f"{prefix}{file_number}{extension}"
        if not path.exists():
            continue
        frame = pygame.image.load(str(path)).convert_alpha()
        frame = remove_green_transparency(frame)
        frame = trim_transparent_padding(frame, padding=6)
        frames.append(scale_surface_to_height(frame, target_height))
    return frames


# ---------------------------------------------------------------------------
# Animáció-segédek
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Placeholder-frame generátor (csak ha az assets nem érhető el)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class Player:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        asset_dir = Path(__file__).parent / "assets"
        self.stop_frame_times = create_stop_frame_times()
        try:
            frames = load_image_sequence(asset_dir, FRAME_FILE_PREFIX, FRAME_FILE_EXTENSION,
                                         FRAME_FILE_DIGITS, TOTAL_FRAME_COUNT, SPRITE_HEIGHT)
            self.run_frames = frames[RUN_START_FRAME : RUN_END_FRAME + 1]
            self.stop_frames = frames[STOP_START_FRAME : STOP_END_FRAME + 1]
            self.jump_frames = load_sprite_sheet_grid(
                asset_dir / JUMP_SHEET_FILENAME,
                JUMP_SHEET_COLUMNS, JUMP_SHEET_ROWS,
                SPRITE_HEIGHT, REFERENCE_STANCE_SOURCE_HEIGHT,
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
        # Külön ülő kép (ulelorenez.png) - ha az assets könyvtárban megtalálható, betöltjük.
        # Ezt a 6. jelenetben használjuk, amikor a csúcson megpihen a farkas.
        # Ha nincs ilyen fájl, fallback: az utolsó stop frame (idle pozíció).
        sitting_path = asset_dir / SITTING_FRAME_FILENAME
        if sitting_path.exists():
            try:
                # ~18%-kal nagyobb mint a normál SPRITE_HEIGHT, hogy a farkas
                # a talajon üljön és ne a levegőben (a kép aljának üres
                # tartománya így lefelé tolódik a talajszint alá).
                self.sitting_frame = load_frame_file(sitting_path, int(SPRITE_HEIGHT * 1.12))
            except Exception:
                self.sitting_frame = self.stop_frames[-1]
        else:
            self.sitting_frame = self.stop_frames[-1]

        # Üvöltés animáció (A billentyű): assets/uvolt/uvolt1.png ... uvolt5.png.
        # Ha a képek még nincsenek a helyükön, nem áll meg a játék: az idle frame
        # marad biztonsági fallbackként.
        howl_folder = asset_dir / HOWL_FOLDER_NAME
        self.howl_frames = load_transparent_image_sequence(
            howl_folder,
            HOWL_FRAME_PREFIX,
            FRAME_FILE_EXTENSION,
            HOWL_FRAME_COUNT,
            max(1, int(SPRITE_HEIGHT * HOWL_SCALE)),
        )
        if not self.howl_frames:
            self.howl_frames = [self.stop_frames[-1]]

        # Üvöltés hang: elsődlegesen assets/uvolt/wolf_howl.wav, de elfogadjuk
        # az assets/wolf_howl.wav helyet is, hogy fejlesztés közben rugalmas legyen.
        self.howl_sound: pygame.mixer.Sound | None = None
        self.howl_sound_channel: pygame.mixer.Channel | None = None
        howl_sound_candidates = [
            howl_folder / HOWL_SOUND_FILENAME,
            asset_dir / HOWL_SOUND_FILENAME,
        ]
        howl_sound_path = next((path for path in howl_sound_candidates if path.exists()), None)
        if howl_sound_path is not None:
            try:
                if pygame.mixer.get_init() is None:
                    pygame.mixer.init()
                self.howl_sound = pygame.mixer.Sound(str(howl_sound_path))
                self.howl_sound.set_volume(HOWL_SOUND_VOLUME)
            except pygame.error:
                # Hangrendszer nélküli környezetben is fusson tovább a játék.
                self.howl_sound = None

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
        # Új: a játékos próbált-e mozogni ebben a frame-ben (még akkor is, ha
        # az effektív mozgás blokkolva van). Erre figyelünk a thought bubble-höz.
        self.tried_to_move = False

    def stop_howl_sound(self) -> None:
        if self.howl_sound_channel is not None:
            self.howl_sound_channel.stop()
            self.howl_sound_channel = None

    def start_animation(self, state: str) -> None:
        if self.animation_state != state:
            if self.animation_state == "howl" and state != "howl":
                self.stop_howl_sound()
            self.animation_state = state
            self.animation_timer = 0.0

    def start_howl(self) -> None:
        """Egyszer, lassan lefutó üvöltés animáció indítása az A billentyűvel."""
        if self.animation_state == "howl":
            return
        self.vx = 0.0
        self.movement_pressed = False
        self.was_movement_pressed = False
        self.start_animation("howl")
        if self.howl_sound is not None:
            self.howl_sound_channel = self.howl_sound.play()

    def is_howling(self) -> bool:
        return self.animation_state == "howl"

    def set_jump_phase(self, phase: str) -> None:
        if self.jump_phase != phase:
            self.jump_phase = phase
            self.jump_phase_timer = 0.0

    def handle_input(self, dt: float, obstacle_left_edge: float | None,
                     controls_enabled: bool, movement_blocked: bool = False) -> None:
        keys = pygame.key.get_pressed()

        # Az A billentyű az üvöltésé, a vízszintes mozgás pedig csak a nyilakkal történik.
        # Üvöltés közben a farkas helyben marad, amíg az animáció végig nem fut.
        if self.is_howling():
            self.tried_to_move = False
            self.movement_pressed = False
            self.vx = 0.0
            self.jump_pressed_last_frame = False
            return

        raw_left = controls_enabled and keys[pygame.K_LEFT]
        raw_right = controls_enabled and keys[pygame.K_RIGHT]
        raw_jump = controls_enabled and (keys[pygame.K_SPACE] or keys[pygame.K_UP])

        # A "raw" szándék azt jelzi: a játékos PRÓBÁLT mozogni.
        # Ezt a Game használja a thought bubble triggerelésére.
        self.tried_to_move = raw_left or raw_right or raw_jump

        if movement_blocked:
            moving_left = moving_right = jump_pressed = False
        else:
            moving_left, moving_right, jump_pressed = raw_left, raw_right, raw_jump

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

    def update_physics(self, dt: float, floor_y: float | None = None) -> None:
        """Fizika-frissítés. floor_y átadásával egyirányú platformokra is leszállhat.

        Ha floor_y nincs megadva, a régi viselkedés érvényes (csak a fő talajra ugorhat).
        Egyirányú platform: csak felülről áll meg rajta a játékos. Felfelé ugrálva
        átszalad alatta (mert vy<0 esetén nem landolunk), oldalról szabadon
        áthalad (csak a contains_x szerint támogat egy adott x-pozíción).
        Oldalvást leesés: ha a játékos a platform szélétől odébb sétál, az új x
        alatt a floor_y már alacsonyabb (vagy a fő talaj), és kioldjuk az
        on_ground állapotot, így gravitáció érvényre jut.
        """
        target_floor_y = float(self.config.ground_top_y) if floor_y is None else float(floor_y)
        # Ha a játékos a talajon volt, de az új floor_y észrevehetően lentebb van,
        # akkor "lesétált" a platform széléről - ne snap-eljük le, csak hadd zuhanjon.
        if self.on_ground and self.y < target_floor_y - 0.5:
            self.on_ground = False
        if self.on_ground:
            # Apró float-eltérések kompenzálása: pontosan a tetejére igazítjuk.
            if abs(self.y - target_floor_y) > 0.01:
                self.y = target_floor_y
            return
        self.vy = min(MAX_FALL_SPEED, self.vy + GRAVITY * dt)
        new_y = self.y + self.vy * dt
        # Csak akkor landolunk, ha esés közben átléptük a felszínt (vy>0).
        if self.vy > 0 and new_y >= target_floor_y >= self.y - 0.01:
            self.y = target_floor_y
            self.vy = 0.0
            self.on_ground = True
        else:
            self.y = new_y

    def update_animation(self, dt: float) -> None:
        if self.animation_state == "howl":
            self.vx = 0.0
            self.movement_pressed = False
            self.animation_timer += dt
            howl_duration = max(HOWL_DURATION, len(self.howl_frames) * HOWL_FRAME_TIME)
            if self.animation_timer >= howl_duration:
                self.start_animation("idle")
            self.was_movement_pressed = False
            return

        # Az "ülő" állapot fix - nem váltunk át belőle automatikusan,
        # csak külső start_animation hívással lehet kilépni belőle.
        if self.animation_state == "sitting":
            self.was_movement_pressed = False
            return
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
        if self.animation_state == "sitting":
            image = self.sitting_frame
        elif self.animation_state == "howl":
            frame_index = min(int(self.animation_timer / HOWL_FRAME_TIME), len(self.howl_frames) - 1)
            image = self.howl_frames[frame_index]
        elif self.animation_state == "jump":
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

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float = 0.0) -> None:
        # round() használata int() helyett: subpixel-stutter csökkentése.
        # int() truncate-ol, így 0.999-ről 1.001-re átlépéskor 1 px ugrás van;
        # round() szimmetrikus, és a kamera-floathoz konzisztensebb.
        screen_x = round(self.world_x - camera_x)
        screen_y = round(self.y - camera_y)
        height_above_ground = max(0.0, self.config.ground_top_y - self.y)
        shadow_scale = max(0.42, 1.0 - height_above_ground / 270.0)
        shadow_rect = pygame.Rect(0, 0, int(96 * shadow_scale), int(16 * shadow_scale))
        # Az árnyék a TALAJ szintjén marad világkoordinátában - kameraval együtt mozog.
        shadow_y_screen = round(self.config.ground_top_y + 8 - camera_y)
        shadow_rect.center = (screen_x, shadow_y_screen)
        # Ne pazaroljunk rajzolást, ha az árnyék már messze a képernyőn kívül van.
        if -50 <= shadow_y_screen <= screen.get_height() + 50:
            pygame.draw.ellipse(screen, (33, 27, 72), shadow_rect)
        image = self.current_image()
        # Sitting állapotban kis lefelé-tolás: az ülő pozícióban a farkas
        # "fenék-vonala" picit a talaj alá kerül, így vizuálisan tényleg
        # ráül a felszínre, nem lebeg felette.
        sitting_offset = 10 if self.animation_state == "sitting" else 0
        rect = image.get_rect(midbottom=(screen_x, screen_y + sitting_offset))
        screen.blit(image, rect)
