from pathlib import Path
import pygame

# Ablak
WIDTH, HEIGHT = 960, 540
FPS = 60

# Talaj
GROUND_Y = 430

# Farkas mozgás
PLAYER_SPEED = 280
SPRITE_HEIGHT = 120

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


def load_frame_file(path: Path, target_height: int) -> pygame.Surface:
    """Betölt egy frame-képet, eltávolítja a zöld hátteret, majd átméretezi."""
    frame = pygame.image.load(str(path)).convert_alpha()

    # Ezt még méretezés előtt csináljuk, hogy ne keletkezzen zöld szél a sprite körül.
    frame = remove_green_transparency(frame)

    scale = target_height / frame.get_height()
    new_width = int(frame.get_width() * scale)
    return pygame.transform.smoothscale(frame, (new_width, target_height))


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


def draw_static_background(screen: pygame.Surface) -> None:
    # Ég
    screen.fill((136, 207, 255))

    # Nap
    pygame.draw.circle(screen, (255, 234, 128), (820, 80), 38)

    # Felhők
    for x, y in [(120, 85), (420, 70), (680, 125)]:
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 26)
        pygame.draw.circle(screen, (255, 255, 255), (x + 30, y - 8), 32)
        pygame.draw.circle(screen, (255, 255, 255), (x + 65, y), 24)
        pygame.draw.rect(screen, (255, 255, 255), (x, y, 65, 25), border_radius=12)

    # Dombok
    pygame.draw.circle(screen, (99, 198, 119), (210, 430), 170)
    pygame.draw.circle(screen, (75, 176, 105), (550, 450), 210)
    pygame.draw.circle(screen, (110, 210, 125), (880, 430), 160)

    # Talaj
    pygame.draw.rect(screen, (93, 191, 80), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.rect(screen, (67, 151, 65), (0, GROUND_Y + 18, WIDTH, HEIGHT - GROUND_Y - 18))

    # Csempe minta
    tile = 48
    for x in range(0, WIDTH, tile):
        pygame.draw.line(screen, (53, 130, 55), (x, GROUND_Y + 18), (x, HEIGHT), 2)

    for y in range(GROUND_Y + 18, HEIGHT, tile):
        pygame.draw.line(screen, (53, 130, 55), (0, y), (WIDTH, y), 2)

    # Dekorációs platformok
    for rect in [(120, 330, 120, 32), (640, 300, 150, 32)]:
        pygame.draw.rect(screen, (217, 151, 78), rect, border_radius=4)
        pygame.draw.rect(screen, (130, 87, 49), rect, 3, border_radius=4)


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

        self.x = 180.0
        self.y = float(GROUND_Y)

        self.vx = 0.0
        self.facing_right = True

        self.movement_pressed = False
        self.was_movement_pressed = False

        # Lehetséges állapotok: "idle", "run", "stop".
        self.animation_state = "idle"
        self.animation_timer = 0.0

    def handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()

        moving_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        moving_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        self.movement_pressed = moving_left or moving_right

        self.vx = 0.0

        if moving_left:
            self.vx = -PLAYER_SPEED
            self.facing_right = False

        if moving_right:
            self.vx = PLAYER_SPEED
            self.facing_right = True

        self.x += self.vx * dt
        self.x = max(55, min(WIDTH - 55, self.x))

    def start_animation(self, state: str) -> None:
        """Új animációs állapot indítása mindig az adott animáció első frame-jéről."""
        if self.animation_state != state:
            self.animation_state = state
            self.animation_timer = 0.0

    def update_animation(self, dt: float) -> None:
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
        if self.animation_state == "run":
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
        # Árnyék
        shadow_rect = pygame.Rect(0, 0, 88, 16)
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

    font = pygame.font.SysFont(None, 26)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        player.handle_input(dt)
        player.update_animation(dt)

        draw_static_background(screen)
        player.draw(screen)

        help_text = font.render(
            "Move: A/D or ←/→    Quit: close window",
            True,
            (30, 40, 45),
        )
        screen.blit(help_text, (22, 18))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
