"""1. kihívás: tövises bozót, amit egy random pozícióba helyezett weak spotra
kattintással lehet összeomlasztani."""
from __future__ import annotations

import random

import pygame

from constants import (
    BUSH_COLLAPSE_RATE,
    WEAK_SPOT_MARKER_COLOR,
    WEAK_SPOT_MIN_ALPHA,
    WEAK_SPOT_RADIUS,
)


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
