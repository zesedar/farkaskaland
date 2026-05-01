"""UI komponensek: dialog-doboz, lebegő gondolatfelhő, intró/menü/névjegy képernyő."""
from __future__ import annotations

import random
from pathlib import Path

import pygame

from constants import (
    BLOCKED_THOUGHT_TEXT,
    INTRO_TEXT,
    THOUGHT_BUBBLE_FADE_SPEED,
    THOUGHT_BUBBLE_VISIBLE_TIME,
    WINDOW_TITLE,
)
from world_config import WorldConfig


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    line = words[0]
    for word in words[1:]:
        test = f"{line} {word}"
        if font.size(test)[0] <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


class DialogueBox:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.active = False
        self.text = ""
        self.hint_text = "Enter - tovább"
        self.font = pygame.font.SysFont("arial", max(26, int(config.height * 0.036)))
        self.hint_font = pygame.font.SysFont("arial", max(18, int(config.height * 0.024)))

    def show(self, text: str, hint_text: str = "Enter - tovább") -> None:
        self.text = text
        self.hint_text = hint_text
        self.active = True

    def hide(self) -> None:
        self.active = False
        self.hint_text = "Enter - tovább"

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        box_width = int(self.config.width * 0.54)
        padding_x = int(self.config.width * 0.025)
        padding_y = int(self.config.height * 0.026)
        line_spacing = max(8, int(self.config.height * 0.012))
        lines = wrap_text(self.text, self.font, box_width - padding_x * 2)
        rendered = [self.font.render(line, True, (234, 235, 255)) for line in lines]
        hint = self.hint_font.render(self.hint_text, True, (176, 198, 245))
        text_h = sum(s.get_height() for s in rendered) + max(0, len(rendered) - 1) * line_spacing
        box_height = padding_y * 2 + text_h + hint.get_height() + line_spacing + 10
        box_rect = pygame.Rect(0, 0, box_width, box_height)
        box_rect.center = (self.config.width // 2, self.config.height // 2)
        shadow = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 90), shadow.get_rect(), border_radius=22)
        screen.blit(shadow, box_rect.move(0, 8).topleft)
        panel = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (14, 20, 54, 220), panel.get_rect(), border_radius=22)
        pygame.draw.rect(panel, (109, 133, 228, 235), panel.get_rect(), 2, border_radius=22)
        screen.blit(panel, box_rect.topleft)
        current_y = box_rect.y + padding_y
        for surface in rendered:
            text_rect = surface.get_rect(centerx=box_rect.centerx, y=current_y)
            screen.blit(surface, text_rect)
            current_y += surface.get_height() + line_spacing
        hint_rect = hint.get_rect(centerx=box_rect.centerx, bottom=box_rect.bottom - padding_y + 2)
        screen.blit(hint, hint_rect)


