"""6. (záró) jelenet: a csúcson ülő farkas felidézi a Göncöl szekér csillagképet,
amelyet a játékosnak egyetlen folyamatos mozdulattal kell összekötnie."""
from __future__ import annotations

import math

import pygame

from constants import (
    CONSTELLATION_LINE_WIDTH_BASE,
    CONSTELLATION_STAR_HIT_TOLERANCE_BASE,
)
from world_config import WorldConfig


class ConstellationChallenge:
    """Záró kihívás a csúcson: a játékosnak egyetlen folyamatos mozdulattal
    össze kell kötnie a Göncöl szekér 7 csillagát.

    A csillagok fix pozícióban láthatók a képernyőn (nem sötétített háttéren!),
    a játékos pedig egy mozdulattal végighúzza a kurzort rajtuk a megfelelő
    sorrendben. A "szekér-test" 4 csillagát követi 3 további csillag a "rúdra".
    Két irányban is rajzolható: a szekér-test bal-alsó csillagából indulva
    a rúd vége felé, vagy fordítva.
    """

    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.active = False
        self.solved = False
        self.drawing = False
        self.points: list[tuple[int, int]] = []
        self.next_star_index = 0
        self.direction = 0  # 0=ismeretlen, 1=előre (0..6), -1=hátra (6..0)
        self.completion_pulse_t = 0.0
        # Skálázás a képernyőhöz
        scale_x = max(0.85, min(1.4, config.width / 1280))
        scale_y = max(0.85, min(1.4, config.height / 720))
        self.tolerance = max(38, int(CONSTELLATION_STAR_HIT_TOLERANCE_BASE
                                     * min(scale_x, scale_y)))
        self.line_width = max(2, int(CONSTELLATION_LINE_WIDTH_BASE * scale_y))
        # Csillagok pozíciója a képernyőn. A klasszikus Göncöl szekér alakzata:
        # bal oldalt egy közel-trapéz alakú bowl (kerekek), jobbra hosszan
        # nyúló, lefelé hajló rúd. Sorrend (egyvonalú trace):
        #   0: Phecda (γ) - bowl jobb-alsó
        #   1: Merak (β)  - bowl bal-alsó
        #   2: Dubhe (α)  - bowl bal-felső
        #   3: Megrez (δ) - bowl jobb-felső (rúd csatlakozik)
        #   4: Alioth (ε) - rúd 1
        #   5: Mizar (ζ)  - rúd 2
        #   6: Alkaid (η) - rúd vége (lefelé hajlik)
        # Csillagok pozíciója a képernyő felső felében, középre igazítva.
        # Nem pont a tetején, hogy elférjen körülötte vizuális tér is.
        # GEOMETRIA: A J2000.0 koordinátákból (RA, Dec) kis-szögű projekcióval
        # számolt relatív pozíciók fokokban, majd skálázva. A Göncöl szekér
        # valódi formája egy ferde paralelogramma (a "kocsi"), amelyhez egy
        # LEFELÉ ívelő rúd csatlakozik (Alkaid mélyen lent-balra).
        #
        # Sorrend (egy mozdulattal végighúzhatóan):
        #   0: Dubhe (α UMa)   - kocsi jobb-felső, "mutató" csillag
        #   1: Merak (β UMa)   - kocsi jobb-alsó (Dubhe alatt, picit lentebb)
        #   2: Phecda (γ UMa)  - kocsi bal-alsó (Merak-tól balra)
        #   3: Megrez (δ UMa)  - kocsi bal-felső, ide csatlakozik a rúd
        #   4: Alioth (ε UMa)  - rúd 1
        #   5: Mizar (ζ UMa)   - rúd 2
        #   6: Alkaid (η UMa)  - rúd vége, mélyen lent-balra ível
        cx = config.width // 2
        cy = int(config.height * 0.45)
        scale_factor = min(scale_x, scale_y)

        def s(dx: float, dy: float) -> tuple[int, int]:
            return (int(cx + dx * scale_factor), int(cy + dy * scale_factor))

        self.stars: list[tuple[int, int]] = [
            s(+245, -136),   # 0: Dubhe   - kocsi jobb-felső
            s(+250,  -18),   # 1: Merak   - kocsi jobb-alsó
            s( +85,  +42),   # 2: Phecda  - kocsi bal-alsó
            s( +18,  -32),   # 3: Megrez  - kocsi bal-felső
            s(-103,   -8),   # 4: Alioth  - rúd 1
            s(-195,  +14),   # 5: Mizar   - rúd 2
            s(-271, +138),   # 6: Alkaid  - rúd vége (lefelé ível)
        ]
        self.completed: list[bool] = [False] * len(self.stars)

    def start(self) -> None:
        self.active = True
        self.solved = False
        self.drawing = False
        self.points.clear()
        self.next_star_index = 0
        self.direction = 0
        self.completion_pulse_t = 0.0
        self.completed = [False] * len(self.stars)

    def is_visible(self) -> bool:
        return self.active

    def blocks_controls(self) -> bool:
        return self.active and not self.solved

    def update(self, dt: float) -> None:
        if self.solved:
            self.completion_pulse_t += dt

    def begin_stroke(self, pos: tuple[int, int]) -> None:
        if not self.active or self.solved:
            return
        self.drawing = True
        self.points = [pos]
        self._check_star_hit(pos)

    def add_point(self, pos: tuple[int, int]) -> bool:
        if not self.active or self.solved or not self.drawing:
            return False
        if self.points:
            last_x, last_y = self.points[-1]
            dx = pos[0] - last_x
            dy = pos[1] - last_y
            if dx * dx + dy * dy < 9:  # legalább 3 px mozgás
                return False
        self.points.append(pos)
        if len(self.points) > 800:
            self.points = self.points[-800:]
        self._check_star_hit(pos)
        return self.solved

    def _check_star_hit(self, pos: tuple[int, int]) -> None:
        """Megnézi, hogy az aktuális pont eltalálja-e a soron következő csillagot.

        Az első találat határozza meg a rajzolási irányt: ha a 0. csillagot éri
        el először, előre megy a sorozaton; ha a 6.-at, fordítva. Bármi más
        kezdés esetén a két végponton várjuk az első találatot.
        """
        if self.direction == 0:
            # Még nincs irány - nézzük mind a két végpontot
            d_first_sq = self._dist_sq(pos, self.stars[0])
            d_last_sq = self._dist_sq(pos, self.stars[-1])
            tol_sq = self.tolerance * self.tolerance
            if d_first_sq <= tol_sq and d_first_sq <= d_last_sq:
                self.direction = 1
                self.completed[0] = True
                self.next_star_index = 1
            elif d_last_sq <= tol_sq:
                self.direction = -1
                self.completed[-1] = True
                self.next_star_index = len(self.stars) - 2
            return
        # Irány már megvan - csak a következő csillagot vizsgáljuk
        if 0 <= self.next_star_index < len(self.stars):
            star = self.stars[self.next_star_index]
            if self._dist_sq(pos, star) <= self.tolerance * self.tolerance:
                self.completed[self.next_star_index] = True
                self.next_star_index += self.direction
                # Megoldás-ellenőrzés
                if self.direction == 1 and self.next_star_index >= len(self.stars):
                    self.solved = True
                elif self.direction == -1 and self.next_star_index < 0:
                    self.solved = True

    @staticmethod
    def _dist_sq(a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return dx * dx + dy * dy

    def end_stroke(self) -> bool:
        # A mozdulat-vég nem reseteli a haladást; a játékos folytathatja egy
        # új lehúzással ott, ahol abbahagyta. (Csak abbahagyja az aktív rajzolást.)
        self.drawing = False
        return self.solved

    def handle_event(self, event: pygame.event.Event) -> bool:
        """True-val tér vissza, ha az esemény megoldotta a kihívást."""
        if not self.active or self.solved:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.begin_stroke(event.pos)
            return self.solved
        if event.type == pygame.MOUSEMOTION:
            # Mint a kereszt-kihívásnál: nem kötelező lenyomva tartani a gombot.
            if not self.drawing:
                self.begin_stroke(event.pos)
            return self.add_point(event.pos)
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            return self.end_stroke()
        return False

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        # 1) Befejezett összekötő-vonalak (csillagról csillagra) - tartósak,
        #    végigvezetik a már megtett útvonalat.
        completed_count = sum(1 for c in self.completed if c)
        if completed_count >= 2:
            if self.direction == 1:
                line_pts = self.stars[:completed_count]
            elif self.direction == -1:
                line_pts = self.stars[len(self.stars) - completed_count:][::-1]
            else:
                line_pts = []
            if len(line_pts) >= 2:
                pygame.draw.lines(screen, (235, 248, 255), False, line_pts,
                                  self.line_width)
                pygame.draw.lines(screen, (165, 195, 245), False, line_pts,
                                  max(1, self.line_width - 1))

        # 2) Aktuális egér-nyom: ez az EGYETLEN feedback a játékos számára
        #    addig, amíg el nem éri az első csillagot. Halvány, de látható
        #    "tintacsík", ami megmutatja merre járt a kurzor.
        if len(self.points) >= 2 and not self.solved:
            pygame.draw.lines(screen, (200, 220, 255), False, self.points,
                              max(1, self.line_width - 1))
            for p in self.points[-6:]:
                pygame.draw.circle(screen, (240, 245, 255), p,
                                   max(2, self.line_width))

        # 3) Csillagok: CSAK a már elért csillagokat rajzoljuk - az érintetlenek
        #    láthatatlanok maradnak, ahogy azt a játékos ki kell tapasztalja
        #    a memóriájából. (A teljes alakzat felfedezése maga a kihívás.)
        for i, (sx, sy) in enumerate(self.stars):
            if not self.completed[i]:
                continue
            pygame.draw.circle(screen, (160, 180, 220), (sx, sy), 12)
            pygame.draw.circle(screen, (240, 248, 255), (sx, sy), 7)
            pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 3)

        # 4) Megoldás után rövid pulzáló glow az egész alakzaton - csak ekkor
        #    jelennek meg az összes csillagot körbevevő gyűrűk.
        if self.solved:
            ts = self.completion_pulse_t
            glow = (math.sin(ts * 4.0) * 0.5 + 0.5)
            for sx, sy in self.stars:
                radius = int(14 + glow * 6)
                pygame.draw.circle(screen, (130, 165, 220), (sx, sy), radius, 1)
