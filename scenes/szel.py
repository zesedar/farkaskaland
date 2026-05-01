"""7. jelenet: Szél - jobbról érkező ágak és a barlang megtalálása."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from constants import (
    SPRITE_HEIGHT,
    WIND_BRANCH_SPAWN_MAX,
    WIND_BRANCH_SPAWN_MIN,
    WIND_BRANCH_SPEED,
    WIND_BRANCH_THICKNESS_BASE,
    WIND_CAVE_DISTANCE,
    WIND_CAVE_HEIGHT_BASE,
    WIND_CAVE_REACH_TOLERANCE,
    WIND_CAVE_WIDTH_BASE,
    WIND_COLLISION_PADDING_X,
    WIND_FIRST_BRANCH_DELAY,
    WIND_HIGH_BRANCH_LENGTH_BASE,
    WIND_HIGH_BRANCH_MAX_OFFSET_BASE,
    WIND_HIGH_BRANCH_MIN_OFFSET_BASE,
    WIND_LOW_BRANCH_LENGTH_BASE,
)

if TYPE_CHECKING:
    from player import Player


@dataclass
class WindBranch:
    """Egy jobbról balra sodródó ág.

    kind:
      - "low": talajközeli ág, át kell ugrani
      - "high": magas ág, nem szabad beleugrani
    """

    kind: str
    world_x: float
    center_y: float
    length: int
    thickness: int
    speed: float
    angle_deg: float
    leaf_count: int
    phase: float

    def collision_rect(self) -> pygame.Rect:
        return pygame.Rect(
            round(self.world_x - self.length * 0.5),
            round(self.center_y - self.thickness * 0.5),
            self.length,
            self.thickness,
        )

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        screen_x = self.world_x - camera_x
        if screen_x < -self.length - 80 or screen_x > screen.get_width() + self.length + 80:
            return

        wobble_y = math.sin(self.phase) * 3.0
        center = (screen_x, self.center_y - camera_y + wobble_y)
        angle = math.radians(self.angle_deg)
        dx = math.cos(angle) * self.length * 0.5
        dy = math.sin(angle) * self.length * 0.5
        start = (round(center[0] - dx), round(center[1] - dy))
        end = (round(center[0] + dx), round(center[1] + dy))

        bark_dark = (63, 38, 24)
        bark_mid = (113, 72, 39)
        twig = (82, 50, 30)
        leaf_dark = (45, 97, 51)
        leaf_light = (83, 132, 64)

        pygame.draw.line(screen, bark_dark, start, end, self.thickness + 4)
        pygame.draw.line(screen, bark_mid, start, end, self.thickness)

        for i in range(3):
            t = (i + 1) / 4
            bx = start[0] + (end[0] - start[0]) * t
            by = start[1] + (end[1] - start[1]) * t
            side = -1 if i % 2 else 1
            twig_len = 18 + i * 5
            twig_angle = angle + side * 0.85
            tx = bx + math.cos(twig_angle) * twig_len
            ty = by + math.sin(twig_angle) * twig_len
            pygame.draw.line(
                screen,
                twig,
                (round(bx), round(by)),
                (round(tx), round(ty)),
                max(3, self.thickness // 4),
            )

        for i in range(self.leaf_count):
            t = (i + 1) / (self.leaf_count + 1)
            bx = start[0] + (end[0] - start[0]) * t
            by = start[1] + (end[1] - start[1]) * t
            side = -1 if i % 2 else 1
            leaf_w = 9 + (i % 3) * 2
            leaf_h = 5 + (i % 2) * 2
            lx = round(bx + side * (8 + (i % 2) * 5))
            ly = round(by - 5 + side * 2)
            color = leaf_light if i % 2 else leaf_dark
            pygame.draw.ellipse(screen, color, (lx - leaf_w // 2, ly - leaf_h // 2, leaf_w, leaf_h))


class WindChallenge:
    """A Szél jelenet: a farkas jobbra halad, ágak sodródnak be jobbról."""

    def __init__(self, config, ground_y: int, scale: float = 1.0) -> None:
        self.config = config
        self.ground_y = int(ground_y)
        self.scale = scale

        self.active = False
        self.solved = False
        self.start_world_x = 0.0
        self.cave_world_x = 0.0

        self.branches: list[WindBranch] = []
        self.spawn_timer = 0.0
        self.spawn_count = 0
        self.gust_time = 0.0
        self.rng = random.Random(7319)

        self.cave_distance = int(WIND_CAVE_DISTANCE * max(0.95, min(1.15, scale)))
        self.cave_width = int(WIND_CAVE_WIDTH_BASE * scale)
        self.cave_height = int(WIND_CAVE_HEIGHT_BASE * scale)

    def start(self, player_world_x: float, camera_x: float, screen_width: int, *, ground_y: int | None = None) -> None:
        if ground_y is not None:
            self.ground_y = int(ground_y)

        self.active = True
        self.solved = False
        self.start_world_x = player_world_x
        self.cave_world_x = player_world_x + self.cave_distance
        self.branches.clear()
        self.spawn_timer = WIND_FIRST_BRANCH_DELAY
        self.spawn_count = 0
        self.gust_time = 0.0
        self.rng.seed(7319)

    def solve(self) -> None:
        self.active = False
        self.solved = True
        self.branches.clear()

    def reached_cave(self, player_world_x: float) -> bool:
        return self.active and not self.solved and player_world_x >= self.cave_world_x - WIND_CAVE_REACH_TOLERANCE

    def _next_branch_kind(self) -> str:
        pattern = ("low", "high", "low", "low", "high", "low", "high")
        return pattern[self.spawn_count % len(pattern)]

    def _spawn_branch(self, camera_x: float, screen_width: int) -> None:
        kind = self._next_branch_kind()
        base_thickness = max(10, int(WIND_BRANCH_THICKNESS_BASE * self.scale))

        if kind == "low":
            length = int(WIND_LOW_BRANCH_LENGTH_BASE * self.scale * self.rng.uniform(0.85, 1.28))
            thickness = int(base_thickness * self.rng.uniform(0.9, 1.25))
            center_y = self.ground_y - thickness * 0.5 + 3
            angle = self.rng.uniform(-7.0, 3.0)
        else:
            length = int(WIND_HIGH_BRANCH_LENGTH_BASE * self.scale * self.rng.uniform(0.9, 1.32))
            thickness = int(base_thickness * self.rng.uniform(0.85, 1.15))
            min_offset = int(WIND_HIGH_BRANCH_MIN_OFFSET_BASE * self.scale)
            max_offset = int(WIND_HIGH_BRANCH_MAX_OFFSET_BASE * self.scale)
            center_y = self.ground_y - self.rng.randint(min_offset, max_offset)
            angle = self.rng.uniform(-10.0, 9.0)

        world_x = camera_x + screen_width + length + self.rng.randint(70, 180)
        speed = WIND_BRANCH_SPEED * max(0.92, min(1.18, self.scale)) * self.rng.uniform(0.92, 1.12)
        leaf_count = self.rng.randint(4, 8)

        self.branches.append(
            WindBranch(
                kind=kind,
                world_x=world_x,
                center_y=center_y,
                length=length,
                thickness=thickness,
                speed=speed,
                angle_deg=angle,
                leaf_count=leaf_count,
                phase=self.rng.random() * math.tau,
            )
        )
        self.spawn_count += 1

    def update(
        self,
        dt: float,
        camera_x: float,
        screen_width: int,
        player_world_x: float,
        *,
        paused: bool = False,
    ) -> None:
        self.gust_time += dt
        if not self.active or self.solved:
            return
        if paused:
            return

        for branch in self.branches:
            branch.world_x -= branch.speed * dt
            branch.phase += dt * 5.5

        self.branches = [
            branch for branch in self.branches
            if branch.world_x + branch.length * 0.5 > camera_x - 140
        ]

        if player_world_x >= self.cave_world_x - max(260, screen_width * 0.22):
            return

        self.spawn_timer -= dt
        while self.spawn_timer <= 0.0:
            self._spawn_branch(camera_x, screen_width)
            self.spawn_timer += self.rng.uniform(WIND_BRANCH_SPAWN_MIN, WIND_BRANCH_SPAWN_MAX)

    def collides_with_player(self, player: "Player") -> bool:
        if not self.active or self.solved:
            return False

        half_width = int(player.collision_half_width + WIND_COLLISION_PADDING_X)
        left = round(player.world_x - half_width)
        width = half_width * 2

        lower_height = max(34, int(46 * self.scale))
        lower_body = pygame.Rect(left, round(player.y - lower_height), width, lower_height)

        full_body = pygame.Rect(left, round(player.y - SPRITE_HEIGHT), width, SPRITE_HEIGHT)
        player_on_ground = bool(getattr(player, "on_ground", False))

        for branch in self.branches:
            branch_rect = branch.collision_rect()
            if branch.kind == "low":
                if branch_rect.colliderect(lower_body):
                    return True
            else:
                if not player_on_ground and branch_rect.colliderect(full_body):
                    return True

        return False

    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        if not self.active and not self.solved:
            return

        if self.active:
            self._draw_wind_streaks(screen, camera_y)

        self._draw_cave(screen, camera_x, camera_y)

        for branch in self.branches:
            branch.draw(screen, camera_x, camera_y)

    def _draw_wind_streaks(self, screen: pygame.Surface, camera_y: float) -> None:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        width, height = screen.get_size()
        base_y = self.ground_y - camera_y

        for i in range(12):
            speed = 150 + i * 13
            x = width + 160 - ((self.gust_time * speed + i * 113) % (width + 420))
            y = base_y - 55 - ((i * 37 + math.sin(self.gust_time * 1.8 + i) * 18) % max(160, height))
            line_len = 70 + (i % 4) * 22
            alpha = 32 + (i % 3) * 12
            pygame.draw.line(
                overlay,
                (225, 234, 255, alpha),
                (round(x), round(y)),
                (round(x - line_len), round(y + 7)),
                2,
            )

        screen.blit(overlay, (0, 0))

    def _draw_cave(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        if self.cave_world_x <= 0:
            return

        cave_x = round(self.cave_world_x - camera_x)
        ground_y = round(self.ground_y - camera_y)
        width = self.cave_width
        height = self.cave_height

        if cave_x < -width or cave_x > screen.get_width() + width:
            return

        shadow_rect = pygame.Rect(0, 0, int(width * 0.92), max(12, int(height * 0.13)))
        shadow_rect.center = (cave_x, ground_y + 8)
        pygame.draw.ellipse(screen, (24, 18, 31), shadow_rect)

        rock_dark = (70, 68, 78)
        rock_mid = (104, 101, 111)
        rock_light = (144, 140, 148)
        entrance = (20, 17, 27)

        mound = [
            (cave_x - width // 2, ground_y + 4),
            (cave_x - int(width * 0.40), ground_y - int(height * 0.45)),
            (cave_x - int(width * 0.17), ground_y - int(height * 0.88)),
            (cave_x + int(width * 0.16), ground_y - int(height * 0.94)),
            (cave_x + int(width * 0.42), ground_y - int(height * 0.45)),
            (cave_x + width // 2, ground_y + 4),
        ]
        pygame.draw.polygon(screen, rock_dark, mound)
        pygame.draw.polygon(screen, rock_mid, mound, 4)

        entrance_rect = pygame.Rect(0, 0, int(width * 0.52), int(height * 0.75))
        entrance_rect.midbottom = (cave_x, ground_y + 2)
        pygame.draw.ellipse(screen, entrance, entrance_rect)
        pygame.draw.rect(
            screen,
            entrance,
            (entrance_rect.left, entrance_rect.centery, entrance_rect.width, entrance_rect.height // 2 + 4),
        )

        pygame.draw.circle(screen, rock_light, (cave_x - int(width * 0.27), ground_y - int(height * 0.18)), 10)
        pygame.draw.circle(screen, rock_mid, (cave_x + int(width * 0.30), ground_y - int(height * 0.12)), 13)
        pygame.draw.circle(screen, rock_light, (cave_x + int(width * 0.08), ground_y - int(height * 0.80)), 7)
