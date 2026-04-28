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

# Sprite sheet adatok
# A kép legyen itt: assets/wolf_run_sheet.png
# 4 oszlop, 3 sor, 256x256 px képkockák
# Ezeket nem kell módosítani, ha a wolf_run_sheet.png tényleg 1024x768 px.
RUN_SHEET_COLUMNS = 4
RUN_SHEET_ROWS = 3
RUN_FRAME_WIDTH = 256
RUN_FRAME_HEIGHT = 256

# A sprite sheeten a zöld háttér jelöli az átlátszó részeket.
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


def load_sprite_sheet(
    path: Path,
    frame_width: int,
    frame_height: int,
    columns: int,
    rows: int,
    target_height: int,
) -> list[pygame.Surface]:
    sheet = pygame.image.load(str(path)).convert_alpha()

    expected_width = frame_width * columns
    expected_height = frame_height * rows

    if sheet.get_width() != expected_width or sheet.get_height() != expected_height:
        raise ValueError(
            f"Hibás sprite sheet méret: {sheet.get_width()}x{sheet.get_height()} px. "
            f"Elvárt méret: {expected_width}x{expected_height} px."
        )

    frames = []

    for row in range(rows):
        for col in range(columns):
            x = col * frame_width
            y = row * frame_height

            frame = sheet.subsurface(
                pygame.Rect(x, y, frame_width, frame_height)
            ).copy()

            # A wolf_run_sheet.png-ben a zöld árnyalatok jelentik az átlátszóságot.
            # Ezt még méretezés előtt csináljuk, hogy ne keletkezzen zöld szél a sprite körül.
            frame = remove_green_transparency(frame)

            scale = target_height / frame.get_height()
            new_width = int(frame.get_width() * scale)
            frame = pygame.transform.smoothscale(frame, (new_width, target_height))

            frames.append(frame)

    return frames


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

        self.run_frames = load_sprite_sheet(
            asset_dir / "wolf_run_sheet.png",
            frame_width=RUN_FRAME_WIDTH,
            frame_height=RUN_FRAME_HEIGHT,
            columns=RUN_SHEET_COLUMNS,
            rows=RUN_SHEET_ROWS,
            target_height=SPRITE_HEIGHT,
        )

        # Álló helyzetnek az első képkockát használjuk.
        self.idle_frames = [
            self.run_frames[0],
        ]

        self.x = 180.0
        self.y = float(GROUND_Y)

        self.vx = 0.0
        self.facing_right = True

        self.run_timer = 0.0
        self.idle_timer = 0.0

    def handle_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()

        moving_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        moving_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        self.vx = 0.0

        if moving_left:
            self.vx = -PLAYER_SPEED
            self.facing_right = False

        if moving_right:
            self.vx = PLAYER_SPEED
            self.facing_right = True

        self.x += self.vx * dt
        self.x = max(55, min(WIDTH - 55, self.x))

    def update_animation(self, dt: float) -> None:
        if self.is_moving():
            self.run_timer += dt
            self.idle_timer = 0.0
        else:
            self.idle_timer += dt
            self.run_timer = 0.0

    def is_moving(self) -> bool:
        return abs(self.vx) > 1

    def current_image(self) -> pygame.Surface:
        if self.is_moving():
            frame_index = int(self.run_timer / 0.07) % len(self.run_frames)
            image = self.run_frames[frame_index]
        else:
            frame_index = int(self.idle_timer / 0.45) % len(self.idle_frames)
            image = self.idle_frames[frame_index]

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
