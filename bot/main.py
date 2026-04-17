import time
import aiohttp
import discord
from discord.ext import commands
import os
import dotenv
from tortoise import Tortoise
from shared.http_requests import HTTPRequester
from bot.commands.tracking import Tracking
from bot.routines.citizens import Citizens


class BotContainer(commands.Bot):
    def __init__(self, nation: str):
        dotenv.load_dotenv(override=False)

        super().__init__(command_prefix="!", intents=discord.Intents(messages=True, guilds=True, members=True, message_content=True))
        self.current_time = time.time()

        self.database_url = os.environ.get("DATABASE_URL")
        self.session = None
        self.http_requester = None

        self.nation = nation

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.http_requester = HTTPRequester(self.session)
        await Tortoise.init(db_url=self.database_url, modules={"models": ["shared.database"]})
        try:
            conn = Tortoise.get_connection("default")
            await conn.execute_query("SELECT 1")
            print("Connection test successful!")
        except Exception as e:
            print(f"Connection test failed: {e}")

        await self.add_cog(Tracking(self))
        await self.add_cog(Citizens(self))
        print("Routines loaded!")

        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}!")
        await self.tree.sync()

    async def close(self):
        await super().close()
        await Tortoise.close_connections()
        if self.session:
            await self.session.close()

bot = BotContainer(nation="Panama")
bot.run(os.environ.get("TOKEN"))