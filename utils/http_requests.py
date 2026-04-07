import aiohttp

class HTTPRequester:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.api_url = "https://api.earthmc.net/v3/aurora"

    async def post_request(self, category: str, topic: str):
        async with self.session.post(f"{self.api_url}/{category}", json={"query": [topic]}) as resp:
            return await resp.json()

    async def get_request(self, category: str):
        async with self.session.get(f"{self.api_url}/{category}") as resp:
            return await resp.json()

    async def map_request(self):
        async with self.session.get("https://map.earthmc.net/tiles/players.json") as resp:
            return await resp.json()