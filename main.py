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

INTRO_TEXT = "Valami azt súgja, meg kell találnom a békémet..."
THORN_TEXT = "Néha csak úgy juthatunk tovább, ha megtaláljuk a legszűkebb járható ösvényt."
BLOCKED_THOUGHT_TEXT = "Valahogy át kellene jutnom..."
BUSH_COLLAPSE_TEXT = "Egy apróságon múlt az egész."
LAKE_TEXT = "Hinnünk kell magunkban..."
LAKE_SOLVED_TEXT = "... és nem lesznek akadályok."
WINDOW_TITLE = "Farkas kaland"

OBSTACLE_CAMERA_REVEAL_SPEED = 230.0
OBSTACLE_CAMERA_REVEAL_EPSILON = 1.0

WEAK_SPOT_RADIUS = 2  # 2 px sugár a hit-detectionhez (kihívásnak szánt)
WEAK_SPOT_MIN_ALPHA = 110  # csak elég látható pixel lehet weak spot
WEAK_SPOT_MARKER_COLOR = (220, 30, 30, 255)  # 2x2 piros marker a bozóton
BUSH_COLLAPSE_RATE = 1.4  # 1/sec - kb. 0.7s teljes összeomlás
THOUGHT_BUBBLE_FADE_SPEED = 5.0
THOUGHT_BUBBLE_VISIBLE_TIME = 1.6

LAKE_HOLD_DURATION = 5.0  # másodperc - meddig kell csökönyösen jobbra nyomni
LAKE_HOLD_DECAY = 2.0  # gyors visszaesés ha elengedik
LAKE_WORLD_X = 5500
LAKE_BLOCK_EPSILON = 0.5  # float-pontosság a "blokkolva van" detektáláshoz

LOG_CHALLENGE_WORLD_X = 7400  # harmadik kihívás triggerpontja, a tó után
LOG_WARNING_TEXT = "Veszélyt érzek!"
GAME_OVER_TEXT = "Játék vége! A farönk elsodort."
LOG_SPEED = 390.0
LOG_RADIUS_BASE = 44
LOG_COLLISION_PADDING_X = 10
LOG_SAFE_CLEARANCE_EXTRA = 16
# A harmadik kihívás nézetváltása lassan, finoman közelítse a farkast középre.
# Kisebb érték = lassabb/selymesebb átmenet.
LOG_CAMERA_CENTER_SMOOTHNESS = 2.6
LOG_CAMERA_CENTER_EPSILON = 0.75

DARK_CHALLENGE_WORLD_X = 8350  # negyedik kihívás triggerpontja, a farönk után
DARKNESS_HINT_TEXT = "E jelben győzni fogsz"
DARKNESS_MAX_ALPHA = 255
DARKNESS_FADE_IN_SPEED = 320.0
DARKNESS_FADE_OUT_SPEED = 430.0
SPOTLIGHT_RADIUS_BASE = 46
CROSS_GESTURE_MIN_SPAN_BASE = 145
CROSS_GESTURE_TOLERANCE_BASE = 18
CROSS_GESTURE_MIN_POINTS = 18

# Ötödik kihívás: sziklacsúcs platform-ugrálással.
PEAK_CHALLENGE_WORLD_X = 9700  # ötödik kihívás triggerpontja, a sötétség után
PEAK_BASE_OFFSET_X = 420  # mennyivel jobbra az első kocka a triggertől (sétáltatós átmenet)
PEAK_INTRO_TEXT = "Fel kell jutnom a csúcsra, hogy lássam a csillagokat."
PEAK_SUCCESS_TEXT = "Mostmár tisztán látom a csillagokat."
PEAK_BLOCKED_HINT_TEXT = "Csak a csúcs felé vezet az út..."
PEAK_BLOCK_WIDTH_BASE = 110  # alap kocka-szélesség (keskeny - skálázódik)
PEAK_BLOCK_HEIGHT_BASE = 26
PEAK_SUMMIT_DETECT_TOLERANCE = 1.6  # mennyire kell pontosan a csúcs tetején állni
PEAK_CLIMB_SCREENS = 4.2  # ennyi képernyőnyit kell felfelé ugrálni
PEAK_VERTICAL_CAMERA_BIAS = 0.62  # a kamera a játékost ennyi magasra tartja a képernyőn (0=fent, 1=lent)
PEAK_VERTICAL_DEADZONE = 0.32  # ekkora "deadzone" a talaj feletti relatív magasság, amíg nem indul scroll

# Hatodik (és záró) jelenet a csúcson: a farkas leül és felidézi a Göncöl szekér csillagképet,
# amit a játékosnak le kell rajzolnia.
SITTING_FRAME_FILENAME = "ulelorenez.png"  # opcionális assets fájl - ha nincs, fallback frame
CONSTELLATION_INTRO_TEXT = "Emlékszem egy csillagképre, egy szekérről..."
CONSTELLATION_COMPLETE_TEXT = "Pont olyan, amilyennek emlékeztem rá."
CONSTELLATION_STAR_HIT_TOLERANCE_BASE = 48  # kb. ekkora sugárban kell áthúzni a csillagot
CONSTELLATION_LINE_WIDTH_BASE = 3

MAX_FRAME_DT = 0.05  # frame-spike clamp, hogy ne ugorjon a játék


