import requests
from PIL import Image
from io import BytesIO

response = requests.get("https://map.earthmc.net/tiles/minecraft_overworld/0/-5_0.png")
img = Image.open(BytesIO(response.content))
img.show()
