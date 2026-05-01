"""5. kihívás: sziklacsúcs platform-ugrálással. Apró kockákon kell felugrálni
egy magas csúcsra; a kamera vertikálisan is követi a játékost."""
from __future__ import annotations

import random

import pygame

from constants import (
    PEAK_BLOCK_HEIGHT_BASE,
    PEAK_BLOCK_WIDTH_BASE,
    PEAK_CLIMB_SCREENS,
    PEAK_SUMMIT_DETECT_TOLERANCE,
)


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
        """Procedurálisan generál egy variált, nehezebb felfelé vezető útvonalat.

        A blokkok között nagyobbak az X tengely menti távolságok,
        ezért több levegő-irányítás és pontosabb ugrás szükséges.
        """
        rng = random.Random(20260)

        block_w = max(78, int(PEAK_BLOCK_WIDTH_BASE * scale))
        v_step_avg = max(58, int(70 * scale))
        num_steps = max(30, target_climb_height // v_step_avg)

        rel_x = 0
        height_above = max(50, int(56 * scale))
        sign = 1

        layout: list[tuple[int, int, int]] = []

        for i in range(num_steps):
            layout.append((rel_x, height_above, block_w))

            # Függőleges lépés: maradhat hasonló, hogy ne legyen túl brutális egyszerre.
            v_step = rng.randint(int(v_step_avg * 0.85), int(v_step_avg * 1.18))
            height_above += v_step

            roll = rng.random()

            if roll < 0.18:
                # Ritkább közvetlen átfedés.
                h_offset = rng.randint(-int(35 * scale), int(35 * scale))

            elif roll < 0.42:
                # Közepes oldalra-ugrás.
                h_offset = int(rng.randint(85, 130) * scale) * sign
                sign *= -1

            elif roll < 0.75:
                # Nagy oldalra-ugrás.
                h_offset = int(rng.randint(130, 190) * scale) * sign
                sign *= -1

            else:
                # Nagyon nagy oldalra-ugrás.
                h_offset = int(rng.randint(190, 260) * scale) * sign
                sign *= -1

            rel_x += h_offset

            # Nagyobb vízszintes mozgást engedünk.
            if rel_x > int(900 * scale):
                rel_x = int(880 * scale)
                sign = -1
            elif rel_x < int(-900 * scale):
                rel_x = int(-880 * scale)
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
