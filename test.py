import requests

map_data = requests.get("https://map.earthmc.net/tiles/players.json")
print(map_data.json())