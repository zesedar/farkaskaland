"""3. kihívás: a képernyő jobb széléről beguruló farönk, amit át kell ugrani."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from constants import (
    LOG_COLLISION_PADDING_X,
    LOG_RADIUS_BASE,
    LOG_SAFE_CLEARANCE_EXTRA,
    LOG_SPEED,
)

if TYPE_CHECKING:
    from player import Player


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

    def collides_with_player(self, player: "Player") -> bool:
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
