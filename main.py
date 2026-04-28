from pathlib import Path
from collections import deque
import random
import pygame

# Ablak
WIDTH, HEIGHT = 960, 540
FPS = 60

# Talaj
GROUND_Y = 430

# Farkas mozgás
PLAYER_SPEED = 280

# A játékbeli méret. Ha nagyobb/kisebb farkast szeretnél a pályán,
# elég ezt az egy értéket állítani.
SPRITE_HEIGHT = 120

# A mellékelt alap stance kép, wolf_run_0063.png, forrásmagassága 328 px.
# Az ugrás képkockáit ehhez az eredeti mérethez igazítjuk, ezért nem lesznek kicsik.
REFERENCE_STANCE_SOURCE_HEIGHT = 328

LEFT_EDGE_X = 55
RIGHT_EDGE_X = WIDTH - 55
BACKGROUND_SEGMENT_WIDTH = WIDTH

# Ugrás fizika
# A y koordináta lefelé nő, ezért az ugrás induló sebessége negatív.
# Kicsit magasabb és lebegősebb ugrásra hangolva.
JUMP_SPEED = 780
GRAVITY = 1500
MAX_FALL_SPEED = 1100

# Ugrás animáció: 2 sor x 4 oszlopos sprite sheet.
# Mentsd a feltöltött ugrás képet ide: assets/wolf_jump_sheet.png
JUMP_SHEET_FILENAME = "wolf_jump_sheet.png"
JUMP_SHEET_COLUMNS = 4
JUMP_SHEET_ROWS = 2
JUMP_FRAME_TIME = 0.13

# Külön képfájlok adatai
# A képek legyenek itt: assets/
# Példa: assets/wolf_run_0001.png, assets/wolf_run_0002.png, ...
# Logikai frame-ek:
# 0-43: futás animáció
# 44-62: megállás animáció
# Mivel a fájlnevek 1-től indulnak:
# 0. frame  -> wolf_run_0001.png
# 43. frame -> wolf_run_0044.png
# 44. frame -> wolf_run_0045.png
# 62. frame -> wolf_run_0063.png
FRAME_FILE_PREFIX = "wolf_run_"
FRAME_FILE_EXTENSION = ".png"
FRAME_FILE_DIGITS = 4
TOTAL_FRAME_COUNT = 63

RUN_START_FRAME = 0
RUN_END_FRAME = 43
STOP_START_FRAME = 44
STOP_END_FRAME = 62
ANIMATION_FRAME_TIME = 0.07

# Ezek a fájlok kicsit zavaróak lassan lejátszva, ezért csak őket gyorsítjuk.
# Fontos: ez fájlnév szerinti számozás, tehát wolf_run_0052.png - wolf_run_0059.png.
FAST_STOP_FILE_START = 52
FAST_STOP_FILE_END = 59
FAST_STOP_FRAME_TIME = 0.002

# A képeken a zöld háttér jelöli az átlátszó részeket.
# Nem csak egyetlen pontos RGB-értéket kezel, hanem a zöldes árnyalatokat is.
GREEN_ALPHA_MIN_GREEN = 70
GREEN_ALPHA_DOMINANCE = 28


def is_transparency_green(r: int, g: int, b: int, a: int) -> bool:
    """Igaz, ha a pixel zöld háttérszín, amelyet átlátszóvá kell tenni."""
    if a == 0:
        return False

    return (
        g >= GREEN_ALPHA_MIN_GREEN
        and g >= r + GREEN_ALPHA_DOMINANCE
        and g >= b + GREEN_ALPHA_DOMINANCE
    )


def remove_green_transparency(surface: pygame.Surface) -> pygame.Surface:
    """A zöld háttérpixeleket teljesen átlátszóvá alakítja."""
    surface = surface.convert_alpha()
    width, height = surface.get_size()

    surface.lock()
    try:
        for y in range(height):
            for x in range(width):
                r, g, b, a = surface.get_at((x, y))

                if is_transparency_green(r, g, b, a):
                    # A színt is nullázzuk, hogy méretezésnél ne maradjon zöld perem.
                    surface.set_at((x, y), (0, 0, 0, 0))
    finally:
        surface.unlock()

    return surface


def is_light_background(r: int, g: int, b: int, a: int) -> bool:
    """Igaz, ha egy világos háttér/grid pixel átlátszóvá alakítható.

    Ezt csak a sprite sheet széleiről induló flood fill használja, ezért a farkas
    világos szőre nem tűnik el, ha nem ér hozzá a kép széléhez.

    A küszöb szándékosan 210: így a halványszürke rácsvonalak is eltűnnek,
    nem marad körülöttük nagy üres képkocka, amitől az ugrás animáció kicsi lenne.
    """
    if a == 0:
        return False

    return r >= 210 and g >= 210 and b >= 210