class WorldConfig:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.left_frame_x = max(55, int(width * 0.075))
        # Jobbra haladásnál korábban kezdjen tolódni a pálya, hogy több tér
        # látszódjon a farkas előtt. Régebben 0.82 volt, emiatt a kamera csak
        # akkor indult, amikor a játékos már túl közel volt a képernyő jobb széléhez.
        self.right_edge_x = int(width * 0.64)
        # Magasabb érték -> kisebb steady-state lemaradás a játékos mögött.
        # 9.0 esetén lag = v_player / 9.0 = 300/9 ≈ 33 px (4.8-nál még 62 px volt).
        self.camera_smoothness = 9.0
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
        # Az "égbolt-folytatás" a sziklacsúcs jelenethez: amikor a kamera felfelé
        # mozdul, a háttérkép is lecsúszik, és felül egy hézag keletkezik. Ezt
        # egy magas, csillagos, lilás-fekete gradient tölti ki, ami pontosan a
        # háttér felső pixelsorához illeszkedik (mintavételezés alapján), így
        # a varrat észrevétlen.
        ext_height = max(3500, int(self.config.height * 5.0))
        self.sky_extension = self._build_sky_extension(ext_height)

    def _load_background(self) -> pygame.Surface:
        candidates = [
            Path(__file__).parent / "assets" / "hatter.png",
            Path(__file__).parent / "assets" / "intro_background.png",
            Path("/mnt/data/assets/hatter.png"),
            Path("/mnt/data/ghostwriter_images/context/cfad7fbc-a0c5-59f7-9bef-e2c6a91c52f1.png"),
        ]
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

    def _build_sky_extension(self, height: int) -> pygame.Surface:
        """Csillagos, lilás-fekete gradient, amit a háttérkép FÖLÉ rajzolunk
        amikor a kamera felfelé mozog (sziklacsúcs jelenet).

        A felület alja pontosan a háttér legfelső pixelsorának ÁTLAGOLT színét
        tükrözi, így varrat-mentes az átmenet. Felfelé fokozatosan a sötét éjszaka
        színhez (mély lila-fekete) olvad át, sűrűsödő csillag-mezővel.
        """
        bg_w = self.background.get_width()
        # NO-alpha felület: gyors, minden pixel átlátszatlan, és a screen.blit()
        # tisztán RGB-másolást csinál - nincs alfa-blendelési bonyodalom.
        surf = pygame.Surface((bg_w, height))

        # Háttér felső sorának mintavételezése (átlag) - ehhez illesztjük az alsó színt
        samples: list[tuple[int, int, int]] = []
        for i in range(20):
            sx = int(i * (bg_w - 1) / 19)
            r, g, b = self.background.get_at((sx, 0))[:3]
            samples.append((r, g, b))
        bot_r = sum(s[0] for s in samples) // len(samples)
        bot_g = sum(s[1] for s in samples) // len(samples)
        bot_b = sum(s[2] for s in samples) // len(samples)
        bottom_color = pygame.Color(bot_r, bot_g, bot_b)
        # Felül: nagyon mély éjszaka, kissé lilás árnyalattal (hogy ne legyen "halott" fekete)
        top_color = pygame.Color(5, 7, 26)

        # Vertikális gradient. Power-curve: az alsó harmadban gyorsan a háttér
        # színéhez közeledik, a felső kétharmadban lassan sötétedik el.
        for y in range(height):
            t = y / max(1, height - 1)
            eased = t ** 0.85
            color = top_color.lerp(bottom_color, eased)
            pygame.draw.line(surf, color, (0, y), (bg_w, y))

        # Csillagok: a "fényesség"-et a SZÍN intenzitásával állítjuk, nem alfával
        # (no-alpha felület van). Halvány csillag = sötétebb szín, közelebb a
        # gradient-hez; fényes csillag = majdnem fehér.
        rng = random.Random(31415)
        area = bg_w * height
        star_count = max(160, area // 4500)
        for _ in range(star_count):
            x = rng.randint(0, bg_w - 1)
            # Kissé bias a magasabb területekre, de mindenhol vannak
            y = int((rng.random() ** 0.85) * (height - 4))
            height_factor = 1.0 - (y / max(1, height))  # 0=alul, 1=felül
            roll = rng.random()
            big_chance = 0.07 + height_factor * 0.07
            med_chance = 0.42 + height_factor * 0.15
            if roll < big_chance:
                radius = 3
                shade = rng.randint(225, 255)
            elif roll < med_chance:
                radius = 2
                shade = rng.randint(170, 225)
            else:
                radius = 1
                shade = rng.randint(115, 175)
            # Enyhe kék/lila árnyalat - holdfényes éjszaka érzet
            color = (shade, shade, min(255, shade + 18))
            pygame.draw.circle(surf, color, (x, y), radius)

        # Csillagcsoportok (galaxis-szerű sűrűsödések) - a felső 60%-ban néhány
        # helyen sűrűbb csillagmezőket teszünk, ami élővé és változatossá teszi
        # az eget. Nem kör, nem felhő - csak több csillag egy körzetben.
        for _ in range(max(4, height // 600)):
            cluster_cx = rng.randint(int(bg_w * 0.05), int(bg_w * 0.95))
            cluster_cy = rng.randint(int(height * 0.04), int(height * 0.55))
            cluster_r = rng.randint(int(bg_w * 0.05), int(bg_w * 0.11))
            cluster_count = rng.randint(20, 38)
            for _ in range(cluster_count):
                # Gauss-szerű eloszlás a középpont körül
                ox = int((rng.random() + rng.random() - 1) * cluster_r)
                oy = int((rng.random() + rng.random() - 1) * cluster_r * 0.7)
                cx_pt = cluster_cx + ox
                cy_pt = cluster_cy + oy
                if 0 <= cx_pt < bg_w and 0 <= cy_pt < height:
                    cs = rng.randint(155, 230)
                    cr = 1 if rng.random() > 0.18 else 2
                    pygame.draw.circle(surf, (cs, cs, min(255, cs + 18)),
                                       (cx_pt, cy_pt), cr)

        return surf

    def draw_sky(self, screen: pygame.Surface, camera_y: float = 0.0) -> None:
        # A háttérkép a sziklacsúcs jelenetben TALAJSZINTHEZ van rögzítve világtérben,
        # tehát ahogy a kamera felfelé úszik, a kép is "lejjebb" csúszik a képernyőn.
        bg_y = round(-camera_y)
        # Ha a kamera felfelé mozdult (camera_y < 0), a háttér felett egy üres rész
        # marad - ezt tölti ki a sky_extension.
        if camera_y < -0.5:
            ext_h = self.sky_extension.get_height()
            ext_y = bg_y - ext_h
            # Csak akkor blittolunk, ha az extension legalább részben látható
            if ext_y < self.config.height and ext_y + ext_h > 0:
                screen.blit(self.sky_extension, (0, ext_y))
            else:
                # A camera_y olyan magas, hogy az extension is teljesen kicsúszott
                # - ekkor a teljes képernyő legyen sötét lila/fekete (legrosszabb eset).
                screen.fill((5, 7, 26))
        screen.blit(self.background, (0, bg_y))

    def draw_ground(self, screen: pygame.Surface, camera_x: float, camera_y: float = 0.0) -> None:
        tile_width = self.ground_tile.get_width()
        start_x = -int(camera_x % tile_width) - tile_width
        y = self.config.ground_top_y - 2 - camera_y
        # Ha a talaj-csík teljesen kívül van a képernyőn (magasan járunk), ne is rajzoljuk.
        if y > self.config.height + 10 or y + self.ground_tile.get_height() < -10:
            return
        for x in range(start_x, self.config.width + tile_width, tile_width):
            screen.blit(self.ground_tile, (x, y))


class DialogueBox:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.active = False
        self.text = ""
        self.hint_text = "Enter - tovább"
        self.font = pygame.font.SysFont("arial", max(26, int(config.height * 0.036)))
        self.hint_font = pygame.font.SysFont("arial", max(18, int(config.height * 0.024)))

    def show(self, text: str, hint_text: str = "Enter - tovább") -> None:
        self.text = text
        self.hint_text = hint_text
        self.active = True

    def hide(self) -> None:
        self.active = False
        self.hint_text = "Enter - tovább"

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        box_width = int(self.config.width * 0.54)
        padding_x = int(self.config.width * 0.025)
        padding_y = int(self.config.height * 0.026)
        line_spacing = max(8, int(self.config.height * 0.012))
        lines = wrap_text(self.text, self.font, box_width - padding_x * 2)
        rendered = [self.font.render(line, True, (234, 235, 255)) for line in lines]
        hint = self.hint_font.render(self.hint_text, True, (176, 198, 245))
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


class ThoughtBubble:
    """Lebegő gondolatfelhő a játékos feje fölött, fade-in/fade-out animációval."""

    def __init__(self, config: WorldConfig, text: str = BLOCKED_THOUGHT_TEXT) -> None:
        self.config = config
        self.text = text
        self.font = pygame.font.SysFont("arial", max(20, int(config.height * 0.026)), italic=True)
        self.alpha = 0.0
        self.target_alpha = 0.0
        self.visible_timer = 0.0
        self._cached_bubble: pygame.Surface | None = None
        self._build_bubble()

    def _build_bubble(self) -> None:
        text_surf = self.font.render(self.text, True, (28, 30, 78))
        padding_x, padding_y = 22, 14
        bubble_w = text_surf.get_width() + padding_x * 2
        bubble_h = text_surf.get_height() + padding_y * 2
        # Bal padding: hely a tail-felhőcskéknek, hogy a buborék MAGA jobbra
        # legyen az anchor ponttól, és csak a tail nyúljon balra a farkas felé.
        left_pad = 30
        bottom_pad = 56
        surf_w = bubble_w + left_pad
        surf_h = bubble_h + bottom_pad
        surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        fill = (245, 248, 255)
        border = (140, 152, 210)
        # Fő buborék: az x=left_pad-tól indul, így az ANCHOR ponttól jobbra van.
        bubble_x = left_pad
        # Tail: a buborék bal-alsó sarkából INDUL és LEFELÉ-BALRA tart, belóg
        # a left_pad területbe. Így vizuálisan visszamutat a farkas feje felé.
        for cx_off, cy_off, r in [(20, bubble_h + 8, 11), (2, bubble_h + 22, 7), (-14, bubble_h + 36, 4)]:
            cx = bubble_x + cx_off
            pygame.draw.circle(surf, border, (cx, cy_off), r)
            pygame.draw.circle(surf, fill, (cx, cy_off), r - 2)
        # Fő buborék
        pygame.draw.rect(surf, fill, (bubble_x, 0, bubble_w, bubble_h), border_radius=20)
        pygame.draw.rect(surf, border, (bubble_x, 0, bubble_w, bubble_h), 2, border_radius=20)
        surf.blit(text_surf, (bubble_x + padding_x, padding_y))
        self._cached_bubble = surf

    def show(self, text: str | None = None) -> None:
        """A megjelenítés "kérése" - minden hívás újraindítja a látható időt.

        A harmadik kihívás ugyanazt a buborék-komponenst használja, csak más
        szöveggel, ezért opcionálisan átépítjük a cache-elt buborékot.
        """
        if text is not None and text != self.text:
            self.text = text
            self._build_bubble()
        self.target_alpha = 1.0
        self.visible_timer = THOUGHT_BUBBLE_VISIBLE_TIME

    def hide_immediately(self) -> None:
        self.alpha = 0.0
        self.target_alpha = 0.0
        self.visible_timer = 0.0

    def update(self, dt: float) -> None:
        if self.visible_timer > 0:
            self.visible_timer -= dt
            if self.visible_timer <= 0:
                self.target_alpha = 0.0
        diff = self.target_alpha - self.alpha
        step = THOUGHT_BUBBLE_FADE_SPEED * dt
        if abs(diff) <= step:
            self.alpha = self.target_alpha
        else:
            self.alpha += step if diff > 0 else -step

    def draw(self, screen: pygame.Surface, anchor_screen_pos: tuple[int, int]) -> None:
        if self.alpha <= 0.01 or self._cached_bubble is None:
            return
        bubble = self._cached_bubble
        bubble.set_alpha(int(255 * self.alpha))
        # bottomleft anchor: a surface bal-alsó sarka az anchor ponton.
        # A buborék maga jobbra van (left_pad miatt), a tail balra-felfelé
        # mutat vissza a farkas feje felé. Bal oldalon NEM lóg ki túl a szegélyen.
        bubble_rect = bubble.get_rect(bottomleft=anchor_screen_pos)
        screen.blit(bubble, bubble_rect)


class IntroMenuScreen:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.options = ["Játék indítása", "Névjegy", "Kilépés"]
        self.selected_index = 0
        self.menu_scale = 0.78  # A főmenü bal oldali paneljének és szövegeinek arányos kicsinyítése.
        self.menu_title_font = pygame.font.SysFont("georgia", max(42, int(config.height * 0.085 * self.menu_scale)), bold=True)
        self.menu_subtitle_font = pygame.font.SysFont("arial", max(19, int(config.height * 0.038 * self.menu_scale)), italic=True)
        self.menu_option_font = pygame.font.SysFont("arial", max(22, int(config.height * 0.043 * self.menu_scale)), bold=True)
        self.menu_small_font = pygame.font.SysFont("arial", max(14, int(config.height * 0.024 * self.menu_scale)))
        self.title_font = pygame.font.SysFont("georgia", max(54, int(config.height * 0.085)), bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", max(24, int(config.height * 0.038)), italic=True)
        self.option_font = pygame.font.SysFont("arial", max(28, int(config.height * 0.043)), bold=True)
        self.body_font = pygame.font.SysFont("arial", max(22, int(config.height * 0.031)))
        self.small_font = pygame.font.SysFont("arial", max(16, int(config.height * 0.024)))
        self.quote_font = pygame.font.SysFont("arial", max(20, int(config.height * 0.025)), italic=True)
        self.option_rects: list[pygame.Rect] = []
        self.background = self._load_background()
        self.wolf_art = self._load_wolf_art()

    def _load_background(self) -> pygame.Surface:
        candidates = [
            Path(__file__).parent / "assets" / "intro_background.png",
            Path(__file__).parent / "assets" / "hatter.png",
            Path("/mnt/data/ghostwriter_images/context/cfad7fbc-a0c5-59f7-9bef-e2c6a91c52f1.png"),
        ]
        source = next((path for path in candidates if path.exists()), None)
        if source is not None:
            image = pygame.image.load(str(source)).convert()
            return pygame.transform.smoothscale(image, (self.config.width, self.config.height))

        fallback = pygame.Surface((self.config.width, self.config.height))
        top = pygame.Color(8, 16, 78)
        middle = pygame.Color(78, 45, 183)
        bottom = pygame.Color(233, 131, 185)
        for y in range(self.config.height):
            t = y / max(1, self.config.height - 1)
            if t < 0.62:
                color = top.lerp(middle, t / 0.62)
            else:
                color = middle.lerp(bottom, (t - 0.62) / 0.38)
            pygame.draw.line(fallback, color, (0, y), (self.config.width, y))
        moon_center = (int(self.config.width * 0.18), int(self.config.height * 0.18))
        pygame.draw.circle(fallback, (250, 236, 206), moon_center, max(38, int(self.config.height * 0.06)))
        pygame.draw.circle(fallback, (35, 41, 126), (moon_center[0] + 18, moon_center[1] - 2), max(34, int(self.config.height * 0.052)))
        rng = random.Random(77)
        for _ in range(140):
            x = rng.randint(0, self.config.width - 1)
            y = rng.randint(0, int(self.config.height * 0.58))
            radius = rng.randint(1, 2)
            shade = rng.randint(220, 255)
            pygame.draw.circle(fallback, (shade, shade, 255), (x, y), radius)
        return fallback

    def _load_wolf_art(self) -> pygame.Surface | None:
        candidates = [
            Path(__file__).parent / "assets" / "menu_wolf.png",
            Path("/mnt/data/ghostwriter_images/context/956dca34-f53d-5e3a-af9c-824288cfb066.png"),
        ]
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            return None
        try:
            image = pygame.image.load(str(source)).convert_alpha()
            target_h = max(140, int(self.config.height * 0.24))
            scale = target_h / max(1, image.get_height())
            target_w = max(1, int(image.get_width() * scale))
            return pygame.transform.smoothscale(image, (target_w, target_h))
        except Exception:
            return None

    def move_selection(self, delta: int) -> None:
        self.selected_index = (self.selected_index + delta) % len(self.options)

    def option_at(self, pos: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self.option_rects):
            if rect.collidepoint(pos):
                return index
        return None

    def draw_menu(self, screen: pygame.Surface) -> None:
        screen.blit(self.background, (0, 0))
        overlay = pygame.Surface((self.config.width, self.config.height), pygame.SRCALPHA)
        overlay.fill((5, 8, 26, 106))
        screen.blit(overlay, (0, 0))

        menu_scale = self.menu_scale
        panel_w = int(self.config.width * 0.44)
        panel_h = int(self.config.height * 0.42)
        panel_rect = pygame.Rect(int(self.config.width * 0.08), int(self.config.height * 0.20), panel_w, panel_h)
        corner_radius = max(18, int(28 * menu_scale))

        panel_shadow = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_shadow, (0, 0, 0, 95), panel_shadow.get_rect(), border_radius=corner_radius)
        screen.blit(panel_shadow, panel_rect.move(0, max(6, int(10 * menu_scale))).topleft)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (11, 15, 41, 188), panel.get_rect(), border_radius=corner_radius)
        pygame.draw.rect(panel, (129, 151, 239, 225), panel.get_rect(), 2, border_radius=corner_radius)
        screen.blit(panel, panel_rect.topleft)

        pad_x = max(22, int(34 * menu_scale))
        title = self.menu_title_font.render(WINDOW_TITLE, True, (241, 239, 255))
        subtitle = self.menu_subtitle_font.render("Holdfényes utazás egy csendes, meseszerű világban.", True, (201, 208, 255))
        screen.blit(title, (panel_rect.x + pad_x, panel_rect.y + max(20, int(28 * menu_scale))))
        screen.blit(subtitle, (panel_rect.x + pad_x, panel_rect.y + max(82, int(108 * menu_scale))))

        self.option_rects = []
        start_y = panel_rect.y + max(126, int(170 * menu_scale))
        box_h = max(42, int(self.config.height * 0.08 * menu_scale))
        box_gap = max(12, int(18 * menu_scale))
        option_pad_x = max(22, int(30 * menu_scale))
        option_radius = max(13, int(18 * menu_scale))
        for index, option in enumerate(self.options):
            rect = pygame.Rect(panel_rect.x + option_pad_x, start_y + index * (box_h + box_gap), panel_rect.width - option_pad_x * 2, box_h)
            self.option_rects.append(rect)
            selected = index == self.selected_index
            box = pygame.Surface(rect.size, pygame.SRCALPHA)
            fill = (137, 112, 232, 210) if selected else (29, 38, 89, 170)
            border = (238, 228, 255, 240) if selected else (120, 139, 219, 210)
            pygame.draw.rect(box, fill, box.get_rect(), border_radius=option_radius)
            pygame.draw.rect(box, border, box.get_rect(), 2, border_radius=option_radius)
            screen.blit(box, rect.topleft)
            label = self.menu_option_font.render(option, True, (255, 248, 255) if selected else (224, 231, 255))
            label_rect = label.get_rect(center=rect.center)
            screen.blit(label, label_rect)

        hint_text = "↑/↓ vagy W/S: választás • Enter: elfogadás • Egér: kattintás"
        hint_lines = wrap_text(hint_text, self.menu_small_font, panel_rect.width - pad_x * 2)
        hint_surfaces = [self.menu_small_font.render(line, True, (220, 227, 255)) for line in hint_lines]
        hint_line_gap = max(3, int(5 * menu_scale))
        hint_w = max(surface.get_width() for surface in hint_surfaces)
        hint_h = sum(surface.get_height() for surface in hint_surfaces) + max(0, len(hint_surfaces) - 1) * hint_line_gap
        hint_pad_x = max(8, int(10 * menu_scale))
        hint_pad_y = max(5, int(6 * menu_scale))
        hint_bg = pygame.Surface((hint_w + hint_pad_x * 2, hint_h + hint_pad_y * 2), pygame.SRCALPHA)
        pygame.draw.rect(hint_bg, (7, 12, 34, 125), hint_bg.get_rect(), border_radius=max(12, int(16 * menu_scale)))
        hint_pos = (panel_rect.x + pad_x - hint_pad_x, panel_rect.bottom + max(4, int(5 * menu_scale)))
        screen.blit(hint_bg, hint_pos)
        hint_y = hint_pos[1] + hint_pad_y
        for surface in hint_surfaces:
            screen.blit(surface, (hint_pos[0] + hint_pad_x, hint_y))
            hint_y += surface.get_height() + hint_line_gap

        moon_quote = self.menu_small_font.render("„Valami azt súgja, meg kell találnom a békémet...”", True, (238, 228, 255))
        moon_quote = self.quote_font.render(INTRO_TEXT, True, (238, 228, 255))
        moon_quote_rect = moon_quote.get_rect(
          bottomleft=(int(self.config.width * 0.09), self.config.height - 36)
        )       
        screen.blit(moon_quote, moon_quote_rect)

        if self.wolf_art is not None:
            wolf = self.wolf_art.copy()
            wolf.set_alpha(244)
            wolf_rect = wolf.get_rect(bottomright=(self.config.width - 86, self.config.height - 76))
            glow_rect = wolf_rect.inflate(70, 52)
            glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (138, 98, 238, 70), glow.get_rect())
            screen.blit(glow, glow_rect.topleft)
            screen.blit(wolf, wolf_rect)

    def draw_about(self, screen: pygame.Surface, music_enabled: bool, music_available: bool, music_path_found: bool) -> None:
        screen.blit(self.background, (0, 0))
        dim = pygame.Surface((self.config.width, self.config.height), pygame.SRCALPHA)
        dim.fill((2, 5, 18, 152))
        screen.blit(dim, (0, 0))

        panel_rect = pygame.Rect(0, 0, int(self.config.width * 0.62), int(self.config.height * 0.64))
        panel_rect.center = (self.config.width // 2, self.config.height // 2)
        shadow = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 105), shadow.get_rect(), border_radius=28)
        screen.blit(shadow, panel_rect.move(0, 10).topleft)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (11, 16, 42, 218), panel.get_rect(), border_radius=28)
        pygame.draw.rect(panel, (130, 154, 240, 230), panel.get_rect(), 2, border_radius=28)
        screen.blit(panel, panel_rect.topleft)

        title = self.title_font.render("Névjegy", True, (245, 243, 255))
        screen.blit(title, (panel_rect.x + 34, panel_rect.y + 26))

        music_text = "bekapcsolva" if music_enabled else "kikapcsolva"
        availability_text = "rendben betöltve" if music_available else ("a dallam.wav hiányzik" if not music_path_found else "hangrendszer nem elérhető")
        paragraphs = [
            "Ez a játék egy holdfényes, mesés hangulatú 2D oldalnézetes kaland.",
            "A főmenüből elindítható a játék, megnyitható ez a névjegy, vagy kiléphetsz.",
            "Irányítás játék közben: A/D vagy nyilak a mozgáshoz, Space/W/Fel az ugráshoz, Enter az üzenetek bezárásához.",
            f"Zene: M billentyűvel kapcsolható ki vagy be. Jelenleg: {music_text}; állapot: {availability_text}.",
            "A dallam végtelenítve szól, ha az assets könyvtárban megtalálható a dallam.wav fájl.",
        ]
        max_width = panel_rect.width - 70
        y = panel_rect.y + 108
        for paragraph in paragraphs:
            for line in wrap_text(paragraph, self.body_font, max_width):
                rendered = self.body_font.render(line, True, (228, 234, 255))
                screen.blit(rendered, (panel_rect.x + 36, y))
                y += rendered.get_height() + 8
            y += 10

        footer = self.small_font.render("Esc / Backspace / Enter - vissza a főmenübe", True, (200, 211, 255))
        screen.blit(footer, (panel_rect.x + 36, panel_rect.bottom - 48))


