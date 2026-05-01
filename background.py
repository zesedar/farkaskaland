"""Statikus háttér: hatter.png + procedurálisan generált talaj-csempe + égbolt-folytatás."""
from __future__ import annotations

import random
from pathlib import Path

import pygame

from world_config import WorldConfig


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
