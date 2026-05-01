"""2. kihívás: tó, amit csak csökönyösen-jobbra-tartással lehet átlépni.
A WillpowerIndicator vizuális visszajelzést ad a haladásról."""
from __future__ import annotations

import random

import pygame

from world_config import WorldConfig


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
