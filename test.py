import requests
from PIL import Image, ImageDraw
from utils.database import Sessions
import numpy as np

# Both Y and X axis are flipped
# Height: -5 -> 4
# Width: -9 -> 8

full_map = Image.new("RGB", (18*512, 10*512))

for x in range(-9, 9):
    for y in range(-5, 5):
        with open(f'cache/{x}_{y}.png', 'wb') as f:
            print(f"Downloading {x}_{y}")
            f.write(requests.get(f"https://map.earthmc.net/tiles/minecraft_overworld/0/{x}_{y}.png").content)
        print(f"Placing {x}_{y}")
        full_map.paste(Image.open(f'cache/{x}_{y}.png'), ((x + 9) * 512, (y + 5) * 512))

# Top Left corner: 448, 480
# Bottom Right corner: 8743, 4623

full_map.crop((448, 480, 8743, 4623)).save("map.png")