class ThoughtBubble:
    """Lebegő gondolatfelhő a játékos feje fölött, fade-in/fade-out animációval."""

    def __init__(self, config: WorldConfig, text: str = BLOCKED_THOUGHT_TEXT) -> None:
        self.config = config
        self.text = text
        self.font = pygame.font.SysFont("arial", max(20, int(config.height * 0.026)), italic=True)
        self.alpha = 0.0
        self.target_alpha = 0.0
        self.visible_timer = 0.0
        self._cached_bubble: pygame.Surface | None = None
        self._build_bubble()

    def _build_bubble(self) -> None:
        text_surf = self.font.render(self.text, True, (28, 30, 78))
        padding_x, padding_y = 22, 14
        bubble_w = text_surf.get_width() + padding_x * 2
        bubble_h = text_surf.get_height() + padding_y * 2
        # Bal padding: hely a tail-felhőcskéknek, hogy a buborék MAGA jobbra
        # legyen az anchor ponttól, és csak a tail nyúljon balra a farkas felé.
        left_pad = 30
        bottom_pad = 56
        surf_w = bubble_w + left_pad
        surf_h = bubble_h + bottom_pad
        surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        fill = (245, 248, 255)
        border = (140, 152, 210)
        # Fő buborék: az x=left_pad-tól indul, így az ANCHOR ponttól jobbra van.
        bubble_x = left_pad
        # Tail: a buborék bal-alsó sarkából INDUL és LEFELÉ-BALRA tart, belóg
        # a left_pad területbe. Így vizuálisan visszamutat a farkas feje felé.
        for cx_off, cy_off, r in [(20, bubble_h + 8, 11), (2, bubble_h + 22, 7), (-14, bubble_h + 36, 4)]:
            cx = bubble_x + cx_off
            pygame.draw.circle(surf, border, (cx, cy_off), r)
            pygame.draw.circle(surf, fill, (cx, cy_off), r - 2)
        # Fő buborék
        pygame.draw.rect(surf, fill, (bubble_x, 0, bubble_w, bubble_h), border_radius=20)
        pygame.draw.rect(surf, border, (bubble_x, 0, bubble_w, bubble_h), 2, border_radius=20)
        surf.blit(text_surf, (bubble_x + padding_x, padding_y))
        self._cached_bubble = surf

    def show(self, text: str | None = None) -> None:
        """A megjelenítés "kérése" - minden hívás újraindítja a látható időt.

        A harmadik kihívás ugyanazt a buborék-komponenst használja, csak más
        szöveggel, ezért opcionálisan átépítjük a cache-elt buborékot.
        """
        if text is not None and text != self.text:
            self.text = text
            self._build_bubble()
        self.target_alpha = 1.0
        self.visible_timer = THOUGHT_BUBBLE_VISIBLE_TIME

    def hide_immediately(self) -> None:
        self.alpha = 0.0
        self.target_alpha = 0.0
        self.visible_timer = 0.0

    def update(self, dt: float) -> None:
        if self.visible_timer > 0:
            self.visible_timer -= dt
            if self.visible_timer <= 0:
                self.target_alpha = 0.0
        diff = self.target_alpha - self.alpha
        step = THOUGHT_BUBBLE_FADE_SPEED * dt
        if abs(diff) <= step:
            self.alpha = self.target_alpha
        else:
            self.alpha += step if diff > 0 else -step

    def draw(self, screen: pygame.Surface, anchor_screen_pos: tuple[int, int]) -> None:
        if self.alpha <= 0.01 or self._cached_bubble is None:
            return
        bubble = self._cached_bubble
        bubble.set_alpha(int(255 * self.alpha))
        # bottomleft anchor: a surface bal-alsó sarka az anchor ponton.
        # A buborék maga jobbra van (left_pad miatt), a tail balra-felfelé
        # mutat vissza a farkas feje felé. Bal oldalon NEM lóg ki túl a szegélyen.
        bubble_rect = bubble.get_rect(bottomleft=anchor_screen_pos)
        screen.blit(bubble, bubble_rect)