class ThornBush:
    def __init__(self, world_x: float, ground_y: int, scale: float = 1.0) -> None:
        self.world_x = world_x
        self.ground_y = ground_y
        self.trigger_distance = 460
        self.stop_distance = 420
        self.surface = self._create_surface(scale)
        self.collapsed = False
        self.collapse_progress = 0.0
        # A weak spot véletlen, minden játékindításkor más helyen van.
        # Determinisztikus seed nélkül választjuk!
        self.weak_spot_local: tuple[int, int] | None = self._choose_weak_spot()

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

    def _choose_weak_spot(self) -> tuple[int, int] | None:
        """Random pixel a bozót látható területén belül, ami a hatékony találati pont.
        Egyúttal felfest egy 2x2 piros markert ezen a helyen, hogy a játékos LÁSSA."""
        rng = random.Random()  # nem deterministic - minden játékindításnál más
        width, height = self.surface.get_size()
        candidates: list[tuple[int, int]] = []
        # Egyszer lock-olunk és sok mintát veszünk - sokkal gyorsabb mint frame-enként.
        self.surface.lock()
        try:
            for _ in range(800):
                x = rng.randint(int(width * 0.18), int(width * 0.82))
                y = rng.randint(int(height * 0.30), int(height * 0.85))
                if self.surface.get_at((x, y))[3] >= WEAK_SPOT_MIN_ALPHA:
                    candidates.append((x, y))
                    if len(candidates) >= 40:
                        break
        finally:
            self.surface.unlock()
        if not candidates:
            spot = (width // 2, int(height * 0.6))
        else:
            spot = rng.choice(candidates)
        # 2x2 piros marker rákerül a bozót textúrájára - ez a vizuális hint.
        self._paint_weak_spot_marker(spot)
        return spot

    def _paint_weak_spot_marker(self, pos: tuple[int, int]) -> None:
        x, y = pos
        width, height = self.surface.get_size()
        self.surface.lock()
        try:
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                px, py = x + dx, y + dy
                if 0 <= px < width and 0 <= py < height:
                    self.surface.set_at((px, py), WEAK_SPOT_MARKER_COLOR)
        finally:
            self.surface.unlock()

    @property
    def left_edge(self) -> float:
        return self.world_x

    def trigger_x(self) -> float:
        return self.left_edge - self.trigger_distance

    def weak_spot_world_pos(self) -> tuple[float, float] | None:
        """A weak spot világkoordinátái (a 2x2 marker GEOMETRIAI KÖZEPE)."""
        if self.weak_spot_local is None:
            return None
        sx, sy = self.weak_spot_local
        height = self.surface.get_height()
        # +0.5 offset: a 2x2 marker pixelei (sx,sy)..(sx+1,sy+1), közepe (sx+0.5, sy+0.5).
        wx = self.world_x + sx + 0.5
        wy = self.ground_y + 18 - height + sy + 0.5
        return (wx, wy)

    def is_weak_spot_hit(self, world_x: float, world_y: float, radius: float = WEAK_SPOT_RADIUS) -> bool:
        if self.collapsed:
            return False
        spot = self.weak_spot_world_pos()
        if spot is None:
            return False
        dx = world_x - spot[0]
        dy = world_y - spot[1]
        return dx * dx + dy * dy <= radius * radius

    def collapse(self) -> None:
        if self.collapsed:
            return
        self.collapsed = True
        self.collapse_progress = 0.0

    def update(self, dt: float) -> None:
        if self.collapsed and self.collapse_progress < 1.0:
            self.collapse_progress = min(1.0, self.collapse_progress + BUSH_COLLAPSE_RATE * dt)

    def is_visually_gone(self) -> bool:
        return self.collapsed and self.collapse_progress >= 1.0

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        if self.is_visually_gone():
            return
        screen_x = round(self.world_x - camera_x)
        rect = self.surface.get_rect(bottomleft=(screen_x, self.ground_y + 18))
        if self.collapse_progress > 0:
            t = self.collapse_progress
            # Összeesik (függőleges scale csökken) + halványul + kicsit szétterül.
            alpha = max(0, int(255 * (1.0 - t)))
            scale_y = max(0.05, 1.0 - t * 0.85)
            scale_x = 1.0 + t * 0.06
            new_w = max(1, int(self.surface.get_width() * scale_x))
            new_h = max(1, int(self.surface.get_height() * scale_y))
            scaled = pygame.transform.smoothscale(self.surface, (new_w, new_h))
            scaled.set_alpha(alpha)
            scaled_rect = scaled.get_rect(midbottom=rect.midbottom)
            screen.blit(scaled, scaled_rect)
        else:
            screen.blit(self.surface, rect)


class Lake:
    """Második akadály: víz, amit csak kitartással lehet átlépni."""

    def __init__(self, world_x: float, ground_y: int, screen_height: int, scale: float = 1.0) -> None:
        self.world_x = world_x
        self.ground_y = ground_y
        self.screen_height = screen_height
        self.trigger_distance = 460
        self.stop_distance = 280
        self.solved = False
        self.water_anim_t = 0.0
        self.scale = scale
        self.width = int(620 * scale)
        # A tó a ground_top_y-tól lefelé tart, a képernyő aljáig kitölti
        # a látható területet (és kicsit túl is, hogy ne legyen rés).
        self.height = max(80, screen_height - ground_y + 24)
        self.surface = self._build_water_surface()

    def _build_water_surface(self) -> pygame.Surface:
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Vertikális gradient: világosabb teal felül, sötét indigo lefelé.
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            r = int(34 + (10 - 34) * t)
            g = int(108 + (24 - 108) * t)
            b = int(140 + (62 - 140) * t)
            pygame.draw.line(s, (r, g, b, 255), (0, y), (self.width, y))
        # "Belesütött" csillanások: statikus, a felső 35%-ban.
        rng = random.Random(513)
        for _ in range(50):
            x = rng.randint(8, self.width - 8)
            y = rng.randint(2, int(self.height * 0.35))
            length = rng.randint(8, 26)
            shade = rng.randint(180, 235)
            pygame.draw.line(s, (shade, min(255, shade + 12), 255), (x, y), (x + length, y), 1)
        # Felső szegély - egy halvány, fehéres "vízszint" csík.
        pygame.draw.line(s, (200, 230, 255, 180), (0, 1), (self.width, 1), 2)
        return s

    @property
    def left_edge(self) -> float:
        return self.world_x

    @property
    def right_edge(self) -> float:
        return self.world_x + self.width

    def trigger_x(self) -> float:
        return self.left_edge - self.trigger_distance

    def is_blocking(self) -> bool:
        return not self.solved

    def solve(self) -> None:
        self.solved = True

    def update(self, dt: float) -> None:
        self.water_anim_t += dt

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        screen_x = round(self.world_x - camera_x)
        rect = self.surface.get_rect(topleft=(screen_x, self.ground_y))
        screen.blit(self.surface, rect)
        # Mozgó hullámvonalak előtér-rétegben - egyszerű, opaque vonalak.
        # (Az alfa-csatornás vonalrajzolás közvetlenül a screen-re nem működik
        # alpha-betartással, ezért fix világos színt használunk.)
        for i in range(12):
            phase = (self.water_anim_t * 0.5 + i * 0.27) % 1.0
            x = screen_x + int(self.width * phase)
            y = self.ground_y + 5 + (i % 5) * 4
            shade_t = 1.0 - phase
            shade = int(140 + 95 * shade_t)
            length = 16 + int(shade_t * 8)
            pygame.draw.line(screen, (shade, min(255, shade + 30), 255), (x, y), (x + length, y), 1)


class WillpowerIndicator:
    """Vízszintes haladó-sáv a tó akadály visszajelzésére (csökönyösen nyomod-e)."""

    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.progress = 0.0
        self.alpha = 0.0
        self.bar_width = max(80, int(config.height * 0.10))
        self.bar_height = 6

    def update(self, target_progress: float, dt: float) -> None:
        # A megjelenített progressz simán követi a tényleges hold_timer arányát.
        diff = target_progress - self.progress
        progress_speed = 6.0
        if abs(diff) <= progress_speed * dt:
            self.progress = target_progress
        else:
            self.progress += progress_speed * dt if diff > 0 else -progress_speed * dt
        self.progress = max(0.0, min(1.0, self.progress))
        # Alpha: csak akkor látszik, ha aktív a holdolás.
        target_alpha = 1.0 if target_progress > 0.005 else 0.0
        diff_a = target_alpha - self.alpha
        step = 4.0 * dt
        if abs(diff_a) <= step:
            self.alpha = target_alpha
        else:
            self.alpha += step if diff_a > 0 else -step
        self.alpha = max(0.0, min(1.0, self.alpha))

    def reset(self) -> None:
        self.progress = 0.0
        self.alpha = 0.0

    def draw(self, screen: pygame.Surface, anchor_pos: tuple[int, int]) -> None:
        if self.alpha <= 0.01:
            return
        cx, cy = anchor_pos
        w = self.bar_width
        h = self.bar_height
        bar = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        # Háttér
        pygame.draw.rect(bar, (10, 20, 50, int(180 * self.alpha)),
                         bar.get_rect(), border_radius=h)
        # Telt rész
        fill_w = int(w * self.progress)
        if fill_w > 0:
            pygame.draw.rect(bar, (140, 220, 255, int(230 * self.alpha)),
                             (2, 2, fill_w, h), border_radius=h)
        # Halvány keret
        pygame.draw.rect(bar, (180, 230, 255, int(120 * self.alpha)),
                         bar.get_rect(), 1, border_radius=h)
        bar_rect = bar.get_rect(center=(cx, cy))
        screen.blit(bar, bar_rect)



class RollingLog:
    """Harmadik akadály: a képernyő jobb széléről beguruló farönk."""

    def __init__(self, ground_y: int, scale: float = 1.0) -> None:
        self.ground_y = ground_y
        self.radius = int(LOG_RADIUS_BASE * scale)
        self.collision_radius = max(18, int(self.radius * 0.82))
        self.speed = LOG_SPEED * max(0.92, min(1.18, scale))
        self.world_x = 0.0
        self.active = False
        self.solved = False
        self.rotation_degrees = 0.0
        self.surface = self._create_surface()

    def _create_surface(self) -> pygame.Surface:
        size = self.radius * 2 + 10
        center = size // 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        bark_dark = (62, 35, 20)
        bark_mid = (118, 72, 37)
        bark_light = (173, 113, 56)
        ring = (226, 174, 92)
        ring_dark = (113, 67, 34)
        shadow = (20, 12, 24, 85)

        pygame.draw.circle(s, shadow, (center + 3, center + 4), self.radius)
        pygame.draw.circle(s, bark_dark, (center, center), self.radius)
        pygame.draw.circle(s, bark_mid, (center, center), self.radius - 4)
        pygame.draw.circle(s, ring, (center, center), self.radius - 13)
        pygame.draw.circle(s, ring_dark, (center, center), self.radius - 13, 3)
        for inset in (22, 31):
            rr = max(4, self.radius - inset)
            pygame.draw.circle(s, ring_dark, (center, center), rr, 2)
        # Repedések / kéregvonalak - ezek miatt forgás közben látszik a mozgás.
        for angle_deg, length_mul in ((18, 0.66), (108, 0.55), (212, 0.70), (296, 0.52)):
            a = math.radians(angle_deg)
            start = (center + int(math.cos(a) * self.radius * 0.18),
                     center + int(math.sin(a) * self.radius * 0.18))
            end = (center + int(math.cos(a) * self.radius * length_mul),
                   center + int(math.sin(a) * self.radius * length_mul))
            pygame.draw.line(s, ring_dark, start, end, 3)
        for y_off in (-self.radius // 2, -self.radius // 5, self.radius // 4):
            pygame.draw.arc(s, bark_light,
                            (center - self.radius + 7, center + y_off - 8, self.radius * 2 - 14, 18),
                            0.1, math.pi - 0.1, 3)
        pygame.draw.circle(s, (255, 220, 132, 80), (center - self.radius // 3, center - self.radius // 3), 6)
        return s

    @property
    def center_y(self) -> float:
        return self.ground_y - self.radius + 4

    @property
    def top_y(self) -> float:
        return self.center_y - self.collision_radius

    def spawn_from_screen_right(self, camera_x: float, screen_width: int) -> None:
        self.world_x = camera_x + screen_width + self.radius + 34
        self.active = True
        self.solved = False
        self.rotation_degrees = 0.0

    def update(self, dt: float, camera_x: float) -> None:
        if not self.active:
            return
        self.world_x -= self.speed * dt
        # Fizikailag a gördülés szöge út/r sugár; fokban tároljuk a pygame.rotate-hoz.
        self.rotation_degrees = (self.rotation_degrees - math.degrees(self.speed * dt / max(1, self.radius))) % 360
        if self.world_x < camera_x - self.radius - 90:
            self.active = False
            self.solved = True

    def collides_with_player(self, player: Player) -> bool:
        if not self.active:
            return False
        horizontal_overlap = abs(player.world_x - self.world_x) <= (
            self.collision_radius + player.collision_half_width + LOG_COLLISION_PADDING_X
        )
        if not horizontal_overlap:
            return False
        # A farkas midbottom Y-koordinátája akkor biztonságos, ha már a farönk
        # teteje fölé emelkedett. Így nem elég csak megnyomni az ugrást: időzíteni kell.
        return player.y > self.top_y + LOG_SAFE_CLEARANCE_EXTRA

    def draw(self, screen: pygame.Surface, camera_x: float) -> None:
        if not self.active:
            return
        screen_x = round(self.world_x - camera_x)
        rotated = pygame.transform.rotate(self.surface, self.rotation_degrees)
        rect = rotated.get_rect(center=(screen_x, round(self.center_y)))
        shadow_rect = pygame.Rect(0, 0, int(self.radius * 1.7), max(7, int(self.radius * 0.28)))
        shadow_rect.center = (screen_x, self.ground_y + 8)
        pygame.draw.ellipse(screen, (31, 22, 54), shadow_rect)
        screen.blit(rotated, rect)


class DarknessSignChallenge:
    """Negyedik kihívás: sötétség, kurzor-fény és egy mozdulattal rajzolt kereszt."""

    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.active = False
        self.solved = False
        self.finished = False
        self.alpha = 0.0
        self.drawing = False
        self.points: list[tuple[int, int]] = []
        scale = max(0.85, min(1.25, config.height / 700))
        self.spotlight_radius = int(SPOTLIGHT_RADIUS_BASE * scale)
        self.min_span = int(CROSS_GESTURE_MIN_SPAN_BASE * scale)
        self.tolerance = int(CROSS_GESTURE_TOLERANCE_BASE * scale)

    def start(self) -> None:
        self.active = True
        self.solved = False
        self.finished = False
        self.alpha = 0.0
        self.drawing = False
        self.points.clear()

    def is_visible(self) -> bool:
        return self.active and (self.alpha > 1.0 or not self.finished)

    def blocks_controls(self) -> bool:
        # A játékos addig maradjon megállítva, amíg a sötétség teljesen ki nem halványul.
        return self.active and not self.finished

    def update(self, dt: float) -> None:
        if not self.active:
            return
        target = 0.0 if self.solved else float(DARKNESS_MAX_ALPHA)
        speed = DARKNESS_FADE_OUT_SPEED if self.solved else DARKNESS_FADE_IN_SPEED
        if self.alpha < target:
            self.alpha = min(target, self.alpha + speed * dt)
        elif self.alpha > target:
            self.alpha = max(target, self.alpha - speed * dt)
        if self.solved and self.alpha <= 0.5:
            self.alpha = 0.0
            self.active = False
            self.finished = True
            self.points.clear()

    def begin_stroke(self, pos: tuple[int, int]) -> None:
        if not self.active or self.solved:
            return
        self.drawing = True
        self.points = [pos]

    def add_point(self, pos: tuple[int, int]) -> bool:
        if not self.active or self.solved or not self.drawing:
            return False
        if not self.points:
            self.points.append(pos)
        else:
            last_x, last_y = self.points[-1]
            dx = pos[0] - last_x
            dy = pos[1] - last_y
            if dx * dx + dy * dy >= 9:  # legalább 3 px mozgás; kis remegést kiszűr
                self.points.append(pos)
        # Ne nőjön végtelenre a lista, de maradjon elég pont a teljes mozdulathoz.
        if len(self.points) > 260:
            self.points = self.points[-260:]
        if self._looks_like_cross(self.points):
            self.solve()
            return True
        return False

    def end_stroke(self) -> bool:
        if not self.active or self.solved:
            self.drawing = False
            return False
        solved_now = self._looks_like_cross(self.points)
        if solved_now:
            self.solve()
        else:
            self.drawing = False
            # Ha nem sikerült, kezdhesse újra egyetlen friss mozdulattal.
            self.points.clear()
        return solved_now

    def solve(self) -> None:
        if self.solved:
            return
        self.solved = True
        self.drawing = False

    def _looks_like_cross(self, points: list[tuple[int, int]]) -> bool:
        """Szigorúbb + alakú kereszt-felismerés.

        A korábbi verzió túl engedékeny volt: már néhány szélső pontból vagy
        X-szerű firkából is megoldódhatott. Itt csak akkor fogadjuk el a jelet,
        ha a teljes mozdulat nagy része két, egymást középen metsző, közel
        vízszintes és közel függőleges sávban halad.
        """
        if len(points) < CROSS_GESTURE_MIN_POINTS:
            return False

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max_x - min_x
        span_y = max_y - min_y
        if span_x < self.min_span or span_y < self.min_span:
            return False

        # A klasszikus + kereszt legyen viszonylag arányos; ne lehessen egy
        # hosszú vonalra kis kampóval megoldani.
        aspect = span_x / max(1, span_y)
        if aspect < 0.72 or aspect > 1.38:
            return False

        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        return self._looks_like_plus(points, cx, cy, span_x, span_y)

    def _looks_like_plus(self, points: list[tuple[int, int]], cx: float, cy: float,
                         span_x: float, span_y: float) -> bool:
        # Jóval kisebb tolerancia: csak a középvonalak közelében húzott mozdulat
        # számít. A magasságfüggő alapértékhez képest sem engedjük túl nagyra nőni.
        tol = max(10.0, min(float(self.tolerance), min(span_x, span_y) * 0.095))
        center_tol = max(12.0, min(span_x, span_y) * 0.075)
        arm_x = span_x * 0.39
        arm_y = span_y * 0.39

        left = right = top = bottom = False
        center_hits = 0
        horizontal_points = 0
        vertical_points = 0
        corner_points = 0

        for x, y in points:
            near_h = abs(y - cy) <= tol
            near_v = abs(x - cx) <= tol
            if near_h:
                horizontal_points += 1
            if near_v:
                vertical_points += 1
            if near_h and x <= cx - arm_x:
                left = True
            if near_h and x >= cx + arm_x:
                right = True
            if near_v and y <= cy - arm_y:
                top = True
            if near_v and y >= cy + arm_y:
                bottom = True
            if abs(x - cx) <= center_tol and abs(y - cy) <= center_tol:
                center_hits += 1
            # Távoli sarokpontok tipikusan X-et, kört vagy firkát jeleznek.
            if abs(x - cx) > tol * 1.7 and abs(y - cy) > tol * 1.7:
                corner_points += 1

        if not (left and right and top and bottom):
            return False
        if center_hits < 3:
            return False
        if horizontal_points < len(points) * 0.24 or vertical_points < len(points) * 0.24:
            return False
        if corner_points > len(points) * 0.16:
            return False

        # A teljes út hosszának nagy része a vízszintes vagy függőleges sávban
        # legyen. Ez kizárja az átlós X-et és a nagy, pontatlan kanyarokat.
        total_len = 0.0
        axis_aligned_len = 0.0
        horizontal_len = 0.0
        vertical_len = 0.0
        center_crossings = 0
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            dx = x2 - x1
            dy = y2 - y1
            seg_len = math.hypot(dx, dy)
            if seg_len <= 0.01:
                continue
            total_len += seg_len
            mx = (x1 + x2) / 2.0
            my = (y1 + y2) / 2.0
            near_h = abs(my - cy) <= tol
            near_v = abs(mx - cx) <= tol
            if near_h or near_v:
                axis_aligned_len += seg_len
            if near_h:
                horizontal_len += seg_len
            if near_v:
                vertical_len += seg_len
            if abs(mx - cx) <= center_tol and abs(my - cy) <= center_tol:
                center_crossings += 1

        if total_len < self.min_span * 1.65:
            return False
        if axis_aligned_len / total_len < 0.82:
            return False
        if horizontal_len / total_len < 0.24 or vertical_len / total_len < 0.24:
            return False
        if center_crossings < 2:
            return False

        return True

    def handle_event(self, event: pygame.event.Event) -> bool:
        """True-val tér vissza, ha az esemény megoldotta a kihívást."""
        if not self.active or self.solved:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Kattintással mindig tiszta, új egy-mozdulatú rajz indul.
            self.begin_stroke(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            # Nem kötelező kattintani: ha a játékos csak a kurzorral rajzolja meg
            # a jelet, azt is egy folyamatos mozdulatként kezeljük.
            if not self.drawing:
                self.begin_stroke(event.pos)
            return self.add_point(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            return self.end_stroke()
        return False

    def draw_trace(self, screen: pygame.Surface) -> None:
        # A rajzolt jel a sötét overlay ALÁ kerül; így igazán csak a kurzor fénye alatt látszik.
        if not self.active or len(self.points) < 2 or self.alpha <= 8:
            return
        trace = pygame.Surface((self.config.width, self.config.height), pygame.SRCALPHA)
        line_width = max(3, int(self.config.height * 0.006))
        pygame.draw.lines(trace, (235, 242, 255, 135), False, self.points, line_width)
        for point in self.points[-5:]:
            pygame.draw.circle(trace, (245, 248, 255, 90), point, line_width + 2)
        screen.blit(trace, (0, 0))

    def draw_darkness(self, screen: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        if not self.active or self.alpha <= 0.5:
            return
        base_alpha = int(max(0, min(DARKNESS_MAX_ALPHA, self.alpha)))
        overlay = pygame.Surface((self.config.width, self.config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, base_alpha))
        mx, my = mouse_pos
        r = self.spotlight_radius
        # Puha peremű fénykör: kívül majdnem fekete, középen teljesen átlátszó.
        for radius, alpha_mul in (
            (int(r * 1.45), 0.92),
            (int(r * 1.25), 0.76),
            (int(r * 1.08), 0.48),
            (r, 0.0),
        ):
            pygame.draw.circle(overlay, (0, 0, 0, int(base_alpha * alpha_mul)), (mx, my), radius)
        screen.blit(overlay, (0, 0))


class Platform:
    """Egyetlen ugró-kocka a sziklacsúcs jelenetben (egyirányú platform - csak felülről áll meg)."""

    def __init__(self, left: float, top_y: float, width: int,
                 height: int = PEAK_BLOCK_HEIGHT_BASE, is_summit: bool = False) -> None:
        self.left = float(left)
        self.top_y = float(top_y)
        self.width = int(width)
        self.height = int(height)
        self.right = self.left + self.width
        self.is_summit = is_summit
        self.surface = self._build_surface()

    def _build_surface(self) -> pygame.Surface:
        w = self.width
        h = self.height
        surf = pygame.Surface((w + 16, h + 18), pygame.SRCALPHA)
        if self.is_summit:
            base_color = (78, 96, 158)
            edge_color = (208, 222, 255)
            highlight = (228, 238, 255)
            crack_color = (32, 40, 84)
            shadow_color = (16, 22, 56, 145)
        else:
            base_color = (52, 64, 110)
            edge_color = (158, 186, 240)
            highlight = (204, 220, 252)
            crack_color = (24, 30, 70)
            shadow_color = (12, 18, 46, 130)
        # Halvány "leheletszerű" árnyék a kocka alatt
        shadow_surf = pygame.Surface((w + 16, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, shadow_color, shadow_surf.get_rect())
        surf.blit(shadow_surf, (0, h + 4))
        body_rect = pygame.Rect(8, 4, w, h)
        pygame.draw.rect(surf, base_color, body_rect, border_radius=7)
        # Felső megvilágított perem - holdfény
        pygame.draw.rect(surf, edge_color, (8, 4, w, 5), border_radius=5)
        pygame.draw.line(surf, highlight, (12, 6), (8 + w - 5, 6), 1)
        # Körvonal
        pygame.draw.rect(surf, edge_color, body_rect, 2, border_radius=7)
        # Néhány halvány szikla-repedés (deterministic seed a kocka pozíciója alapján)
        rng = random.Random(int(self.left * 31 + self.top_y * 7) & 0xFFFFFF)
        crack_count = 4 if self.is_summit else 3
        for _ in range(crack_count):
            cx = rng.randint(12, max(13, w - 4))
            cy = rng.randint(10, max(11, h - 3))
            length = rng.randint(4, 11)
            pygame.draw.line(surf, crack_color, (cx, cy), (cx + length, cy + 1), 1)
        if self.is_summit:
            # Apró fény-csillanás a csúcson
            pygame.draw.circle(surf, (235, 245, 255, 200),
                               (8 + w // 2, 7), 3)
        return surf

    def contains_x(self, world_x: float) -> bool:
        return self.left <= world_x <= self.right

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float = 0.0) -> None:
        screen_x = round(self.left - camera_x) - 8
        screen_y = round(self.top_y - camera_y) - 4
        screen.blit(self.surface, (screen_x, screen_y))


class RockyPeak:
    """Ötödik akadály: apró kockákon kell felugrálni egy magas sziklacsúcsra.

    A pálya kb. 4-5 képernyőnyi magas, függőlegesen variált útvonal.
    A kamera vertikálisan is követi a játékost, így a következő kocka mindig
    látható. A blokkok keskenyek (alap 110 px) és gyakran átfedik egymást
    vízszintesen, így a függőleges felugrálás a fő mechanika.
    """

    def __init__(self, base_x: float, ground_y: int, scale: float = 1.0,
                 screen_height: int = 720) -> None:
        self.base_x = float(base_x)
        self.ground_y = int(ground_y)
        self.scale = scale
        self.screen_height = screen_height
        self.active = False
        self.solved = False
        target_climb_height = max(2400, int(screen_height * PEAK_CLIMB_SCREENS))
        layout, total_height = self._generate_layout(scale, target_climb_height)
        self.platforms: list[Platform] = []
        for rel_x, height_above, w in layout:
            left = self.base_x + rel_x
            top = self.ground_y - height_above
            self.platforms.append(Platform(left, top, w))
        # A sziklacsúcs - utolsó, szélesebb és magasabban a legfelsőnél.
        last_rel_x, last_height, last_w = layout[-1]
        summit_w = max(170, int(220 * scale))
        # A csúcs a legutolsó kocka középvonala fölé igazítva, de a kockánál
        # szélesebb, így a játékos kényelmesen tud landolni.
        summit_rel_x = last_rel_x + (last_w - summit_w) // 2
        summit_height = last_height + max(60, int(72 * scale))
        summit_left = self.base_x + summit_rel_x
        summit_top = self.ground_y - summit_height
        self.summit = Platform(summit_left, summit_top, summit_w,
                               height=int(PEAK_BLOCK_HEIGHT_BASE * 1.30),
                               is_summit=True)
        self.platforms.append(self.summit)
        self.summit_height = summit_height
        # Láthatatlan szikla-fal a talajon, a kockáktól jobbra.
        # Csak a kockákon át lehet feljutni / továbbjutni.
        max_x = max(p.right for p in self.platforms) + max(80, int(120 * scale))
        self.wall_world_x = max_x
        # Háttérrétegek: hegy-sziluett és csillagok
        self.silhouette = self._build_silhouette()
        # A csillagokat egy listában tároljuk (rel_x, height_above_ground, radius, shade)
        # - sokkal hatékonyabb mint egy óriási előre-renderelt felület.
        self.stars = self._build_stars_data()

    def _generate_layout(self, scale: float, target_climb_height: int):
        """Procedurálisan generál egy variált felfelé vezető útvonalat (deterministic).

        A blokkok jellemzően átfedik egymást vízszintesen (h_offset < block_w),
        így a játékos egyszerű "felugrás egyenesen" technikával is feljebb juthat.
        Időnként nagyobb oldalsó eltolások (kis átfedés) levegő-irányítást
        igényelnek, ami változatossá teszi a mászást.

        Visszaadja: ((rel_x, height_above_ground, width), ...), total_height
        """
        rng = random.Random(20260)
        block_w = max(78, int(PEAK_BLOCK_WIDTH_BASE * scale))
        v_step_avg = max(58, int(70 * scale))
        num_steps = max(30, target_climb_height // v_step_avg)
        # A vízszintes "pszeudo-középvonal" - a kockák ekörül cikkcakkolnak.
        rel_x = 0
        height_above = max(50, int(56 * scale))
        sign = 1
        layout: list[tuple[int, int, int]] = []
        for i in range(num_steps):
            layout.append((rel_x, height_above, block_w))
            # Függőleges lépés: enyhe variancia, hogy ne legyen mechanikus.
            v_step = rng.randint(int(v_step_avg * 0.85), int(v_step_avg * 1.18))
            height_above += v_step
            # Vízszintes minta-választás: 4-féle közül.
            roll = rng.random()
            if roll < 0.32:
                # Közvetlen átfedés - majdnem teljesen függőleges felugrás.
                h_offset = rng.randint(-int(22 * scale), int(22 * scale))
            elif roll < 0.58:
                # Kis oldalra-csúszás (jó átfedés).
                h_offset = int(rng.randint(28, 50) * scale) * sign
                sign *= -1
            elif roll < 0.84:
                # Mérsékelt oldalra-lépés (kisebb átfedés).
                h_offset = int(rng.randint(50, 75) * scale) * sign
                sign *= -1
            else:
                # Nagyobb oldal-ugrás - levegő-irányítás kell, kis vagy nincs átfedés.
                h_offset = int(rng.randint(75, 95) * scale) * sign
                sign *= -1
            rel_x += h_offset
            # Tartsuk a vízszintes drift-et viszonylag korlátok közt, hogy a
            # sziluett mögötte mindig kompozícióban maradjon.
            if rel_x > int(550 * scale):
                rel_x = int(540 * scale)
                sign = -1
            elif rel_x < int(-450 * scale):
                rel_x = int(-440 * scale)
                sign = 1
        return layout, height_above

    def _build_silhouette(self) -> pygame.Surface:
        """Hegy-sziluett a kockák mögött. Magas, hogy a mászás nagy részét lefedje."""
        scale = self.scale
        w = max(1500, int(2400 * scale))
        # A magasság kb. 1500-1800 px. Ennél magasabban már csak csillagok látszanak,
        # ahogy "a hegy fölé emelkedik" a játékos - ez vizuálisan helyes.
        h = max(1100, int(1700 * scale))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(2027)
        # Három réteg mélységérzethez
        layers = [
            ((16, 22, 58, 220),  0.00, 1.00, 65),
            ((26, 34, 80, 200),  0.05, 0.90, 50),
            ((40, 52, 106, 170), 0.12, 0.78, 38),
        ]
        for color, ox_factor, sy_factor, jag in layers:
            ox = int(w * ox_factor)
            base_y = h
            peak_y = int(h * (1.0 - sy_factor))
            mid_x = int(w * 0.55) + ox
            points = [(0, base_y)]
            x = 0
            while x < w:
                step = rng.randint(38, 100)
                x += step
                t = max(0.0, 1.0 - abs(x - mid_x) / (w * 0.55))
                local_jag = rng.randint(-jag // 2, jag)
                y = int(base_y - (base_y - peak_y) * (t ** 1.55) + local_jag)
                y = max(peak_y - 25, min(base_y, y))
                points.append((min(x, w), y))
            points.append((w, base_y))
            pygame.draw.polygon(surf, color, points)
        # Hó-csillanások a magasabb pontok körül
        for _ in range(28):
            sx = int(w * 0.5) + rng.randint(-int(w * 0.20), int(w * 0.20))
            sy = int(h * 0.08) + rng.randint(0, int(h * 0.12))
            pygame.draw.circle(surf, (210, 220, 250, 130), (sx, sy), rng.randint(2, 4))
        return surf

    def _build_stars_data(self) -> list[tuple[int, int, int, int, int]]:
        """Csillagok mint (rel_x, height_above_ground, radius, shade, alpha) tuplek.

        Egy lista - a draw során direkt rajzoljuk őket. Lefedi a teljes mászási
        területet, beleértve a csúcs feletti "égbolt" tartományt is.
        """
        scale = self.scale
        rng = random.Random(7777)
        # Vízszintes kiterjedés: a kockák szélességét lefedi, plusz buffer.
        x_min = int(-450 * scale)
        x_max = int(self.wall_world_x - self.base_x + 350 * scale)
        # Függőleges: a talajtól a csúcs felett még 350 px-ig.
        y_max_above = self.summit_height + max(280, int(380 * scale))
        # Sűrűség: arányosan a területtel
        area = (x_max - x_min) * y_max_above
        count = max(180, int(area / 5800))
        stars: list[tuple[int, int, int, int, int]] = []
        for _ in range(count):
            rx = rng.randint(x_min, x_max)
            # Magasságfüggő bias: minél magasabb, annál sűrűbb csillag.
            ry_factor = rng.random() ** 0.55
            ry = int(40 + ry_factor * (y_max_above - 40))
            # Néha nagyobb csillag (ritkább)
            r = rng.randint(1, 2)
            if rng.random() < 0.08:
                r = 3
            shade = rng.randint(195, 255)
            alpha = rng.randint(150, 240)
            stars.append((rx, ry, r, shade, alpha))
        return stars

    def activate(self) -> None:
        self.active = True

    def floor_y_under(self, world_x: float, current_y: float) -> float | None:
        """A legmagasabb (legkisebb y) platform-tető, amely a játékos talpa alatt van."""
        best: float | None = None
        for plat in self.platforms:
            if plat.contains_x(world_x) and plat.top_y >= current_y - 0.5:
                if best is None or plat.top_y < best:
                    best = plat.top_y
        return best

    def is_on_summit(self, world_x: float, y: float, on_ground: bool) -> bool:
        if not on_ground:
            return False
        if not self.summit.contains_x(world_x):
            return False
        return abs(y - self.summit.top_y) <= PEAK_SUMMIT_DETECT_TOLERANCE

    def player_blocked_by_wall(self, player_world_x: float, collision_half_width: float) -> bool:
        """Igaz, ha a játékos jelenleg pont a (még zárt) sziklafalnak nyomódik."""
        if self.solved:
            return False
        block_x = self.wall_world_x - collision_half_width
        return abs(player_world_x - block_x) < 0.5

    def draw_silhouette(self, screen: pygame.Surface, camera_x: float, camera_y: float = 0.0) -> None:
        if not self.active:
            return
        screen_w = screen.get_width()
        screen_h = screen.get_height()
        # Csillagok: a legtávolabbi réteg, lassú parallax mind X-ben, mind Y-ban.
        # Direkt rajz: kis, gyors körök. Egyszerűbb mint óriási felület-cache.
        star_parallax_x = 0.30
        star_parallax_y = 0.20
        for rx, ry, radius, shade, alpha in self.stars:
            world_x = self.base_x + rx
            world_y = self.ground_y - ry
            sx = round(world_x - camera_x * star_parallax_x)
            sy = round(world_y - camera_y * star_parallax_y)
            # Csak a látható csillagokat rajzoljuk
            if -3 <= sx < screen_w + 3 and -3 <= sy < screen_h + 3:
                color = (shade, shade, min(255, shade + 8))
                if radius >= 3:
                    # Nagyobb csillaghoz halvány glow-aura
                    pygame.draw.circle(screen, (shade // 2, shade // 2, shade), (sx, sy), radius + 1)
                pygame.draw.circle(screen, color, (sx, sy), radius)
        # Hegy-sziluett: közepes parallax (0.42), így csak akkor "marad alul",
        # ahogy felfelé mászunk - természetes érzet.
        sil_parallax = 0.42
        sil_screen_x = round(self.base_x - 350 * self.scale - camera_x * sil_parallax)
        sil_screen_y = round(self.ground_y - self.silhouette.get_height() - camera_y * sil_parallax)
        # Csak akkor blittolunk, ha a sziluett legalább részben látható.
        if (sil_screen_y < screen_h
            and sil_screen_y + self.silhouette.get_height() > 0
            and sil_screen_x < screen_w
            and sil_screen_x + self.silhouette.get_width() > 0):
            screen.blit(self.silhouette, (sil_screen_x, sil_screen_y))

    def draw_platforms(self, screen: pygame.Surface, camera_x: float, camera_y: float = 0.0) -> None:
        if not self.active:
            return
        for plat in self.platforms:
            plat.draw(screen, camera_x, camera_y)


class ConstellationChallenge:
    """Záró kihívás a csúcson: a játékosnak egyetlen folyamatos mozdulattal
    össze kell kötnie a Göncöl szekér 7 csillagát.

    A csillagok fix pozícióban láthatók a képernyőn (nem sötétített háttéren!),
    a játékos pedig egy mozdulattal végighúzza a kurzort rajtuk a megfelelő
    sorrendben. A "szekér-test" 4 csillagát követi 3 további csillag a "rúdra".
    Két irányban is rajzolható: a szekér-test bal-alsó csillagából indulva
    a rúd vége felé, vagy fordítva.
    """

    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.active = False
        self.solved = False
        self.drawing = False
        self.points: list[tuple[int, int]] = []
        self.next_star_index = 0
        self.direction = 0  # 0=ismeretlen, 1=előre (0..6), -1=hátra (6..0)
        self.completion_pulse_t = 0.0
        # Skálázás a képernyőhöz
        scale_x = max(0.85, min(1.4, config.width / 1280))
        scale_y = max(0.85, min(1.4, config.height / 720))
        self.tolerance = max(38, int(CONSTELLATION_STAR_HIT_TOLERANCE_BASE
                                     * min(scale_x, scale_y)))
        self.line_width = max(2, int(CONSTELLATION_LINE_WIDTH_BASE * scale_y))
        # Csillagok pozíciója a képernyő felső felében, középre igazítva.
        # Nem pont a tetején, hogy elférjen körülötte vizuális tér is.
        cx = config.width // 2
        cy = int(config.height * 0.34)

        def s(dx: float, dy: float) -> tuple[int, int]:
            return (int(cx + dx * scale_x), int(cy + dy * scale_y))

        self.stars: list[tuple[int, int]] = [
            s(-300, +75),   # 0: szekér bal-lent
            s(-300, -90),   # 1: szekér bal-fent
            s(-105, -90),   # 2: szekér jobb-fent
            s(-105, +75),   # 3: szekér jobb-lent (ide csatlakozik a rúd)
            s(+85,  +35),   # 4: rúd 1 (Alioth)
            s(+225, -10),   # 5: rúd 2 (Mizar) - enyhe felfelé ív
            s(+385, -65),   # 6: rúd 3 / Alkaid (vége)
        ]
        self.completed: list[bool] = [False] * len(self.stars)

    def start(self) -> None:
        self.active = True
        self.solved = False
        self.drawing = False
        self.points.clear()
        self.next_star_index = 0
        self.direction = 0
        self.completion_pulse_t = 0.0
        self.completed = [False] * len(self.stars)

    def is_visible(self) -> bool:
        return self.active

    def blocks_controls(self) -> bool:
        return self.active and not self.solved

    def update(self, dt: float) -> None:
        if self.solved:
            self.completion_pulse_t += dt

    def begin_stroke(self, pos: tuple[int, int]) -> None:
        if not self.active or self.solved:
            return
        self.drawing = True
        self.points = [pos]
        self._check_star_hit(pos)

    def add_point(self, pos: tuple[int, int]) -> bool:
        if not self.active or self.solved or not self.drawing:
            return False
        if self.points:
            last_x, last_y = self.points[-1]
            dx = pos[0] - last_x
            dy = pos[1] - last_y
            if dx * dx + dy * dy < 9:  # legalább 3 px mozgás
                return False
        self.points.append(pos)
        if len(self.points) > 800:
            self.points = self.points[-800:]
        self._check_star_hit(pos)
        return self.solved

    def _check_star_hit(self, pos: tuple[int, int]) -> None:
        """Megnézi, hogy az aktuális pont eltalálja-e a soron következő csillagot.

        Az első találat határozza meg a rajzolási irányt: ha a 0. csillagot éri
        el először, előre megy a sorozaton; ha a 6.-at, fordítva. Bármi más
        kezdés esetén a két végponton várjuk az első találatot.
        """
        if self.direction == 0:
            # Még nincs irány - nézzük mind a két végpontot
            d_first_sq = self._dist_sq(pos, self.stars[0])
            d_last_sq = self._dist_sq(pos, self.stars[-1])
            tol_sq = self.tolerance * self.tolerance
            if d_first_sq <= tol_sq and d_first_sq <= d_last_sq:
                self.direction = 1
                self.completed[0] = True
                self.next_star_index = 1
            elif d_last_sq <= tol_sq:
                self.direction = -1
                self.completed[-1] = True
                self.next_star_index = len(self.stars) - 2
            return
        # Irány már megvan - csak a következő csillagot vizsgáljuk
        if 0 <= self.next_star_index < len(self.stars):
            star = self.stars[self.next_star_index]
            if self._dist_sq(pos, star) <= self.tolerance * self.tolerance:
                self.completed[self.next_star_index] = True
                self.next_star_index += self.direction
                # Megoldás-ellenőrzés
                if self.direction == 1 and self.next_star_index >= len(self.stars):
                    self.solved = True
                elif self.direction == -1 and self.next_star_index < 0:
                    self.solved = True

    @staticmethod
    def _dist_sq(a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return dx * dx + dy * dy

    def end_stroke(self) -> bool:
        # A mozdulat-vég nem reseteli a haladást; a játékos folytathatja egy
        # új lehúzással ott, ahol abbahagyta. (Csak abbahagyja az aktív rajzolást.)
        self.drawing = False
        return self.solved

    def handle_event(self, event: pygame.event.Event) -> bool:
        """True-val tér vissza, ha az esemény megoldotta a kihívást."""
        if not self.active or self.solved:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.begin_stroke(event.pos)
            return self.solved
        if event.type == pygame.MOUSEMOTION:
            # Mint a kereszt-kihívásnál: nem kötelező lenyomva tartani a gombot.
            if not self.drawing:
                self.begin_stroke(event.pos)
            return self.add_point(event.pos)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            return self.end_stroke()
        return False

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        # 1) Befejezett összekötő-vonalak (csillagról csillagra) - ezek tartósak.
        completed_count = sum(1 for c in self.completed if c)
        if completed_count >= 2:
            if self.direction == 1:
                line_pts = self.stars[:completed_count]
            elif self.direction == -1:
                # Hátrafelé: a végéről indulva
                line_pts = self.stars[len(self.stars) - completed_count:][::-1]
            else:
                line_pts = []
            if len(line_pts) >= 2:
                pygame.draw.lines(screen, (235, 248, 255), False, line_pts,
                                  self.line_width)
                # Halvány glow a vonalak körül
                pygame.draw.lines(screen, (165, 195, 245), False, line_pts,
                                  max(1, self.line_width - 1))

        # 2) Az aktuális rajzolás-nyom (a kurzor mozgása) - lényegesen halványabb
        # mint a befejezett vonalak, de még mindig látható segítség.
        if len(self.points) >= 2 and not self.solved:
            pygame.draw.lines(screen, (200, 220, 255), False, self.points,
                              max(1, self.line_width - 1))
            # A legfrissebb pontok ragyognak picit jobban
            for p in self.points[-6:]:
                pygame.draw.circle(screen, (240, 245, 255), p,
                                   max(2, self.line_width))

        # 3) Csillagok megjelenítése - különböző állapotok:
        #    - befejezett: világos, fényes csillag halóval
        #    - "soron következő": pulzáló célpont
        #    - várakozó: halvány, szerény csillag
        ticks_ms = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(ticks_ms * 0.006)
        for i, (sx, sy) in enumerate(self.stars):
            done = self.completed[i]
            is_next = (i == self.next_star_index) and not self.solved and self.direction != 0
            # Kezdő pont jelölés (0 vagy 6) ha még nincs irány - mindkét végpont pulzál
            is_start_candidate = (self.direction == 0 and i in (0, len(self.stars) - 1)
                                  and not self.solved)
            if done:
                # Fényes csillag halóval
                pygame.draw.circle(screen, (160, 180, 220), (sx, sy), 12)
                pygame.draw.circle(screen, (240, 248, 255), (sx, sy), 7)
                pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 3)
            elif is_next or is_start_candidate:
                # Pulzáló cél
                radius = int(9 + pulse * 5)
                pygame.draw.circle(screen, (180, 210, 255), (sx, sy),
                                   radius, 2)
                pygame.draw.circle(screen, (235, 245, 255), (sx, sy), 5)
                pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 2)
            else:
                # Halvány, várakozó csillag
                pygame.draw.circle(screen, (155, 175, 220), (sx, sy), 6)
                pygame.draw.circle(screen, (210, 220, 245), (sx, sy), 3)

        # 4) Megoldás után rövid pulzáló glow az egész alakzaton
        if self.solved:
            ts = self.completion_pulse_t
            glow = (math.sin(ts * 4.0) * 0.5 + 0.5)
            for sx, sy in self.stars:
                radius = int(14 + glow * 6)
                # Halvány, áttetsző glow réteg - direct rajzolás opaque színnel
                pygame.draw.circle(screen, (130, 165, 220), (sx, sy), radius, 1)


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
        # Külön ülő kép (ulelorenez.png) - ha az assets könyvtárban megtalálható, betöltjük.
        # Ezt a 6. jelenetben használjuk, amikor a csúcson megpihen a farkas.
        # Ha nincs ilyen fájl, fallback: az utolsó stop frame (idle pozíció).
        sitting_path = asset_dir / SITTING_FRAME_FILENAME
        if sitting_path.exists():
            try:
                self.sitting_frame = load_frame_file(sitting_path, SPRITE_HEIGHT)
            except Exception:
                self.sitting_frame = self.stop_frames[-1]
        else:
            self.sitting_frame = self.stop_frames[-1]
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

    def start_animation(self, state: str) -> None:
        if self.animation_state != state:
            self.animation_state = state
            self.animation_timer = 0.0

    def set_jump_phase(self, phase: str) -> None:
        if self.jump_phase != phase:
            self.jump_phase = phase
            self.jump_phase_timer = 0.0

    def handle_input(self, dt: float, obstacle_left_edge: float | None,
                     controls_enabled: bool, movement_blocked: bool = False) -> None:
        keys = pygame.key.get_pressed()
        raw_left = controls_enabled and (keys[pygame.K_LEFT] or keys[pygame.K_a])
        raw_right = controls_enabled and (keys[pygame.K_RIGHT] or keys[pygame.K_d])
        raw_jump = controls_enabled and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP])

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
        rect = image.get_rect(midbottom=(screen_x, screen_y))
        screen.blit(image, rect)


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        info = pygame.display.Info()
        self.config = WorldConfig(max(960, info.current_w), max(540, info.current_h))
        self.screen = pygame.display.set_mode((self.config.width, self.config.height), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.menu = IntroMenuScreen(self.config)
        self.state = "menu"
        self.music_enabled = True
        self.music_available = False
        self.music_path_found = False
        self._init_music()
        self.background = StaticBackground(self.config)
        self.player = Player(self.config)
        self.dialogue = DialogueBox(self.config)
        self.thought_bubble = ThoughtBubble(self.config)
        scale = max(1.0, self.config.height / 700)
        self.bush = ThornBush(world_x=2500, ground_y=self.config.ground_top_y, scale=scale)
        self.lake = Lake(world_x=LAKE_WORLD_X, ground_y=self.config.ground_top_y,
                         screen_height=self.config.height, scale=scale)
        self.willpower = WillpowerIndicator(self.config)
        self.rolling_log = RollingLog(ground_y=self.config.ground_top_y, scale=scale)
        self.dark_challenge = DarknessSignChallenge(self.config)
        self.camera_x = 0.0
        self.camera_y = 0.0  # vertikális kamera-eltolás (csak a sziklacsúcs jelenetben mozog)
        self.cinematic_camera_active = False
        self.cinematic_camera_target_x = 0.0
        self.pending_obstacle_text = ""
        # Bozót akadály állapotai
        self.bush_event_triggered = False
        self.bush_solved = False
        # Tó akadály állapotai
        self.lake_event_triggered = False
        self.lake_solved = False
        self.lake_hold_timer = 0.0  # 0..LAKE_HOLD_DURATION
        # Farönk akadály állapotai
        self.log_event_triggered = False
        self.log_solved = False
        self.log_camera_transition_active = False
        self.log_camera_transition_target_x = 0.0
        # Sötétség / kereszt akadály állapotai
        self.dark_event_triggered = False
        self.dark_solved = False
        # Sziklacsúcs akadály állapotai (5. jelenet)
        peak_base_x = float(PEAK_CHALLENGE_WORLD_X + PEAK_BASE_OFFSET_X)
        self.peak = RockyPeak(base_x=peak_base_x, ground_y=self.config.ground_top_y,
                              scale=scale, screen_height=self.config.height)
        self.peak_event_triggered = False
        self.peak_solved = False
        # 6. jelenet: csillagkép - a farkas a csúcson ülve felidézi a Göncölt.
        # A workflow szakaszai:
        #   "idle"     - még nem ért fel
        #   "sit"      - leült, dialog mutatja a "Mostmár tisztán látom..." szöveget
        #   "memory"   - dialog mutatja a "Emlékszem egy csillagképre..." szöveget
        #   "drawing"  - a csillagkép-kihívás aktív
        #   "done"     - kész, dialog mutatja a befejező szöveget
        self.constellation = ConstellationChallenge(self.config)
        self.constellation_phase = "idle"
        self.game_over = False
        self.debug_font = pygame.font.SysFont("arial", max(18, int(self.config.height * 0.024)))
        self.music_font = pygame.font.SysFont("arial", max(18, int(self.config.height * 0.025)), bold=True)
        # Cache-elt help szöveg - nem változik, nem kell minden frame újra-renderelni.
        self._help_surface: pygame.Surface | None = None
        self._help_bg: pygame.Surface | None = None
        self._build_help_overlay()
        self.running = True

    def _build_help_overlay(self) -> None:
        text = "Mozgás: A/D vagy ←/→    Ugrás: Space / W / ↑    M: zene ki/be    Enter: üzenet bezárása    Esc: kilépés"
        surface = self.debug_font.render(text, True, (226, 232, 255))
        bg = pygame.Surface((surface.get_width() + 22, surface.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 12, 34, 110), bg.get_rect(), border_radius=14)
        self._help_surface = surface
        self._help_bg = bg

    def _init_music(self) -> None:
        asset_dir = Path(__file__).parent / "assets"
        candidates = [
            asset_dir / "dallam.wav",
            Path("/mnt/data/assets/dallam.wav"),
        ]
        music_path = next((path for path in candidates if path.exists()), asset_dir / "dallam.wav")
        self.music_path_found = music_path.exists()
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            if self.music_path_found:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(0.55)
                self.music_available = True
        except pygame.error:
            self.music_available = False

    def _start_music_if_needed(self) -> None:
        if self.state != "playing" or not self.music_enabled or not self.music_available:
            return
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)

    def _stop_music(self) -> None:
        if self.music_available and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def toggle_music(self) -> None:
        self.music_enabled = not self.music_enabled
        if not self.music_enabled:
            self._stop_music()
        else:
            self._start_music_if_needed()

    def activate_menu_option(self, option_index: int) -> None:
        option = self.menu.options[option_index]
        if option == "Játék indítása":
            self.start_game()
        elif option == "Névjegy":
            self.state = "about"
            self._stop_music()
        else:
            self.running = False

    def start_game(self) -> None:
        self.state = "playing"
        self.dialogue.hide()
        self.dialogue.show(INTRO_TEXT)
        self._start_music_if_needed()

    def draw_music_status(self) -> None:
        if self.state != "playing":
            return
        if not self.music_path_found:
            text = "Zene: a dallam.wav hiányzik az assets mappából"
        elif not self.music_available:
            text = "Zene: a hangrendszer nem elérhető"
        else:
            text = f"Zene: {'BE' if self.music_enabled else 'KI'}  [M]"
        surface = self.music_font.render(text, True, (234, 238, 255))
        bg = pygame.Surface((surface.get_width() + 18, surface.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 12, 34, 120), bg.get_rect(), border_radius=14)
        x = self.config.width - bg.get_width() - 22
        y = 18
        self.screen.blit(bg, (x, y))
        self.screen.blit(surface, (x + 9, y + 6))

    def controls_enabled(self) -> bool:
        return (
            not self.game_over
            and not self.dialogue.active
            and not self.cinematic_camera_active
            and not self.log_camera_transition_active
            and not self.dark_challenge.blocks_controls()
            and not self.constellation.blocks_controls()
            and self.constellation_phase in ("idle", "done")
        )

    def movement_blocked(self) -> bool:
        """Teljes mozgás-tiltás csak a bozót akadálynál van. A tó NEM tiltja
        a mozgást, csak a jobbra-haladást blokkolja az obstacle_left_edge-en át -
        így a játékos elsétálhat balra is, és a fizika természetes marad."""
        return self.bush_event_triggered and not self.bush_solved

    def obstacle_left_edge(self) -> float | None:
        if self.bush_event_triggered and not self.bush_solved:
            return self.bush.left_edge
        if self.lake_event_triggered and not self.lake_solved:
            return self.lake.left_edge
        # A sziklacsúcs jelenetben láthatatlan fal blokkolja a talajszintű
        # tovább-sétálást, amíg a játékos nem ér fel a csúcsra. Így a kockákon
        # át vezet az egyetlen lehetséges út.
        if self.peak_event_triggered and not self.peak_solved:
            return self.peak.wall_world_x
        return None

    def floor_y_for_player(self) -> float:
        """A játékos jelenlegi x-pozíciója alatt fellelhető legmagasabb támaszték y-ja.

        Ha aktív a sziklacsúcs jelenet, a kockák tetejei is jelölhetnek "felszínt".
        Egyébként a fő talaj.
        """
        ground_y = float(self.config.ground_top_y)
        if self.peak_event_triggered:
            plat_y = self.peak.floor_y_under(self.player.world_x, self.player.y)
            if plat_y is not None and plat_y < ground_y:
                return plat_y
        return ground_y

    def is_pressed_against_lake(self) -> bool:
        """A játékos ténylegesen a tó által blokkolt helyzetben van-e?
        (handle_input min()-eli a world_x-et erre az értékre, ha jobbra próbál menni.)"""
        if not self.lake_event_triggered or self.lake_solved:
            return False
        block_x = self.lake.left_edge - self.player.collision_half_width
        return abs(self.player.world_x - block_x) < LAKE_BLOCK_EPSILON

    def start_obstacle_reveal(self, obstacle_left_edge: float, stop_distance: float, text: str,
                              *, preserve_player_position: bool = False,
                              target_player_screen_x: int | None = None) -> None:
        """Közös, újrahasználható akadály-megjelenítés minden nagy akadályhoz.

        A tónál már nem teleportáljuk előre a farkast a régi bal oldali reveal
        pozícióba, mert a korábbi kamerakövetéssel ez rángatósnak hatott. Ott
        a játékos marad a helyén, és csak a kamera úszik át egy olyan nézetre,
        ahol a tó jól látszik előtte.
        """
        if not preserve_player_position:
            self.player.world_x = obstacle_left_edge - stop_distance
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.cinematic_camera_active = True
        if target_player_screen_x is None:
            target_player_screen_x = self.config.left_frame_x
        self.cinematic_camera_target_x = max(0.0, self.player.world_x - target_player_screen_x)
        self.pending_obstacle_text = text
        if self.dialogue.active:
            self.dialogue.hide()

    def trigger_bush_event(self) -> None:
        self.bush_event_triggered = True
        self.start_obstacle_reveal(self.bush.left_edge, self.bush.stop_distance, THORN_TEXT)

    def trigger_lake_event(self) -> None:
        self.lake_event_triggered = True
        # A korábbi, jobban előre néző kamera mellett a régi tó-reveal túl nagy
        # átrendezést okozott. A farkas marad a triggerpontján, a kamera pedig
        # kb. a képernyő 30%-ára úsztatja, így a tó már látszik, de nincs rángás.
        self.start_obstacle_reveal(
            self.lake.left_edge,
            self.lake.stop_distance,
            LAKE_TEXT,
            preserve_player_position=True,
            target_player_screen_x=int(self.config.width * 0.30),
        )

    def centered_camera_x_for_player(self) -> float:
        """Kameraállás, ahol a farkas vízszintesen középen látszik."""
        return max(0.0, self.player.world_x - self.config.center_x)

    def trigger_log_event(self) -> None:
        self.log_event_triggered = True
        # A veszélyjelzésnél nézetet váltunk: a farkas középre kerül.
        # Nem vágunk azonnal a célkamerára, hanem külön, lassabb átmenettel
        # közelítünk rá, hogy ne "rántson" a kép. A farönk csak akkor spawnol,
        # amikor a kamera már beállt erre az új kompozícióra.
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.log_camera_transition_target_x = self.centered_camera_x_for_player()
        self.log_camera_transition_active = True
        self.thought_bubble.show(LOG_WARNING_TEXT)

    def trigger_dark_event(self) -> None:
        self.dark_event_triggered = True
        self.dark_solved = False
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.dark_challenge.start()
        self.thought_bubble.show(DARKNESS_HINT_TEXT)
        if self.dialogue.active:
            self.dialogue.hide()

    def trigger_peak_event(self) -> None:
        """Az 5. jelenet beindítása: aktiváljuk a sziklacsúcsot és intro üzenetet mutatunk.

        A játékos a triggerpontról még tovább kell sétáljon, amíg a kockák alá ér -
        ez ad egy természetes "rácsodálkozás" pillanatot. A láthatatlan fal akadályozza
        meg, hogy egyszerűen elsétáljon a csúcs alatt: csak a kockákon át vezet az út.
        """
        self.peak_event_triggered = True
        self.peak.activate()
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.dialogue.show(PEAK_INTRO_TEXT)

    def set_game_over(self) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.start_animation("idle")
        self.thought_bubble.hide_immediately()
        self.dialogue.show(GAME_OVER_TEXT, hint_text="Esc - kilépés")

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

    def update_log_camera_transition(self, dt: float) -> bool:
        """Finom kameraátmenet a harmadik kihívás elején.

        A normál kamerakövetés 9.0-s smoothness-szel dolgozik, ami jó játék közben,
        de nézetváltásnál túl hirtelennek érződik. Itt külön, lassabb értékkel
        ease-out módon közelítjük a célpozíciót.
        """
        if not self.log_camera_transition_active:
            return False
        target_camera_x = self.log_camera_transition_target_x
        distance = target_camera_x - self.camera_x
        if abs(distance) <= LOG_CAMERA_CENTER_EPSILON:
            self.camera_x = target_camera_x
            self.log_camera_transition_active = False
            self.rolling_log.spawn_from_screen_right(self.camera_x, self.config.width)
            return True

        smooth_factor = 1.0 - math.exp(-LOG_CAMERA_CENTER_SMOOTHNESS * dt)
        self.camera_x += distance * smooth_factor
        return True

    def _target_camera_y(self) -> float:
        """A vertikális kamera célpozíciója.

        Csak a sziklacsúcs jelenetben mozog: amikor a játékos a "deadzone" felett
        van (a talajtól számítva több mint PEAK_VERTICAL_DEADZONE * képernyőmagasság),
        a kamera követi felfelé. Egyébként 0 (nincs scroll).
        """
        if not self.peak_event_triggered:
            return 0.0
        deadzone_height = self.config.height * PEAK_VERTICAL_DEADZONE
        target_screen_y = int(self.config.height * PEAK_VERTICAL_CAMERA_BIAS)
        # Ha a játékos még a deadzone-on belül van (a talaj közelében), nincs scroll.
        if self.player.y >= self.config.ground_top_y - deadzone_height:
            return 0.0
        # Egyébként a kamera úgy csúszik, hogy a játékos kb. a képernyő felső
        # részén-középén legyen, így mindig látszódjon, mi következik felfelé.
        raw = self.player.y - target_screen_y
        # Ne mehessen lefelé (camera_y > 0 lefelé scroll lenne, az itt nem értelmes).
        return min(0.0, raw)

    def _update_camera_y(self, dt: float) -> None:
        target = self._target_camera_y()
        smooth = 1.0 - math.exp(-self.config.camera_smoothness * dt)
        self.camera_y += (target - self.camera_y) * smooth

    def update_camera(self, dt: float) -> None:
        if self.update_cinematic_camera(dt):
            self._update_camera_y(dt)
            return
        if self.update_log_camera_transition(dt):
            self._update_camera_y(dt)
            return
        if self.dialogue.active:
            self._update_camera_y(dt)
            return
        if self.log_event_triggered and not self.log_solved and not self.game_over:
            # A harmadik kihívás alatt a kamera a farkast tartja középen,
            # hogy a jobbról érkező farönk jól látható legyen. Ez már a
            # beállt kamera utáni követés, ezért maradhat fürgébb.
            target_camera_x = self.centered_camera_x_for_player()
            smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
            self.camera_x += (target_camera_x - self.camera_x) * smooth_factor
            self._update_camera_y(dt)
            return
        screen_x = self.player.world_x - self.camera_x
        target_camera_x = self.camera_x
        # JAVÍTÁS: a target a deadzone SZÉLÉN tartja a játékost, nem a center_x-en.
        # Korábban a center_x-re ugrott a target, így a játékos folyamatosan a
        # right_edge_x és center_x között "lebegett" - ez okozta az akadósságot.
        # Most: amint átlép, a target a játékossal együtt halad fix offsettel.
        if screen_x > self.config.right_edge_x:
            target_camera_x = self.player.world_x - self.config.right_edge_x
        elif screen_x < self.config.left_frame_x and self.camera_x > 0:
            target_camera_x = self.player.world_x - self.config.left_frame_x
        target_camera_x = max(0.0, target_camera_x)
        smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
        self.camera_x += (target_camera_x - self.camera_x) * smooth_factor
        self._update_camera_y(dt)

    def handle_mouse_click(self, mouse_pos: tuple[int, int]) -> None:
        """Egér-kattintás kezelése: a bozót weak spotjának keresése."""
        if not self.bush_event_triggered or self.bush_solved:
            return
        if self.dialogue.active or self.cinematic_camera_active:
            return
        mouse_screen_x, mouse_screen_y = mouse_pos
        # A kamera csak X-ben offsetet csinál, Y nem.
        world_x = mouse_screen_x + self.camera_x
        world_y = float(mouse_screen_y)
        if self.bush.is_weak_spot_hit(world_x, world_y):
            self.bush_solved = True
            self.bush.collapse()
            self.thought_bubble.hide_immediately()
            self.dialogue.show(BUSH_COLLAPSE_TEXT)

    def draw_intro(self) -> None:
        if self.state == "about":
            self.menu.draw_about(self.screen, self.music_enabled, self.music_available, self.music_path_found)
        else:
            self.menu.draw_menu(self.screen)
        pygame.display.flip()

    def draw_help(self) -> None:
      if self.state != "playing" or self.dialogue.active:
        return
      if self._help_surface is None or self._help_bg is None:
        return
      self.screen.blit(self._help_bg, (18, 18))
      self.screen.blit(self._help_surface, (29, 25))

    def draw(self) -> None:
        self.background.draw_sky(self.screen, self.camera_y)
        # Sziklacsúcs jelenet háttér-rétege (csillagok + sziluett) - az ég után, minden más elé
        self.peak.draw_silhouette(self.screen, self.camera_x, self.camera_y)
        self.bush.draw(self.screen, self.camera_x)
        self.background.draw_ground(self.screen, self.camera_x, self.camera_y)
        # Tó a ground UTÁN, hogy lefedje a vízfelszín alatti talajt.
        self.lake.draw(self.screen, self.camera_x)
        self.rolling_log.draw(self.screen, self.camera_x)
        # Sziklacsúcs platformjai - a talaj előtt, de a játékos mögött
        self.peak.draw_platforms(self.screen, self.camera_x, self.camera_y)
        self.player.draw(self.screen, self.camera_x, self.camera_y)
        if self.dark_challenge.is_visible():
            self.dark_challenge.draw_trace(self.screen)
            self.dark_challenge.draw_darkness(self.screen, pygame.mouse.get_pos())
        # Vizuális overlay-k a játékos feje fölött:
        player_screen_x = round(self.player.world_x - self.camera_x)
        player_screen_y = round(self.player.y - self.camera_y)
        player_top_y = player_screen_y - SPRITE_HEIGHT
        # Gondolatfelhő anchor: a farkas közepétől kicsit JOBBRA, fej magasságában.
        # A buborék MAGA jobbra-fent jelenik meg, a tail bal-lefelé visszamutat.
        bubble_anchor = (player_screen_x + 5, player_top_y + 35)
        self.thought_bubble.draw(self.screen, bubble_anchor)
        # Willpower-sáv: a fej fölött középen, csak a tó akadálynál látható.
        if self.lake_event_triggered and not self.lake_solved:
            wp_anchor = (player_screen_x, player_top_y - 18)
            self.willpower.draw(self.screen, wp_anchor)
        if (self.state == "playing" and not self.dialogue.active
            and not self.dark_challenge.is_visible()
            and not self.constellation.is_visible()):
            self.draw_help()
        self.draw_music_status()
        # Csillagkép-kihívás: a háttér-csillagok és platformok FÖLÉ rajzolva,
        # de a dialógus ALATT - hogy az emlékezető-szöveg ne legyen takarva.
        self.constellation.draw(self.screen)
        self.dialogue.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            # dt clamp: ha a frame megakad (pl. fókuszváltás miatt), ne ugorjon a játék.
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_FRAME_DT)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                if self.state != "playing":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if self.state == "about":
                                self.state = "menu"
                            else:
                                self.running = False
                        elif self.state == "menu":
                            if event.key in (pygame.K_UP, pygame.K_w):
                                self.menu.move_selection(-1)
                            elif event.key in (pygame.K_DOWN, pygame.K_s):
                                self.menu.move_selection(1)
                            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                                self.activate_menu_option(self.menu.selected_index)
                        elif self.state == "about" and event.key in (pygame.K_RETURN, pygame.K_BACKSPACE):
                            self.state = "menu"
                    elif self.state == "menu" and event.type == pygame.MOUSEMOTION:
                        hovered = self.menu.option_at(event.pos)
                        if hovered is not None:
                            self.menu.selected_index = hovered
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.state == "menu":
                            clicked = self.menu.option_at(event.pos)
                            if clicked is not None:
                                self.menu.selected_index = clicked
                                self.activate_menu_option(clicked)
                        elif self.state == "about":
                            self.state = "menu"
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_RETURN and self.dialogue.active and not self.game_over:
                        self.dialogue.hide()
                    elif event.key == pygame.K_m:
                        self.toggle_music()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                    if self.dark_challenge.handle_event(event):
                        self.dark_solved = True
                        self.thought_bubble.hide_immediately()
                    elif self.constellation.active and not self.constellation.solved:
                        self.constellation.handle_event(event)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_mouse_click(event.pos)

            if self.state != "playing":
                self.draw_intro()
                continue

            self._start_music_if_needed()

            # Akadály-trigger ellenőrzés: csak az aktuálisan releváns akadály.
            if not self.game_over:
                if not self.bush_event_triggered and self.player.world_x >= self.bush.trigger_x():
                    self.trigger_bush_event()
                elif (self.bush_solved and not self.lake_event_triggered
                      and self.player.world_x >= self.lake.trigger_x()):
                    self.trigger_lake_event()
                elif (self.lake_solved and not self.log_event_triggered
                      and self.player.world_x >= LOG_CHALLENGE_WORLD_X):
                    self.trigger_log_event()
                elif (self.log_solved and not self.dark_event_triggered
                      and self.player.world_x >= DARK_CHALLENGE_WORLD_X):
                    self.trigger_dark_event()
                elif (self.dark_solved and not self.peak_event_triggered
                      and self.player.world_x >= PEAK_CHALLENGE_WORLD_X):
                    self.trigger_peak_event()

            blocked = self.movement_blocked()
            self.player.handle_input(dt, self.obstacle_left_edge(), self.controls_enabled(), blocked)
            # Bozót: gondolatfelhő ha próbálkozik mozogni.
            if blocked and self.player.tried_to_move and not self.dialogue.active:
                self.thought_bubble.show(BLOCKED_THOUGHT_TEXT)

            # Sziklacsúcs jelenet: ha a játékos a falnak nyomódik, mutassunk egy hint-et.
            if (self.peak_event_triggered and not self.peak_solved
                and not self.dialogue.active and self.player.tried_to_move
                and self.peak.player_blocked_by_wall(self.player.world_x, self.player.collision_half_width)
                and self.player.on_ground):
                self.thought_bubble.show(PEAK_BLOCKED_HINT_TEXT)

            # Tó: csökönyös jobbra-nyomás számolása.
            self._update_lake_hold(dt)

            self.player.update_physics(dt, floor_y=self.floor_y_for_player())
            self.player.update_animation(dt)
            self.bush.update(dt)
            self.lake.update(dt)
            self.rolling_log.update(dt, self.camera_x)
            if self.rolling_log.active and self.rolling_log.collides_with_player(self.player):
                self.set_game_over()
            if self.rolling_log.solved:
                self.log_solved = True
            self.dark_challenge.update(dt)
            if self.dark_challenge.active and not self.dark_challenge.solved:
                self.thought_bubble.show(DARKNESS_HINT_TEXT)
            if self.dark_challenge.solved:
                self.dark_solved = True
            # Csillagkép-kihívás frissítése
            self.constellation.update(dt)
            # Detektáljuk, ha most fejezte be (drawing → completed_pending átmenet)
            if self.constellation_phase == "drawing" and self.constellation.solved:
                # A megoldás után rövid pulzáló csillag-glow effekt látható,
                # majd jön a befejező dialógus. A pulzálási idő után átkapcsolunk.
                if self.constellation.completion_pulse_t >= 1.4:
                    self.constellation.active = False
                    self.constellation_phase = "completed_pending"
            # Csúcs elérése: a játékos felért, leültetjük és megkezdjük a záró
            # jelenetet. A peak_solved most azt jelzi, hogy felértünk - az ezt
            # követő constellation_phase átmenetek vezetik tovább a jelenetet.
            if (self.peak_event_triggered and not self.peak_solved
                and self.peak.is_on_summit(self.player.world_x, self.player.y, self.player.on_ground)):
                self.peak_solved = True
                self.peak.solved = True
                self.thought_bubble.hide_immediately()
                # Megállítjuk a játékost és átkapcsolunk az ülő képkockára.
                self.player.vx = 0.0
                self.player.vy = 0.0
                self.player.movement_pressed = False
                self.player.was_movement_pressed = False
                # A megfelelő irányú ülés: a játékos arrafelé néz, amerre éppen
                # a csúcs felé haladt - ezt a `facing_right` már tartja.
                self.player.start_animation("sitting")
                self.constellation_phase = "sit"
                self.dialogue.show(PEAK_SUCCESS_TEXT)
            # Constellation fázis-átmenetek: a dialógus záródásakor lépünk tovább.
            self._update_constellation_phase()
            self.thought_bubble.update(dt)
            # A willpower-sáv csak akkor "él", ha aktív tó-akadály van.
            wp_target = (self.lake_hold_timer / LAKE_HOLD_DURATION
                         if (self.lake_event_triggered and not self.lake_solved)
                         else 0.0)
            self.willpower.update(wp_target, dt)
            self.update_camera(dt)
            self.draw()
        self._stop_music()
        pygame.quit()

    def _update_constellation_phase(self) -> None:
        """Vezeti a 6. (záró) jelenet fázis-átmeneteit.

        A fázisok mindig egy dialógus-bezárás után lépnek tovább. A
        `peak_solved=True` az első ilyen átmenet előfeltétele (csak akkor
        kezdődik, ha a játékos felért és leült).
        """
        if not self.peak_solved:
            return
        if self.dialogue.active:
            return
        if self.constellation_phase == "sit":
            # Az első dialógust ("Mostmár tisztán látom...") a játékos becsukta.
            # Most jön a memory-szöveg.
            self.dialogue.show(CONSTELLATION_INTRO_TEXT)
            self.constellation_phase = "memory"
            return
        if self.constellation_phase == "memory":
            # A memory-szöveget is elolvasta - induljon a csillag-rajzolás.
            self.constellation.start()
            self.constellation_phase = "drawing"
            return
        if self.constellation_phase == "drawing":
            # A drawing fázisból a constellation.solved figyelése lépteti tovább
            # (a run() ciklusban). Itt nincs teendő.
            return
        if self.constellation_phase == "completed_pending":
            # A megoldás után rövid pulzáló glow látszott, most a befejező szöveg.
            self.dialogue.show(CONSTELLATION_COMPLETE_TEXT)
            self.constellation_phase = "done"
            return

    def _update_lake_hold(self, dt: float) -> None:
        """A tó-puzzle "csökönyös jobbra-nyomás" számláló kezelése.

        Csak akkor ticelünk, ha:
          - aktív a tó-akadály ÉS még nem oldódott meg,
          - a játékos fizikailag a tó-élnek nyomódik (nem csak közelít),
          - a játékos jobbra-irányú gombot tartja,
          - a kontrollok engedélyezettek (nincs aktív dialógus / cinematic).

        Elengedéskor gyorsan visszaesik (LAKE_HOLD_DECAY), így TÉNYLEG
        folyamatosan kell tartani 5 másodpercig - ahogy a "csökönyös" szó
        sugallja.
        """
        if not self.lake_event_triggered or self.lake_solved:
            self.lake_hold_timer = 0.0
            return
        if not self.controls_enabled():
            return  # Dialógus alatt sem ticeljen, sem ne csökkenjen.

        keys = pygame.key.get_pressed()
        holding_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if holding_right and self.is_pressed_against_lake():
            self.lake_hold_timer = min(LAKE_HOLD_DURATION, self.lake_hold_timer + dt)
            if self.lake_hold_timer >= LAKE_HOLD_DURATION:
                self.lake_solved = True
                self.lake.solve()
                self.dialogue.show(LAKE_SOLVED_TEXT)
        else:
            self.lake_hold_timer = max(0.0, self.lake_hold_timer - dt * LAKE_HOLD_DECAY)


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
