from pathlib import Path
import pygame


pygame.init()
BLACK = (0, 0, 0, 255)
BLUE = (0, 0, 255, 255)
DARK_GRAY = (40, 40, 40, 255)
GRAY = (150, 150, 150, 255)
GREEN = (0, 255, 0, 255)
BROWN = (97, 54, 19)
ORANGE = (255, 140, 0, 255)
RED = (255, 0, 0, 255)
WHITE = (255, 255, 255, 255)
YELLOW = (255, 255, 0, 255)

v_fonts = [pygame.font.Font(Path("client", "assets", "VT323", "VT323-Regular.ttf"), i) for i in range(101)]