class IntroMenuScreen:
    def __init__(self, config: WorldConfig) -> None:
        self.config = config
        self.options = ["Játék indítása", "Névjegy", "Kilépés"]
        self.selected_index = 0
        self.menu_scale = 0.78  # A főmenü bal oldali paneljének és szövegeinek arányos kicsinyítése.
        self.menu_title_font = pygame.font.SysFont("georgia", max(42, int(config.height * 0.085 * self.menu_scale)), bold=True)
        self.menu_subtitle_font = pygame.font.SysFont("arial", max(19, int(config.height * 0.038 * self.menu_scale)), italic=True)
        self.menu_option_font = pygame.font.SysFont("arial", max(22, int(config.height * 0.043 * self.menu_scale)), bold=True)
        self.menu_small_font = pygame.font.SysFont("arial", max(14, int(config.height * 0.024 * self.menu_scale)))
        self.title_font = pygame.font.SysFont("georgia", max(54, int(config.height * 0.085)), bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", max(24, int(config.height * 0.038)), italic=True)
        self.option_font = pygame.font.SysFont("arial", max(28, int(config.height * 0.043)), bold=True)
        self.body_font = pygame.font.SysFont("arial", max(22, int(config.height * 0.031)))
        self.small_font = pygame.font.SysFont("arial", max(16, int(config.height * 0.024)))
        self.quote_font = pygame.font.SysFont("arial", max(20, int(config.height * 0.025)), italic=True)
        self.option_rects: list[pygame.Rect] = []
        self.background = self._load_background()


    def _load_background(self) -> pygame.Surface:
        candidates = [
            Path(__file__).parent / "assets" / "intro_background.png",
            Path(__file__).parent / "assets" / "hatter.png",
            Path("/mnt/data/ghostwriter_images/context/cfad7fbc-a0c5-59f7-9bef-e2c6a91c52f1.png"),
        ]
        source = next((path for path in candidates if path.exists()), None)
        if source is not None:
            image = pygame.image.load(str(source)).convert()
            return pygame.transform.smoothscale(image, (self.config.width, self.config.height))

        fallback = pygame.Surface((self.config.width, self.config.height))
        top = pygame.Color(8, 16, 78)
        middle = pygame.Color(78, 45, 183)
        bottom = pygame.Color(233, 131, 185)
        for y in range(self.config.height):
            t = y / max(1, self.config.height - 1)
            if t < 0.62:
                color = top.lerp(middle, t / 0.62)
            else:
                color = middle.lerp(bottom, (t - 0.62) / 0.38)
            pygame.draw.line(fallback, color, (0, y), (self.config.width, y))
        moon_center = (int(self.config.width * 0.18), int(self.config.height * 0.18))
        pygame.draw.circle(fallback, (250, 236, 206), moon_center, max(38, int(self.config.height * 0.06)))
        pygame.draw.circle(fallback, (35, 41, 126), (moon_center[0] + 18, moon_center[1] - 2), max(34, int(self.config.height * 0.052)))
        rng = random.Random(77)
        for _ in range(140):
            x = rng.randint(0, self.config.width - 1)
            y = rng.randint(0, int(self.config.height * 0.58))
            radius = rng.randint(1, 2)
            shade = rng.randint(220, 255)
            pygame.draw.circle(fallback, (shade, shade, 255), (x, y), radius)
        return fallback


    def move_selection(self, delta: int) -> None:
        self.selected_index = (self.selected_index + delta) % len(self.options)

    def option_at(self, pos: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self.option_rects):
            if rect.collidepoint(pos):
                return index
        return None

    def draw_menu(self, screen: pygame.Surface) -> None:
        screen.blit(self.background, (0, 0))
        overlay = pygame.Surface((self.config.width, self.config.height), pygame.SRCALPHA)
        overlay.fill((5, 8, 26, 106))
        screen.blit(overlay, (0, 0))

        menu_scale = self.menu_scale
        panel_w = int(self.config.width * 0.44)
        panel_h = int(self.config.height * 0.42)
        panel_rect = pygame.Rect(int(self.config.width * 0.08), int(self.config.height * 0.20), panel_w, panel_h)
        corner_radius = max(18, int(28 * menu_scale))

        panel_shadow = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_shadow, (0, 0, 0, 95), panel_shadow.get_rect(), border_radius=corner_radius)
        screen.blit(panel_shadow, panel_rect.move(0, max(6, int(10 * menu_scale))).topleft)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (11, 15, 41, 188), panel.get_rect(), border_radius=corner_radius)
        pygame.draw.rect(panel, (129, 151, 239, 225), panel.get_rect(), 2, border_radius=corner_radius)
        screen.blit(panel, panel_rect.topleft)

        pad_x = max(22, int(34 * menu_scale))
        title = self.menu_title_font.render(WINDOW_TITLE, True, (241, 239, 255))
        subtitle = self.menu_subtitle_font.render("Holdfényes utazás egy csendes, meseszerű világban.", True, (201, 208, 255))
        screen.blit(title, (panel_rect.x + pad_x, panel_rect.y + max(20, int(28 * menu_scale))))
        screen.blit(subtitle, (panel_rect.x + pad_x, panel_rect.y + max(82, int(108 * menu_scale))))

        self.option_rects = []
        start_y = panel_rect.y + max(126, int(170 * menu_scale))
        box_h = max(42, int(self.config.height * 0.08 * menu_scale))
        box_gap = max(12, int(18 * menu_scale))
        option_pad_x = max(22, int(30 * menu_scale))
        option_radius = max(13, int(18 * menu_scale))
        for index, option in enumerate(self.options):
            rect = pygame.Rect(panel_rect.x + option_pad_x, start_y + index * (box_h + box_gap), panel_rect.width - option_pad_x * 2, box_h)
            self.option_rects.append(rect)
            selected = index == self.selected_index
            box = pygame.Surface(rect.size, pygame.SRCALPHA)
            fill = (137, 112, 232, 210) if selected else (29, 38, 89, 170)
            border = (238, 228, 255, 240) if selected else (120, 139, 219, 210)
            pygame.draw.rect(box, fill, box.get_rect(), border_radius=option_radius)
            pygame.draw.rect(box, border, box.get_rect(), 2, border_radius=option_radius)
            screen.blit(box, rect.topleft)
            label = self.menu_option_font.render(option, True, (255, 248, 255) if selected else (224, 231, 255))
            label_rect = label.get_rect(center=rect.center)
            screen.blit(label, label_rect)

        hint_text = "↑/↓: választás • Enter: elfogadás • Egér: kattintás"
        hint_lines = wrap_text(hint_text, self.menu_small_font, panel_rect.width - pad_x * 2)
        hint_surfaces = [self.menu_small_font.render(line, True, (220, 227, 255)) for line in hint_lines]
        hint_line_gap = max(3, int(5 * menu_scale))
        hint_w = max(surface.get_width() for surface in hint_surfaces)
        hint_h = sum(surface.get_height() for surface in hint_surfaces) + max(0, len(hint_surfaces) - 1) * hint_line_gap
        hint_pad_x = max(8, int(10 * menu_scale))
        hint_pad_y = max(5, int(6 * menu_scale))
        hint_bg = pygame.Surface((hint_w + hint_pad_x * 2, hint_h + hint_pad_y * 2), pygame.SRCALPHA)
        pygame.draw.rect(hint_bg, (7, 12, 34, 125), hint_bg.get_rect(), border_radius=max(12, int(16 * menu_scale)))
        hint_pos = (panel_rect.x + pad_x - hint_pad_x, panel_rect.bottom + max(4, int(5 * menu_scale)))
        screen.blit(hint_bg, hint_pos)
        hint_y = hint_pos[1] + hint_pad_y
        for surface in hint_surfaces:
            screen.blit(surface, (hint_pos[0] + hint_pad_x, hint_y))
            hint_y += surface.get_height() + hint_line_gap

        moon_quote = self.quote_font.render(INTRO_TEXT, True, (238, 228, 255))
        moon_quote_rect = moon_quote.get_rect(
            bottomleft=(int(self.config.width * 0.09), self.config.height - 36)
        )
        screen.blit(moon_quote, moon_quote_rect)


    def draw_about(self, screen: pygame.Surface, music_enabled: bool, music_available: bool, music_path_found: bool) -> None:
        screen.blit(self.background, (0, 0))
        dim = pygame.Surface((self.config.width, self.config.height), pygame.SRCALPHA)
        dim.fill((2, 5, 18, 152))
        screen.blit(dim, (0, 0))

        panel_rect = pygame.Rect(0, 0, int(self.config.width * 0.62), int(self.config.height * 0.64))
        panel_rect.center = (self.config.width // 2, self.config.height // 2)
        shadow = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 105), shadow.get_rect(), border_radius=28)
        screen.blit(shadow, panel_rect.move(0, 10).topleft)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (11, 16, 42, 218), panel.get_rect(), border_radius=28)
        pygame.draw.rect(panel, (130, 154, 240, 230), panel.get_rect(), 2, border_radius=28)
        screen.blit(panel, panel_rect.topleft)

        title = self.title_font.render("Névjegy", True, (245, 243, 255))
        screen.blit(title, (panel_rect.x + 34, panel_rect.y + 26))

        music_text = "bekapcsolva" if music_enabled else "kikapcsolva"
        availability_text = "rendben betöltve" if music_available else ("a dallam.wav hiányzik" if not music_path_found else "hangrendszer nem elérhető")
        paragraphs = [
            "Ez a játék egy holdfényes, mesés hangulatú 2D oldalnézetes kaland.",
            "A főmenüből elindítható a játék, megnyitható ez a névjegy, vagy kiléphetsz.",
            "Irányítás játék közben: nyilak a mozgáshoz, Space/Fel az ugráshoz, A az üvöltéshez, Enter az üzenetek bezárásához.",
            f"Zene: M billentyűvel kapcsolható ki vagy be. Jelenleg: {music_text}; állapot: {availability_text}.",
            "A dallam végtelenítve szól, ha az assets könyvtárban megtalálható a dallam.wav fájl.",
        ]
        max_width = panel_rect.width - 70
        y = panel_rect.y + 108
        for paragraph in paragraphs:
            for line in wrap_text(paragraph, self.body_font, max_width):
                rendered = self.body_font.render(line, True, (228, 234, 255))
                screen.blit(rendered, (panel_rect.x + 36, y))
                y += rendered.get_height() + 8
            y += 10

        footer = self.small_font.render("Esc / Backspace / Enter - vissza a főmenübe", True, (200, 211, 255))
        screen.blit(footer, (panel_rect.x + 36, panel_rect.bottom - 48))