def remove_light_background_from_edges(surface: pygame.Surface) -> pygame.Surface:
    """A világos háttért csak a kép szélei felől törli ki.

    Ez a feltöltött ugrás sprite sheethez kell, mert fehér háttere és halvány
    rácsvonalai vannak. A kitöltés csak a széllel összefüggő világos pixeleket
    teszi átlátszóvá.
    """
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
    """Levágja az átlátszó üres terület nagy részét a sprite körül."""
    rect = surface.get_bounding_rect(min_alpha=1)

    if rect.width <= 0 or rect.height <= 0:
        return surface

    rect = rect.inflate(padding * 2, padding * 2)
    rect.clamp_ip(surface.get_rect())

    cropped = pygame.Surface(rect.size, pygame.SRCALPHA)
    cropped.blit(surface, (0, 0), rect)
    return cropped


def scale_surface_to_height(surface: pygame.Surface, target_height: int) -> pygame.Surface:
    """Arányosan átméretez egy felületet a megadott magasságra."""
    scale = target_height / surface.get_height()
    new_width = max(1, int(surface.get_width() * scale))
    return pygame.transform.smoothscale(surface, (new_width, target_height))


def scale_surface_by_factor(surface: pygame.Surface, scale: float) -> pygame.Surface:
    """Arányosan átméretez egy felületet fix skálával.

    Az ugrás animációnál ezt használjuk, nem pedig azt, hogy minden képkocka
    külön-külön ugyanakkora magasságú legyen. Így a nyújtott/csukott ugró pózok
    megőrzik az eredeti arányukat az alap stance méretéhez képest.
    """
    new_width = max(1, int(surface.get_width() * scale))
    new_height = max(1, int(surface.get_height() * scale))
    return pygame.transform.smoothscale(surface, (new_width, new_height))


def load_frame_file(path: Path, target_height: int) -> pygame.Surface:
    """Betölt egy frame-képet, eltávolítja a zöld hátteret, majd átméretezi."""
    frame = pygame.image.load(str(path)).convert_alpha()

    # Ezt még méretezés előtt csináljuk, hogy ne keletkezzen zöld szél a sprite körül.
    frame = remove_green_transparency(frame)

    return scale_surface_to_height(frame, target_height)


def load_sprite_sheet_grid(
    path: Path,
    columns: int,
    rows: int,
    target_height: int,
    reference_source_height: int,
) -> list[pygame.Surface]:
    """Betölt egy rácsos sprite sheetet soronként, balról jobbra.

    A feltöltött ugrás képen 4 oszlop és 2 sor van, ezért abból 8 képkocka lesz.
    Ha nincs ilyen fájl az assets mappában, üres listát ad vissza, így a játék
    továbbra is elindul a futó képkockákból képzett tartalék animációval.

    Fontos: az ugrás frame-eket nem külön-külön 120 px magasra nyújtjuk,
    hanem az alap stance forrásmagasságához képest skálázzuk. Ettől a jump
    animáció ugyanakkora karakter-méretű lesz, mint a futás/állás.
    """
    if not path.exists():
        return []

    sheet = pygame.image.load(str(path)).convert_alpha()
    sheet_width, sheet_height = sheet.get_size()
    cell_width = sheet_width // columns
    cell_height = sheet_height // rows

    frames: list[pygame.Surface] = []

    for row in range(rows):
        for column in range(columns):
            # 1 pixeles belső margóval vágunk, hogy a rácsvonal ne kerüljön a sprite-ba.
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
    """Betölti a külön fájlokban lévő képkockákat 1-től számozva.

    Példa frame_count=63 esetén:
    wolf_run_0001.png ... wolf_run_0063.png
    """
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
    """Visszaadja, hogy eltelt idő alapján melyik frame-et kell mutatni.

    Ezt a megállás animációnál használjuk, mert ott egyes képkockák gyorsabbak.
    """
    elapsed = 0.0

    for frame_index, frame_time in enumerate(frame_times):
        elapsed += frame_time

        if animation_timer < elapsed:
            return frame_index

    return len(frame_times) - 1


