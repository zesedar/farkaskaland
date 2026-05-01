"""4. kihívás: sötétség, kurzor-fény és egy mozdulattal rajzolt + alakú kereszt."""
from __future__ import annotations

import math

import pygame

from constants import (
    CROSS_GESTURE_MIN_POINTS,
    CROSS_GESTURE_MIN_SPAN_BASE,
    CROSS_GESTURE_TOLERANCE_BASE,
    DARKNESS_FADE_IN_SPEED,
    DARKNESS_FADE_OUT_SPEED,
    DARKNESS_MAX_ALPHA,
    SPOTLIGHT_RADIUS_BASE,
)
from world_config import WorldConfig


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
