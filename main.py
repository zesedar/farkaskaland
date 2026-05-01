from __future__ import annotations

import math
from pathlib import Path

import pygame

from constants import (
    FPS,
    MAX_FRAME_DT,
    WINDOW_TITLE,
    INTRO_TEXT,
    THORN_TEXT,
    BLOCKED_THOUGHT_TEXT,
    BUSH_COLLAPSE_TEXT,
    LAKE_TEXT,
    LAKE_SOLVED_TEXT,
    LOG_WARNING_TEXT,
    GAME_OVER_TEXT,
    DARKNESS_HINT_TEXT,
    PEAK_INTRO_TEXT,
    PEAK_SUCCESS_TEXT,
    PEAK_BLOCKED_HINT_TEXT,
    CONSTELLATION_INTRO_TEXT,
    CONSTELLATION_COMPLETE_TEXT,
    SPRITE_HEIGHT,
    OBSTACLE_CAMERA_REVEAL_SPEED,
    OBSTACLE_CAMERA_REVEAL_EPSILON,
    LAKE_WORLD_X,
    LAKE_BLOCK_EPSILON,
    LAKE_HOLD_DURATION,
    LAKE_HOLD_DECAY,
    LOG_CHALLENGE_WORLD_X,
    LOG_CAMERA_CENTER_SMOOTHNESS,
    LOG_CAMERA_CENTER_EPSILON,
    DARK_CHALLENGE_WORLD_X,
    PEAK_CHALLENGE_WORLD_X,
    PEAK_BASE_OFFSET_X,
    PEAK_VERTICAL_CAMERA_BIAS,
    PEAK_VERTICAL_DEADZONE,
    WIND_CHALLENGE_WORLD_X,
    WIND_INTRO_TEXT,
    WIND_SUCCESS_TEXT,
    WIND_GAME_OVER_TEXT,
)
from world_config import WorldConfig
from player import Player
from ui import DialogueBox, ThoughtBubble, IntroMenuScreen
from background import StaticBackground
from scenes.bush import ThornBush
from scenes.lake import Lake, WillpowerIndicator
from scenes.log import RollingLog
from scenes.darkness import DarknessSignChallenge
from scenes.peak import RockyPeak
from scenes.constellation import ConstellationChallenge
from scenes.szel import WindChallenge


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        info = pygame.display.Info()
        self.config = WorldConfig(max(960, info.current_w), max(540, info.current_h))
        self.screen = pygame.display.set_mode((self.config.width, self.config.height), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.menu = IntroMenuScreen(self.config)
        self.state = "menu"
        self.music_enabled = True
        self.music_available = False
        self.music_path_found = False
        self._init_music()
        self.background = StaticBackground(self.config)
        self.player = Player(self.config)
        self.dialogue = DialogueBox(self.config)
        self.thought_bubble = ThoughtBubble(self.config)
        scale = max(1.0, self.config.height / 700)
        self.bush = ThornBush(world_x=2500, ground_y=self.config.ground_top_y, scale=scale)
        self.lake = Lake(world_x=LAKE_WORLD_X, ground_y=self.config.ground_top_y,
                         screen_height=self.config.height, scale=scale)
        self.willpower = WillpowerIndicator(self.config)
        self.rolling_log = RollingLog(ground_y=self.config.ground_top_y, scale=scale)
        self.dark_challenge = DarknessSignChallenge(self.config)
        self.camera_x = 0.0
        self.camera_y = 0.0  # vertikális kamera-eltolás (csak a sziklacsúcs jelenetben mozog)
        self.cinematic_camera_active = False
        self.cinematic_camera_target_x = 0.0
        self.pending_obstacle_text = ""
        # Bozót akadály állapotai
        self.bush_event_triggered = False
        self.bush_solved = False
        # Tó akadály állapotai
        self.lake_event_triggered = False
        self.lake_solved = False
        self.lake_hold_timer = 0.0  # 0..LAKE_HOLD_DURATION
        # Farönk akadály állapotai
        self.log_event_triggered = False
        self.log_solved = False
        self.log_camera_transition_active = False
        self.log_camera_transition_target_x = 0.0
        # Sötétség / kereszt akadály állapotai
        self.dark_event_triggered = False
        self.dark_solved = False
        # Sziklacsúcs akadály állapotai (5. jelenet)
        peak_base_x = float(PEAK_CHALLENGE_WORLD_X + PEAK_BASE_OFFSET_X)
        self.peak = RockyPeak(base_x=peak_base_x, ground_y=self.config.ground_top_y,
                              scale=scale, screen_height=self.config.height)
        self.peak_event_triggered = False
        self.peak_solved = False
        # 6. jelenet: csillagkép - a farkas a csúcson ülve felidézi a Göncölt.
        # A workflow szakaszai:
        #   "idle"     - még nem ért fel
        #   "sit"      - leült, dialog mutatja a "Mostmár tisztán látom..." szöveget
        #   "memory"   - dialog mutatja a "Emlékszem egy csillagképre..." szöveget
        #   "drawing"  - a csillagkép-kihívás aktív
        #   "done"     - kész, dialog mutatja a befejező szöveget
        self.constellation = ConstellationChallenge(self.config)
        self.constellation_phase = "idle"
        # 7. jelenet: Szél - jobbról érkező ágak, a végén barlangbejárat.
        self.wind = WindChallenge(self.config, ground_y=self.config.ground_top_y, scale=scale)
        self.wind_event_triggered = False
        self.wind_solved = False
        self.wind_outro_active = False
        self.game_over = False
        self.debug_font = pygame.font.SysFont("arial", max(18, int(self.config.height * 0.024)))
        self.music_font = pygame.font.SysFont("arial", max(18, int(self.config.height * 0.025)), bold=True)
        # Cache-elt help szöveg - nem változik, nem kell minden frame újra-renderelni.
        self._help_surface: pygame.Surface | None = None
        self._help_bg: pygame.Surface | None = None
        self._build_help_overlay()
        self.running = True

    def _build_help_overlay(self) -> None:
        text = "Mozgás: ←/→    Ugrás: Space / ↑    Üvöltés: A    M: zene ki/be    Enter: üzenet bezárása    Esc: kilépés"
        surface = self.debug_font.render(text, True, (226, 232, 255))
        bg = pygame.Surface((surface.get_width() + 22, surface.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 12, 34, 110), bg.get_rect(), border_radius=14)
        self._help_surface = surface
        self._help_bg = bg

    def _init_music(self) -> None:
        asset_dir = Path(__file__).parent / "assets"
        candidates = [
            asset_dir / "dallam.wav",
            Path("/mnt/data/assets/dallam.wav"),
        ]
        music_path = next((path for path in candidates if path.exists()), asset_dir / "dallam.wav")
        self.music_path_found = music_path.exists()
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            if self.music_path_found:
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(0.55)
                self.music_available = True
        except pygame.error:
            self.music_available = False

    def _start_music_if_needed(self) -> None:
        if self.state != "playing" or not self.music_enabled or not self.music_available:
            return
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)

    def _stop_music(self) -> None:
        if self.music_available and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def toggle_music(self) -> None:
        self.music_enabled = not self.music_enabled
        if not self.music_enabled:
            self._stop_music()
        else:
            self._start_music_if_needed()

    def activate_menu_option(self, option_index: int) -> None:
        option = self.menu.options[option_index]
        if option == "Játék indítása":
            self.start_game()
        elif option == "Névjegy":
            self.state = "about"
            self._stop_music()
        else:
            self.running = False

    def start_game(self) -> None:
        self.state = "playing"
        self.dialogue.hide()
        self.dialogue.show(INTRO_TEXT)
        self._start_music_if_needed()

    def draw_music_status(self) -> None:
        if self.state != "playing":
            return
        if not self.music_path_found:
            text = "Zene: a dallam.wav hiányzik az assets mappából"
        elif not self.music_available:
            text = "Zene: a hangrendszer nem elérhető"
        else:
            text = f"Zene: {'BE' if self.music_enabled else 'KI'}  [M]"
        surface = self.music_font.render(text, True, (234, 238, 255))
        bg = pygame.Surface((surface.get_width() + 18, surface.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 12, 34, 120), bg.get_rect(), border_radius=14)
        x = self.config.width - bg.get_width() - 22
        y = 18
        self.screen.blit(bg, (x, y))
        self.screen.blit(surface, (x + 9, y + 6))

    def controls_enabled(self) -> bool:
        return (
            not self.game_over
            and not self.dialogue.active
            and not self.cinematic_camera_active
            and not self.log_camera_transition_active
            and not self.player.is_howling()
            and not self.dark_challenge.blocks_controls()
            and not self.constellation.blocks_controls()
            and self.constellation_phase in ("idle", "done")
        )

    def movement_blocked(self) -> bool:
        """Teljes mozgás-tiltás csak a bozót akadálynál van. A tó NEM tiltja
        a mozgást, csak a jobbra-haladást blokkolja az obstacle_left_edge-en át -
        így a játékos elsétálhat balra is, és a fizika természetes marad."""
        return self.bush_event_triggered and not self.bush_solved

    def obstacle_left_edge(self) -> float | None:
        if self.bush_event_triggered and not self.bush_solved:
            return self.bush.left_edge
        if self.lake_event_triggered and not self.lake_solved:
            return self.lake.left_edge
        # A sziklacsúcs jelenetben láthatatlan fal blokkolja a talajszintű
        # tovább-sétálást, amíg a játékos nem ér fel a csúcsra. Így a kockákon
        # át vezet az egyetlen lehetséges út.
        if self.peak_event_triggered and not self.peak_solved:
            return self.peak.wall_world_x
        return None

    def floor_y_for_player(self) -> float:
        """A játékos jelenlegi x-pozíciója alatt fellelhető legmagasabb támaszték y-ja.

        Ha aktív a sziklacsúcs jelenet, a kockák tetejei is jelölhetnek "felszínt".
        Egyébként a fő talaj.
        """
        ground_y = float(self.config.ground_top_y)
        if self.peak_event_triggered:
            plat_y = self.peak.floor_y_under(self.player.world_x, self.player.y)
            if plat_y is not None and plat_y < ground_y:
                return plat_y
        return ground_y

    def is_pressed_against_lake(self) -> bool:
        """A játékos ténylegesen a tó által blokkolt helyzetben van-e?
        (handle_input min()-eli a world_x-et erre az értékre, ha jobbra próbál menni.)"""
        if not self.lake_event_triggered or self.lake_solved:
            return False
        block_x = self.lake.left_edge - self.player.collision_half_width
        return abs(self.player.world_x - block_x) < LAKE_BLOCK_EPSILON

    def start_obstacle_reveal(self, obstacle_left_edge: float, stop_distance: float, text: str,
                              *, preserve_player_position: bool = False,
                              target_player_screen_x: int | None = None) -> None:
        """Közös, újrahasználható akadály-megjelenítés minden nagy akadályhoz.

        A tónál már nem teleportáljuk előre a farkast a régi bal oldali reveal
        pozícióba, mert a korábbi kamerakövetéssel ez rángatósnak hatott. Ott
        a játékos marad a helyén, és csak a kamera úszik át egy olyan nézetre,
        ahol a tó jól látszik előtte.
        """
        if not preserve_player_position:
            self.player.world_x = obstacle_left_edge - stop_distance
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.cinematic_camera_active = True
        if target_player_screen_x is None:
            target_player_screen_x = self.config.left_frame_x
        self.cinematic_camera_target_x = max(0.0, self.player.world_x - target_player_screen_x)
        self.pending_obstacle_text = text
        if self.dialogue.active:
            self.dialogue.hide()

    def trigger_bush_event(self) -> None:
        self.bush_event_triggered = True
        self.start_obstacle_reveal(self.bush.left_edge, self.bush.stop_distance, THORN_TEXT)

    def trigger_lake_event(self) -> None:
        self.lake_event_triggered = True
        # A korábbi, jobban előre néző kamera mellett a régi tó-reveal túl nagy
        # átrendezést okozott. A farkas marad a triggerpontján, a kamera pedig
        # kb. a képernyő 30%-ára úsztatja, így a tó már látszik, de nincs rángás.
        self.start_obstacle_reveal(
            self.lake.left_edge,
            self.lake.stop_distance,
            LAKE_TEXT,
            preserve_player_position=True,
            target_player_screen_x=int(self.config.width * 0.30),
        )

    def centered_camera_x_for_player(self) -> float:
        """Kameraállás, ahol a farkas vízszintesen középen látszik."""
        return max(0.0, self.player.world_x - self.config.center_x)

    def trigger_log_event(self) -> None:
        self.log_event_triggered = True
        # A veszélyjelzésnél nézetet váltunk: a farkas középre kerül.
        # Nem vágunk azonnal a célkamerára, hanem külön, lassabb átmenettel
        # közelítünk rá, hogy ne "rántson" a kép. A farönk csak akkor spawnol,
        # amikor a kamera már beállt erre az új kompozícióra.
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.log_camera_transition_target_x = self.centered_camera_x_for_player()
        self.log_camera_transition_active = True
        self.thought_bubble.show(LOG_WARNING_TEXT)

    def trigger_dark_event(self) -> None:
        self.dark_event_triggered = True
        self.dark_solved = False
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.dark_challenge.start()
        self.thought_bubble.show(DARKNESS_HINT_TEXT)
        if self.dialogue.active:
            self.dialogue.hide()

    def trigger_peak_event(self) -> None:
        """Az 5. jelenet beindítása: aktiváljuk a sziklacsúcsot és intro üzenetet mutatunk.

        A játékos a triggerpontról még tovább kell sétáljon, amíg a kockák alá ér -
        ez ad egy természetes "rácsodálkozás" pillanatot. A láthatatlan fal akadályozza
        meg, hogy egyszerűen elsétáljon a csúcs alatt: csak a kockákon át vezet az út.
        """
        self.peak_event_triggered = True
        self.peak.activate()
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.dialogue.show(PEAK_INTRO_TEXT)

    def trigger_wind_event(self) -> None:
        """A 7. jelenet indítása a Göncöl-szekér jelenet lezárása után."""
        self.wind_event_triggered = True
        self.wind_solved = False
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.was_movement_pressed = False
        self.player.start_animation("idle")
        self.thought_bubble.hide_immediately()

        if self.dialogue.active:
            self.dialogue.hide()

        self.wind.start(
            self.player.world_x,
            self.camera_x,
            self.config.width,
            ground_y=int(self.floor_y_for_player()),
        )
        self.dialogue.show(WIND_INTRO_TEXT)

    def set_game_over(self, text: str = GAME_OVER_TEXT) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.player.vx = 0.0
        self.player.movement_pressed = False
        self.player.start_animation("idle")
        self.thought_bubble.hide_immediately()
        self.dialogue.show(text, hint_text="Esc - kilépés")

    def update_cinematic_camera(self, dt: float) -> bool:
        if not self.cinematic_camera_active:
            return False
        distance = self.cinematic_camera_target_x - self.camera_x
        step = OBSTACLE_CAMERA_REVEAL_SPEED * dt
        if abs(distance) <= step + OBSTACLE_CAMERA_REVEAL_EPSILON:
            self.camera_x = self.cinematic_camera_target_x
            self.cinematic_camera_active = False
            if self.pending_obstacle_text:
                self.dialogue.show(self.pending_obstacle_text)
                self.pending_obstacle_text = ""
        else:
            self.camera_x += math.copysign(step, distance)
        return True

    def update_log_camera_transition(self, dt: float) -> bool:
        """Finom kameraátmenet a harmadik kihívás elején.

        A normál kamerakövetés 9.0-s smoothness-szel dolgozik, ami jó játék közben,
        de nézetváltásnál túl hirtelennek érződik. Itt külön, lassabb értékkel
        ease-out módon közelítjük a célpozíciót.
        """
        if not self.log_camera_transition_active:
            return False
        target_camera_x = self.log_camera_transition_target_x
        distance = target_camera_x - self.camera_x
        if abs(distance) <= LOG_CAMERA_CENTER_EPSILON:
            self.camera_x = target_camera_x
            self.log_camera_transition_active = False
            self.rolling_log.spawn_from_screen_right(self.camera_x, self.config.width)
            return True

        smooth_factor = 1.0 - math.exp(-LOG_CAMERA_CENTER_SMOOTHNESS * dt)
        self.camera_x += distance * smooth_factor
        return True

    def _target_camera_y(self) -> float:
        """A vertikális kamera célpozíciója.

        Csak a sziklacsúcs jelenetben mozog: amikor a játékos a "deadzone" felett
        van (a talajtól számítva több mint PEAK_VERTICAL_DEADZONE * képernyőmagasság),
        a kamera követi felfelé. Egyébként 0 (nincs scroll).
        """
        if not self.peak_event_triggered:
            return 0.0
        deadzone_height = self.config.height * PEAK_VERTICAL_DEADZONE
        target_screen_y = int(self.config.height * PEAK_VERTICAL_CAMERA_BIAS)
        # Ha a játékos még a deadzone-on belül van (a talaj közelében), nincs scroll.
        if self.player.y >= self.config.ground_top_y - deadzone_height:
            return 0.0
        # Egyébként a kamera úgy csúszik, hogy a játékos kb. a képernyő felső
        # részén-középén legyen, így mindig látszódjon, mi következik felfelé.
        raw = self.player.y - target_screen_y
        # Ne mehessen lefelé (camera_y > 0 lefelé scroll lenne, az itt nem értelmes).
        return min(0.0, raw)

    def _update_camera_y(self, dt: float) -> None:
        target = self._target_camera_y()
        smooth = 1.0 - math.exp(-self.config.camera_smoothness * dt)
        self.camera_y += (target - self.camera_y) * smooth

    def update_camera(self, dt: float) -> None:
        if self.update_cinematic_camera(dt):
            self._update_camera_y(dt)
            return
        if self.update_log_camera_transition(dt):
            self._update_camera_y(dt)
            return
        if self.dialogue.active:
            self._update_camera_y(dt)
            return
        if self.log_event_triggered and not self.log_solved and not self.game_over:
            # A harmadik kihívás alatt a kamera a farkast tartja középen,
            # hogy a jobbról érkező farönk jól látható legyen. Ez már a
            # beállt kamera utáni követés, ezért maradhat fürgébb.
            target_camera_x = self.centered_camera_x_for_player()
            smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
            self.camera_x += (target_camera_x - self.camera_x) * smooth_factor
            self._update_camera_y(dt)
            return
        if self.wind_event_triggered and not self.wind_solved and not self.game_over:
            # A szél-jelenetben középen tartjuk a farkast, hogy a jobbról érkező
            # ágak időben látszódjanak.
            target_camera_x = self.centered_camera_x_for_player()
            smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
            self.camera_x += (target_camera_x - self.camera_x) * smooth_factor
            self._update_camera_y(dt)
            return
        screen_x = self.player.world_x - self.camera_x
        target_camera_x = self.camera_x
        # JAVÍTÁS: a target a deadzone SZÉLÉN tartja a játékost, nem a center_x-en.
        # Korábban a center_x-re ugrott a target, így a játékos folyamatosan a
        # right_edge_x és center_x között "lebegett" - ez okozta az akadósságot.
        # Most: amint átlép, a target a játékossal együtt halad fix offsettel.
        if screen_x > self.config.right_edge_x:
            target_camera_x = self.player.world_x - self.config.right_edge_x
        elif screen_x < self.config.left_frame_x and self.camera_x > 0:
            target_camera_x = self.player.world_x - self.config.left_frame_x
        target_camera_x = max(0.0, target_camera_x)
        smooth_factor = 1.0 - math.exp(-self.config.camera_smoothness * dt)
        self.camera_x += (target_camera_x - self.camera_x) * smooth_factor
        self._update_camera_y(dt)

    def handle_mouse_click(self, mouse_pos: tuple[int, int]) -> None:
        """Egér-kattintás kezelése: a bozót weak spotjának keresése."""
        if not self.bush_event_triggered or self.bush_solved:
            return
        if self.dialogue.active or self.cinematic_camera_active:
            return
        mouse_screen_x, mouse_screen_y = mouse_pos
        # A kamera csak X-ben offsetet csinál, Y nem.
        world_x = mouse_screen_x + self.camera_x
        world_y = float(mouse_screen_y)
        if self.bush.is_weak_spot_hit(world_x, world_y):
            self.bush_solved = True
            self.bush.collapse()
            self.thought_bubble.hide_immediately()
            self.dialogue.show(BUSH_COLLAPSE_TEXT)

    def draw_intro(self) -> None:
        if self.state == "about":
            self.menu.draw_about(self.screen, self.music_enabled, self.music_available, self.music_path_found)
        else:
            self.menu.draw_menu(self.screen)
        pygame.display.flip()

    def draw_help(self) -> None:
      if self.state != "playing" or self.dialogue.active:
        return
      if self._help_surface is None or self._help_bg is None:
        return
      self.screen.blit(self._help_bg, (18, 18))
      self.screen.blit(self._help_surface, (29, 25))

    def draw(self) -> None:
        self.background.draw_sky(self.screen, self.camera_y)
        # Sziklacsúcs jelenet háttér-rétege (csillagok + sziluett) - az ég után, minden más elé
        self.peak.draw_silhouette(self.screen, self.camera_x, self.camera_y)
        self.bush.draw(self.screen, self.camera_x)
        self.background.draw_ground(self.screen, self.camera_x, self.camera_y)
        # Tó a ground UTÁN, hogy lefedje a vízfelszín alatti talajt.
        self.lake.draw(self.screen, self.camera_x)
        self.rolling_log.draw(self.screen, self.camera_x)
        if self.wind_event_triggered:
            self.wind.draw(self.screen, self.camera_x, self.camera_y)
        # Sziklacsúcs platformjai - a talaj előtt, de a játékos mögött
        self.peak.draw_platforms(self.screen, self.camera_x, self.camera_y)
        self.player.draw(self.screen, self.camera_x, self.camera_y)
        if self.dark_challenge.is_visible():
            self.dark_challenge.draw_trace(self.screen)
            self.dark_challenge.draw_darkness(self.screen, pygame.mouse.get_pos())
        # Vizuális overlay-k a játékos feje fölött:
        player_screen_x = round(self.player.world_x - self.camera_x)
        player_screen_y = round(self.player.y - self.camera_y)
        player_top_y = player_screen_y - SPRITE_HEIGHT
        # Gondolatfelhő anchor: a farkas közepétől kicsit JOBBRA, fej magasságában.
        # A buborék MAGA jobbra-fent jelenik meg, a tail bal-lefelé visszamutat.
        bubble_anchor = (player_screen_x + 5, player_top_y + 35)
        self.thought_bubble.draw(self.screen, bubble_anchor)
        # Willpower-sáv: a fej fölött középen, csak a tó akadálynál látható.
        if self.lake_event_triggered and not self.lake_solved:
            wp_anchor = (player_screen_x, player_top_y - 18)
            self.willpower.draw(self.screen, wp_anchor)
        if (self.state == "playing" and not self.dialogue.active
            and not self.dark_challenge.is_visible()
            and not self.constellation.is_visible()):
            self.draw_help()
        self.draw_music_status()
        # Csillagkép-kihívás: a háttér-csillagok és platformok FÖLÉ rajzolva,
        # de a dialógus ALATT - hogy az emlékezető-szöveg ne legyen takarva.
        self.constellation.draw(self.screen)
        self.dialogue.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            # dt clamp: ha a frame megakad (pl. fókuszváltás miatt), ne ugorjon a játék.
            dt = min(self.clock.tick(FPS) / 1000.0, MAX_FRAME_DT)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                if self.state != "playing":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if self.state == "about":
                                self.state = "menu"
                            else:
                                self.running = False
                        elif self.state == "menu":
                            if event.key == pygame.K_UP:
                                self.menu.move_selection(-1)
                            elif event.key == pygame.K_DOWN:
                                self.menu.move_selection(1)
                            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                                self.activate_menu_option(self.menu.selected_index)
                        elif self.state == "about" and event.key in (pygame.K_RETURN, pygame.K_BACKSPACE):
                            self.state = "menu"
                    elif self.state == "menu" and event.type == pygame.MOUSEMOTION:
                        hovered = self.menu.option_at(event.pos)
                        if hovered is not None:
                            self.menu.selected_index = hovered
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.state == "menu":
                            clicked = self.menu.option_at(event.pos)
                            if clicked is not None:
                                self.menu.selected_index = clicked
                                self.activate_menu_option(clicked)
                        elif self.state == "about":
                            self.state = "menu"
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_RETURN and self.dialogue.active and not self.game_over:
                        self.dialogue.hide()
                        if self.wind_outro_active:
                            self.running = False
                    elif event.key == pygame.K_m:
                        self.toggle_music()
                    elif event.key == pygame.K_a and self.controls_enabled() and self.player.on_ground:
                        self.player.start_howl()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                    if self.dark_challenge.handle_event(event):
                        self.dark_solved = True
                        self.thought_bubble.hide_immediately()
                    elif self.constellation.active and not self.constellation.solved:
                        self.constellation.handle_event(event)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self.handle_mouse_click(event.pos)

            if self.state != "playing":
                self.draw_intro()
                continue

            self._start_music_if_needed()

            # Akadály-trigger ellenőrzés: csak az aktuálisan releváns akadály.
            if not self.game_over:
                if not self.bush_event_triggered and self.player.world_x >= self.bush.trigger_x():
                    self.trigger_bush_event()
                elif (self.bush_solved and not self.lake_event_triggered
                      and self.player.world_x >= self.lake.trigger_x()):
                    self.trigger_lake_event()
                elif (self.lake_solved and not self.log_event_triggered
                      and self.player.world_x >= LOG_CHALLENGE_WORLD_X):
                    self.trigger_log_event()
                elif (self.log_solved and not self.dark_event_triggered
                      and self.player.world_x >= DARK_CHALLENGE_WORLD_X):
                    self.trigger_dark_event()
                elif (self.dark_solved and not self.peak_event_triggered
                      and self.player.world_x >= PEAK_CHALLENGE_WORLD_X):
                    self.trigger_peak_event()

            if (not self.game_over
                and self.constellation_phase == "done"
                and not self.dialogue.active
                and not self.wind_event_triggered
                and self.player.world_x >= WIND_CHALLENGE_WORLD_X):
                self.trigger_wind_event()

            blocked = self.movement_blocked()
            self.player.handle_input(dt, self.obstacle_left_edge(), self.controls_enabled(), blocked)
            # Bozót: gondolatfelhő ha próbálkozik mozogni.
            if blocked and self.player.tried_to_move and not self.dialogue.active:
                self.thought_bubble.show(BLOCKED_THOUGHT_TEXT)

            # Sziklacsúcs jelenet: ha a játékos a falnak nyomódik, mutassunk egy hint-et.
            if (self.peak_event_triggered and not self.peak_solved
                and not self.dialogue.active and self.player.tried_to_move
                and self.peak.player_blocked_by_wall(self.player.world_x, self.player.collision_half_width)
                and self.player.on_ground):
                self.thought_bubble.show(PEAK_BLOCKED_HINT_TEXT)

            # Tó: csökönyös jobbra-nyomás számolása.
            self._update_lake_hold(dt)

            self.player.update_physics(dt, floor_y=self.floor_y_for_player())
            self.player.update_animation(dt)
            self.bush.update(dt)
            self.lake.update(dt)
            self.rolling_log.update(dt, self.camera_x)
            if self.rolling_log.active and self.rolling_log.collides_with_player(self.player):
                self.set_game_over()
            if self.rolling_log.solved:
                self.log_solved = True
            if self.wind_event_triggered and not self.wind_solved:
                self.wind.update(
                    dt,
                    self.camera_x,
                    self.config.width,
                    self.player.world_x,
                    paused=self.dialogue.active or self.game_over,
                )

                if not self.game_over and not self.dialogue.active:
                    if self.wind.reached_cave(self.player.world_x):
                        self.wind_solved = True
                        self.wind_outro_active = True
                        self.wind.solve()
                        self.player.vx = 0.0
                        self.player.movement_pressed = False
                        self.player.was_movement_pressed = False
                        self.player.start_animation("idle")
                        self.dialogue.show(WIND_SUCCESS_TEXT, hint_text="Enter - kilépés")
                    elif self.wind.collides_with_player(self.player):
                        self.set_game_over(WIND_GAME_OVER_TEXT)

            self.dark_challenge.update(dt)
            if self.dark_challenge.active and not self.dark_challenge.solved:
                self.thought_bubble.show(DARKNESS_HINT_TEXT)
            if self.dark_challenge.solved:
                self.dark_solved = True
            # Csillagkép-kihívás frissítése
            self.constellation.update(dt)
            # Detektáljuk, ha most fejezte be (drawing → completed_pending átmenet)
            if self.constellation_phase == "drawing" and self.constellation.solved:
                # A megoldás után rövid pulzáló csillag-glow effekt látható,
                # majd jön a befejező dialógus. A pulzálási idő után átkapcsolunk.
                if self.constellation.completion_pulse_t >= 1.4:
                    self.constellation.active = False
                    self.constellation_phase = "completed_pending"
            # Csúcs elérése: a játékos felért, leültetjük és megkezdjük a záró
            # jelenetet. A peak_solved most azt jelzi, hogy felértünk - az ezt
            # követő constellation_phase átmenetek vezetik tovább a jelenetet.
            if (self.peak_event_triggered and not self.peak_solved
                and self.peak.is_on_summit(self.player.world_x, self.player.y, self.player.on_ground)):
                self.peak_solved = True
                self.peak.solved = True
                self.thought_bubble.hide_immediately()
                # Megállítjuk a játékost és átkapcsolunk az ülő képkockára.
                self.player.vx = 0.0
                self.player.vy = 0.0
                self.player.movement_pressed = False
                self.player.was_movement_pressed = False
                # A megfelelő irányú ülés: a játékos arrafelé néz, amerre éppen
                # a csúcs felé haladt - ezt a `facing_right` már tartja.
                self.player.start_animation("sitting")
                self.constellation_phase = "sit"
                self.dialogue.show(PEAK_SUCCESS_TEXT)
            # Constellation fázis-átmenetek: a dialógus záródásakor lépünk tovább.
            self._update_constellation_phase()
            self.thought_bubble.update(dt)
            # A willpower-sáv csak akkor "él", ha aktív tó-akadály van.
            wp_target = (self.lake_hold_timer / LAKE_HOLD_DURATION
                         if (self.lake_event_triggered and not self.lake_solved)
                         else 0.0)
            self.willpower.update(wp_target, dt)
            self.update_camera(dt)
            self.draw()
        self._stop_music()
        pygame.quit()

    def _update_constellation_phase(self) -> None:
        """Vezeti a 6. (záró) jelenet fázis-átmeneteit.

        A fázisok mindig egy dialógus-bezárás után lépnek tovább. A
        `peak_solved=True` az első ilyen átmenet előfeltétele (csak akkor
        kezdődik, ha a játékos felért és leült).
        """
        if not self.peak_solved:
            return
        if self.dialogue.active:
            return
        if self.constellation_phase == "sit":
            # Az első dialógust ("Mostmár tisztán látom...") a játékos becsukta.
            # Most jön a memory-szöveg.
            self.dialogue.show(CONSTELLATION_INTRO_TEXT)
            self.constellation_phase = "memory"
            return
        if self.constellation_phase == "memory":
            # A memory-szöveget is elolvasta - induljon a csillag-rajzolás.
            self.constellation.start()
            self.constellation_phase = "drawing"
            return
        if self.constellation_phase == "drawing":
            # A drawing fázisból a constellation.solved figyelése lépteti tovább
            # (a run() ciklusban). Itt nincs teendő.
            return
        if self.constellation_phase == "completed_pending":
            # A megoldás után rövid pulzáló glow látszott, most a befejező szöveg.
            self.dialogue.show(CONSTELLATION_COMPLETE_TEXT)
            self.constellation_phase = "done"
            return

    def _update_lake_hold(self, dt: float) -> None:
        """A tó-puzzle "csökönyös jobbra-nyomás" számláló kezelése.

        Csak akkor ticelünk, ha:
          - aktív a tó-akadály ÉS még nem oldódott meg,
          - a játékos fizikailag a tó-élnek nyomódik (nem csak közelít),
          - a játékos jobbra-irányú gombot tartja,
          - a kontrollok engedélyezettek (nincs aktív dialógus / cinematic).

        Elengedéskor gyorsan visszaesik (LAKE_HOLD_DECAY), így TÉNYLEG
        folyamatosan kell tartani 5 másodpercig - ahogy a "csökönyös" szó
        sugallja.
        """
        if not self.lake_event_triggered or self.lake_solved:
            self.lake_hold_timer = 0.0
            return
        if not self.controls_enabled():
            return  # Dialógus alatt sem ticeljen, sem ne csökkenjen.

        keys = pygame.key.get_pressed()
        holding_right = keys[pygame.K_RIGHT]
        if holding_right and self.is_pressed_against_lake():
            self.lake_hold_timer = min(LAKE_HOLD_DURATION, self.lake_hold_timer + dt)
            if self.lake_hold_timer >= LAKE_HOLD_DURATION:
                self.lake_solved = True
                self.lake.solve()
                self.dialogue.show(LAKE_SOLVED_TEXT)
        else:
            self.lake_hold_timer = max(0.0, self.lake_hold_timer - dt * LAKE_HOLD_DECAY)


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