def create_stop_frame_times() -> list[float]:
    """Megállás animáció frame-idői.

    A wolf_run_0052.png - wolf_run_0059.png fájlokat gyorsabban játsszuk le,
    a többi megállás frame marad az eredeti tempón.
    """
    frame_times: list[float] = []

    for logical_frame in range(STOP_START_FRAME, STOP_END_FRAME + 1):
        file_number = logical_frame + 1

        if FAST_STOP_FILE_START <= file_number <= FAST_STOP_FILE_END:
            frame_times.append(FAST_STOP_FRAME_TIME)
        else:
            frame_times.append(ANIMATION_FRAME_TIME)

    return frame_times


def draw_cloud(screen: pygame.Surface, x: int, y: int, size: int) -> None:
    """Egyszerű felhő rajzolása tetszőleges pozícióra."""
    pygame.draw.circle(screen, (255, 255, 255), (x, y), size)
    pygame.draw.circle(screen, (255, 255, 255), (x + int(size * 1.15), y - int(size * 0.30)), int(size * 1.20))
    pygame.draw.circle(screen, (255, 255, 255), (x + int(size * 2.40), y), int(size * 0.90))
    pygame.draw.rect(
        screen,
        (255, 255, 255),
        (x, y, int(size * 2.45), int(size * 0.95)),
        border_radius=max(6, size // 2),
    )


def draw_platform(screen: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.rect(screen, (217, 151, 78), rect, border_radius=4)
    pygame.draw.rect(screen, (130, 87, 49), rect, 3, border_radius=4)


class ScrollingBackground:
    """Jobbra végtelenül gördülő, szakaszonként véletlen háttér.

    A háttér csak jobbra halad. Bal oldalon nem scrollozunk vissza, ezért a farkas
    balra egyszerűen a képernyő bal szélén megáll.
    """

    def __init__(self) -> None:
        self.scroll_x = 0.0
        self.segment_width = BACKGROUND_SEGMENT_WIDTH
        self.segments: dict[int, dict[str, object]] = {}
        self._ensure_visible_segments()

    def advance(self, distance: float) -> None:
        """Ennyivel tolja tovább a világot jobbra."""
        if distance <= 0:
            return

        self.scroll_x += distance
        self._ensure_visible_segments()

    def _ensure_visible_segments(self) -> None:
        first_index = int(self.scroll_x // self.segment_width)

        # Mindig legyen előre pár képernyőnyi háttér előkészítve.
        for segment_index in range(first_index, first_index + 4):
            if segment_index not in self.segments:
                self.segments[segment_index] = self._create_segment(segment_index)

        # Régi szakaszokat kidobjuk, hogy hosszú futásnál se nőjön végtelenül a memóriahasználat.
        for segment_index in list(self.segments):
            if segment_index < first_index - 1 or segment_index > first_index + 4:
                del self.segments[segment_index]

    def _create_segment(self, segment_index: int) -> dict[str, object]:
        # Stabil "véletlen": ugyanaz a szakasz mindig ugyanúgy néz ki, de minden új szakasz más.
        rng = random.Random(10_000 + segment_index * 7919)

        sky_colors = [
            (136, 207, 255),
            (126, 199, 250),
            (150, 216, 255),
            (158, 210, 245),
        ]
        ground_colors = [
            ((93, 191, 80), (67, 151, 65)),
            ((101, 184, 78), (74, 145, 63)),
            ((83, 178, 88), (58, 137, 67)),
        ]
        hill_colors = [(99, 198, 119), (75, 176, 105), (110, 210, 125), (92, 185, 116)]

        clouds = []
        for _ in range(rng.randint(2, 5)):
            clouds.append(
                (
                    rng.randint(-40, self.segment_width - 90),
                    rng.randint(55, 145),
                    rng.randint(18, 34),
                )
            )

        hills = []
        for _ in range(rng.randint(2, 4)):
            hills.append(
                (
                    rng.randint(-80, self.segment_width + 80),
                    rng.randint(420, 470),
                    rng.randint(120, 230),
                    rng.choice(hill_colors),
                )
            )

        platforms = []
        for _ in range(rng.randint(1, 3)):
            platforms.append(
                pygame.Rect(
                    rng.randint(70, self.segment_width - 220),
                    rng.randint(285, 355),
                    rng.randint(100, 170),
                    32,
                )
            )

        return {
            "sky_color": rng.choice(sky_colors),
            "ground_colors": rng.choice(ground_colors),
            "sun": (rng.randint(700, 880), rng.randint(65, 105), rng.randint(30, 44)),
            "clouds": clouds,
            "hills": hills,
            "platforms": platforms,
        }

    def draw(self, screen: pygame.Surface) -> None:
        first_index = int(self.scroll_x // self.segment_width)
        tile = 48

        for segment_index in range(first_index, first_index + 3):
            segment = self.segments[segment_index]
            base_x = int(segment_index * self.segment_width - self.scroll_x)

            sky_color = segment["sky_color"]
            ground_top, ground_bottom = segment["ground_colors"]
            sun_x, sun_y, sun_radius = segment["sun"]

            pygame.draw.rect(screen, sky_color, (base_x, 0, self.segment_width, HEIGHT))
            pygame.draw.circle(screen, (255, 234, 128), (base_x + sun_x, sun_y), sun_radius)

            for cloud_x, cloud_y, cloud_size in segment["clouds"]:
                draw_cloud(screen, base_x + cloud_x, cloud_y, cloud_size)

            for hill_x, hill_y, hill_radius, hill_color in segment["hills"]:
                pygame.draw.circle(screen, hill_color, (base_x + hill_x, hill_y), hill_radius)

            pygame.draw.rect(screen, ground_top, (base_x, GROUND_Y, self.segment_width, HEIGHT - GROUND_Y))
            pygame.draw.rect(
                screen,
                ground_bottom,
                (base_x, GROUND_Y + 18, self.segment_width, HEIGHT - GROUND_Y - 18),
            )

            for x in range(0, self.segment_width + tile, tile):
                line_x = base_x + x
                pygame.draw.line(screen, (53, 130, 55), (line_x, GROUND_Y + 18), (line_x, HEIGHT), 2)

            for y in range(GROUND_Y + 18, HEIGHT, tile):
                pygame.draw.line(screen, (53, 130, 55), (base_x, y), (base_x + self.segment_width, y), 2)

            for platform in segment["platforms"]:
                screen_rect = platform.move(base_x, 0)
                draw_platform(screen, screen_rect)

class Player:
    def __init__(self) -> None:
        asset_dir = Path(__file__).parent / "assets"

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
                f"Csak {len(frames)} képkocka lett betöltve. "
                f"Legalább {needed_frame_count} kell, mert a kód a 0-{STOP_END_FRAME} frame-eket használja."
            )

        # 0-43: futás. Fájlnév szerint ez wolf_run_0001.png - wolf_run_0044.png.
        self.run_frames = frames[RUN_START_FRAME : RUN_END_FRAME + 1]

        # 44-62: megállás. Fájlnév szerint ez wolf_run_0045.png - wolf_run_0063.png.
        self.stop_frames = frames[STOP_START_FRAME : STOP_END_FRAME + 1]
        self.stop_frame_times = create_stop_frame_times()

        # Ugrás: a feltöltött 2x4-es sprite sheetből 8 frame-et vágunk ki.
        self.jump_frames = load_sprite_sheet_grid(
            path=asset_dir / JUMP_SHEET_FILENAME,
            columns=JUMP_SHEET_COLUMNS,
            rows=JUMP_SHEET_ROWS,
            target_height=SPRITE_HEIGHT,
            reference_source_height=REFERENCE_STANCE_SOURCE_HEIGHT,
        )

        if not self.jump_frames:
            # Tartalék, hogy a játék akkor is fusson, ha még nincs bemásolva a jump sheet.
            self.jump_frames = [
                self.run_frames[0],
                self.run_frames[len(self.run_frames) // 4],
                self.run_frames[len(self.run_frames) // 2],
                self.run_frames[-1],
            ]

        self.x = 180.0
        self.y = float(GROUND_Y)

        self.vx = 0.0
        self.vy = 0.0
        self.facing_right = True
        self.on_ground = True

        self.movement_pressed = False
        self.was_movement_pressed = False
        self.jump_pressed_last_frame = False

        # Lehetséges állapotok: "idle", "run", "stop", "jump".
        self.animation_state = "idle"
        self.animation_timer = 0.0

    def handle_input(self, dt: float, background: ScrollingBackground) -> None:
        keys = pygame.key.get_pressed()

        moving_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        moving_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        jump_pressed = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        self.movement_pressed = moving_left or moving_right

        self.vx = 0.0

        if moving_left:
            self.vx = -PLAYER_SPEED
            self.facing_right = False

        if moving_right:
            self.vx = PLAYER_SPEED
            self.facing_right = True

        # Ugrás csak akkor indulhat, amikor a gombot most nyomták le és a farkas talajon van.
        # Így a Space/W/↑ nyomva tartása nem indít végtelen ugrást.
        if jump_pressed and not self.jump_pressed_last_frame and self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False
            self.start_animation("jump")

        self.jump_pressed_last_frame = jump_pressed

        movement = self.vx * dt

        if self.vx > 0:
            next_x = self.x + movement

            if next_x > RIGHT_EDGE_X:
                # A farkas a jobb szélen marad, a felesleges mozgás pedig továbbtolja a világot.
                background.advance(next_x - RIGHT_EDGE_X)
                self.x = RIGHT_EDGE_X
            else:
                self.x = next_x
        elif self.vx < 0:
            # Bal oldalon nincs végtelen világ: egyszerűen megáll a bal szélnél.
            self.x = max(LEFT_EDGE_X, self.x + movement)

    def update_physics(self, dt: float) -> None:
        """Egyszerű gravitáció és talajra érkezés kezelése."""
        if self.on_ground:
            return

        self.vy = min(MAX_FALL_SPEED, self.vy + GRAVITY * dt)
        self.y += self.vy * dt

        if self.y >= GROUND_Y:
            self.y = float(GROUND_Y)
            self.vy = 0.0
            self.on_ground = True

    def start_animation(self, state: str) -> None:
        """Új animációs állapot indítása mindig az adott animáció első frame-jéről."""
        if self.animation_state != state:
            self.animation_state = state
            self.animation_timer = 0.0

    def update_animation(self, dt: float) -> None:
        if not self.on_ground:
            # Levegőben mindig az ugrás animáció aktív.
            self.start_animation("jump")
            self.animation_timer += dt
            self.was_movement_pressed = self.movement_pressed
            return

        if self.animation_state == "jump":
            # Földet érés után térjen vissza futásba vagy alapállásba.
            if self.movement_pressed:
                self.start_animation("run")
            else:
                self.start_animation("idle")

        if self.movement_pressed:
            # A gomb nyomva van: a 0-43 futás animáció menjen végig, majd loopoljon.
            self.start_animation("run")
            self.animation_timer += dt
        else:
            # Pont most engedte fel a gombot: induljon el a 44-62 megállás animáció.
            if self.was_movement_pressed:
                self.start_animation("stop")

            if self.animation_state == "stop":
                self.animation_timer += dt

                stop_duration = sum(self.stop_frame_times)
                if self.animation_timer >= stop_duration:
                    # A megállás animáció egyszer végigment, maradjon az utolsó frame-en.
                    self.animation_timer = stop_duration
                    self.animation_state = "idle"

        self.was_movement_pressed = self.movement_pressed

    def current_image(self) -> pygame.Surface:
        if self.animation_state == "jump":
            # Az ugrás animáció egyszer fut végig; ha még levegőben van, az utolsó frame marad.
            frame_index = min(
                int(self.animation_timer / JUMP_FRAME_TIME),
                len(self.jump_frames) - 1,
            )
            image = self.jump_frames[frame_index]
        elif self.animation_state == "run":
            # 0-43: végigmegy, majd újraindul, amíg nyomva van a gomb.
            frame_index = int(self.animation_timer / ANIMATION_FRAME_TIME) % len(self.run_frames)
            image = self.run_frames[frame_index]
        elif self.animation_state == "stop":
            # 44-62: egyszer végigmegy, nem loopol.
            # A wolf_run_0052.png - wolf_run_0059.png fájlok gyorsabban mennek át.
            frame_index = get_frame_index_from_timer(self.animation_timer, self.stop_frame_times)
            image = self.stop_frames[frame_index]
        else:
            # Ha nincs input és a megállás animáció már lement, az utolsó megálló frame marad.
            image = self.stop_frames[-1]

        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)

        return image

    def draw(self, screen: pygame.Surface) -> None:
        # Árnyék: ugrás közben kisebb lesz, de a talajon marad.
        height_above_ground = max(0.0, GROUND_Y - self.y)
        shadow_scale = max(0.42, 1.0 - height_above_ground / 270.0)
        shadow_rect = pygame.Rect(0, 0, int(88 * shadow_scale), int(16 * shadow_scale))
        shadow_rect.center = (int(self.x), GROUND_Y + 7)
        pygame.draw.ellipse(screen, (62, 92, 65), shadow_rect)

        image = self.current_image()
        rect = image.get_rect(midbottom=(int(self.x), int(self.y)))
        screen.blit(image, rect)


def main() -> None:
    pygame.init()

    pygame.display.set_caption("Little Wolf Run Demo")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    player = Player()
    background = ScrollingBackground()

    font = pygame.font.SysFont(None, 26)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        player.handle_input(dt, background)
        player.update_physics(dt)
        player.update_animation(dt)

        background.draw(screen)
        player.draw(screen)

        help_text = font.render(
            "Move: A/D or ←/→    Jump: Space/W/↑    Right edge: infinite random background",
            True,
            (30, 40, 45),
        )
        screen.blit(help_text, (22, 18))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
