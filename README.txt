Ugrás animáció méretjavítás

Fájlok:
- main.py
- assets/wolf_jump_sheet.png

Mit változtattam:
- Az ugrás animáció a mellékelt wolf_run_0063.png stance kép forrásmagasságához van igazítva.
- A jump sprite sheet világos/rácsos háttere erősebben törlődik.
- Az ugrás képkockák nem külön-külön 120 px magasra vannak felnagyítva, hanem fix skálával,
  ezért a csukott/nyújtott pózok megtartják az arányukat, és nem lesznek kicsik.
- A játékbeli karakter-méretet továbbra is a SPRITE_HEIGHT állítja a main.py tetején.

Használat:
1. A main.py cserélje le a régi main.py fájlodat.
2. Az assets/wolf_jump_sheet.png kerüljön az assets mappába.
3. A meglévő wolf_run_0001.png ... wolf_run_0063.png fájlokat hagyd az assets mappában.
