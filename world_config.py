"""A pálya méretarányos konfigurációja - egyszer hozzuk létre, és mindenki ezt használja."""
from __future__ import annotations


class WorldConfig:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.left_frame_x = max(55, int(width * 0.075))
        # Jobbra haladásnál korábban kezdjen tolódni a pálya, hogy több tér
        # látszódjon a farkas előtt. Régebben 0.82 volt, emiatt a kamera csak
        # akkor indult, amikor a játékos már túl közel volt a képernyő jobb széléhez.
        self.right_edge_x = int(width * 0.64)
        # Magasabb érték -> kisebb steady-state lemaradás a játékos mögött.
        # 9.0 esetén lag = v_player / 9.0 = 300/9 ≈ 33 px (4.8-nál még 62 px volt).
        self.camera_smoothness = 9.0
        self.ground_top_y = int(height * 0.885)
        self.ground_cap_height = max(12, int(height * 0.022))
