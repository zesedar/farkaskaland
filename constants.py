"""A játék minden konstansa egyetlen helyen, a karbantartást megkönnyítendő."""
from __future__ import annotations

# --- Alap fizika és időzítés ---
FPS = 60
PLAYER_SPEED = 300
SPRITE_HEIGHT = 120
JUMP_SPEED = 780
GRAVITY = 1500
MAX_FALL_SPEED = 1100
MAX_FRAME_DT = 0.05  # frame-spike clamp, hogy ne ugorjon a játék

# --- Animáció ---
REFERENCE_STANCE_SOURCE_HEIGHT = 328
JUMP_SHEET_FILENAME = "wolf_jump_sheet.png"
JUMP_SHEET_COLUMNS = 4
JUMP_SHEET_ROWS = 2
JUMP_ASCEND_FRAME_TIME = 0.12
JUMP_DESCEND_FRAME_TIMES = [0.10, 0.38, 0.15, 0.14]

FRAME_FILE_PREFIX = "wolf_run_"
FRAME_FILE_EXTENSION = ".png"
FRAME_FILE_DIGITS = 4
TOTAL_FRAME_COUNT = 63
RUN_START_FRAME = 0
RUN_END_FRAME = 43
STOP_START_FRAME = 44
STOP_END_FRAME = 62
ANIMATION_FRAME_TIME = 0.07
FAST_STOP_FILE_START = 52
FAST_STOP_FILE_END = 59
FAST_STOP_FRAME_TIME = 0.002

# Ülő frame (6. jelenet) - opcionális assets fájl
SITTING_FRAME_FILENAME = "ulelorenez.png"

# --- Sprite-feldolgozás (zöld háttér transzparenciára cserélése) ---
GREEN_ALPHA_MIN_GREEN = 70
GREEN_ALPHA_DOMINANCE = 28

# --- Szövegek ---
WINDOW_TITLE = "Farkas kaland"
INTRO_TEXT = "Valami azt súgja, meg kell találnom a békémet..."
THORN_TEXT = "Néha csak úgy juthatunk tovább, ha megtaláljuk a legszűkebb járható ösvényt."
BLOCKED_THOUGHT_TEXT = "Valahogy át kellene jutnom..."
BUSH_COLLAPSE_TEXT = "Egy apróságon múlt az egész."
LAKE_TEXT = "Hinnünk kell magunkban..."
LAKE_SOLVED_TEXT = "... és nem lesznek akadályok."
LOG_WARNING_TEXT = "Veszélyt érzek!"
GAME_OVER_TEXT = "Játék vége! A farönk elsodort."
DARKNESS_HINT_TEXT = "E jelben győzni fogsz"
PEAK_INTRO_TEXT = "Fel kell jutnom a csúcsra, hogy lássam a csillagokat."
PEAK_SUCCESS_TEXT = "Mostmár tisztán látom a csillagokat."
PEAK_BLOCKED_HINT_TEXT = "Csak a csúcs felé vezet az út..."
CONSTELLATION_INTRO_TEXT = "Emlékszem egy csillagképre, egy szekérről..."
CONSTELLATION_COMPLETE_TEXT = "Pont olyan, amilyennek emlékeztem rá."

# --- Kamera (akadály-reveal és sziklacsúcs) ---
OBSTACLE_CAMERA_REVEAL_SPEED = 230.0
OBSTACLE_CAMERA_REVEAL_EPSILON = 1.0
LOG_CAMERA_CENTER_SMOOTHNESS = 2.6
LOG_CAMERA_CENTER_EPSILON = 0.75

# --- 1. kihívás: tövises bozót ---
WEAK_SPOT_RADIUS = 2  # 2 px sugár a hit-detectionhez
WEAK_SPOT_MIN_ALPHA = 110  # csak elég látható pixel lehet weak spot
WEAK_SPOT_MARKER_COLOR = (220, 30, 30, 255)  # 2x2 piros marker a bozóton
BUSH_COLLAPSE_RATE = 1.4  # 1/sec - kb. 0.7s teljes összeomlás
THOUGHT_BUBBLE_FADE_SPEED = 5.0
THOUGHT_BUBBLE_VISIBLE_TIME = 1.6

# --- 2. kihívás: tó (csökönyösség-mérce) ---
LAKE_HOLD_DURATION = 5.0  # másodperc - meddig kell csökönyösen jobbra nyomni
LAKE_HOLD_DECAY = 2.0  # gyors visszaesés ha elengedik
LAKE_WORLD_X = 5500
LAKE_BLOCK_EPSILON = 0.5  # float-pontosság a "blokkolva van" detektáláshoz

# --- 3. kihívás: gördülő farönk ---
LOG_CHALLENGE_WORLD_X = 7400
LOG_SPEED = 390.0
LOG_RADIUS_BASE = 44
LOG_COLLISION_PADDING_X = 10
LOG_SAFE_CLEARANCE_EXTRA = 16

# --- 4. kihívás: sötétség és kereszt-jel ---
DARK_CHALLENGE_WORLD_X = 8350
DARKNESS_MAX_ALPHA = 255
DARKNESS_FADE_IN_SPEED = 320.0
DARKNESS_FADE_OUT_SPEED = 430.0
SPOTLIGHT_RADIUS_BASE = 46
CROSS_GESTURE_MIN_SPAN_BASE = 145
CROSS_GESTURE_TOLERANCE_BASE = 18
CROSS_GESTURE_MIN_POINTS = 18

# --- 5. kihívás: sziklacsúcs (platformer) ---
PEAK_CHALLENGE_WORLD_X = 9700
PEAK_BASE_OFFSET_X = 420
PEAK_BLOCK_WIDTH_BASE = 110
PEAK_BLOCK_HEIGHT_BASE = 26
PEAK_SUMMIT_DETECT_TOLERANCE = 1.6
PEAK_CLIMB_SCREENS = 4.2
PEAK_VERTICAL_CAMERA_BIAS = 0.62
PEAK_VERTICAL_DEADZONE = 0.32

# --- 6. (záró) jelenet: csillagkép-rajzolás ---
CONSTELLATION_STAR_HIT_TOLERANCE_BASE = 48
CONSTELLATION_LINE_WIDTH_BASE = 3
# --- 7. jelenet: szél és barlang ---
WIND_CHALLENGE_WORLD_X = 11250
WIND_INTRO_TEXT = "Sietnem kell"
WIND_SUCCESS_TEXT = "Elértem az otthont!"
WIND_GAME_OVER_TEXT = "Játék vége! Az ág elsodort."

WIND_CAVE_DISTANCE = 2700
WIND_CAVE_REACH_TOLERANCE = 48
WIND_CAVE_WIDTH_BASE = 280
WIND_CAVE_HEIGHT_BASE = 185

WIND_FIRST_BRANCH_DELAY = 0.7
WIND_BRANCH_SPAWN_MIN = 0.95
WIND_BRANCH_SPAWN_MAX = 1.45
WIND_BRANCH_SPEED = 450.0
WIND_BRANCH_THICKNESS_BASE = 20
WIND_LOW_BRANCH_LENGTH_BASE = 145
WIND_HIGH_BRANCH_LENGTH_BASE = 170
WIND_HIGH_BRANCH_MIN_OFFSET_BASE = 160
WIND_HIGH_BRANCH_MAX_OFFSET_BASE = 215
WIND_COLLISION_PADDING_X = 8
