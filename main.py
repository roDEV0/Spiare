import time
import aiohttp
import discord
from discord.ext import commands
import os
import dotenv
from tortoise import Tortoise
from utils.http_requests import HTTPRequester
import logging
from routines.tracking import Tracking

class BotContainer(commands.Bot):
    def __init__(self, nation: str):
        dotenv.load_dotenv()

        super().__init__(command_prefix="!", intents=discord.Intents(messages=True, guilds=True, members=True))
        self.current_time = time.time()

        self.database_url = os.getenv("DATABASE_URL")
        self.session = None
        self.http_requester = None

        self.nation = nation

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.http_requester = HTTPRequester(self.session)

        await Tortoise.init(db_url=self.database_url, modules={"models": ["utils.database"]})
        await Tortoise.generate_schemas()
        print("Database connection established!")

        await self.add_cog(Tracking(self))
        print("Routines loaded!")

    async def on_ready(self):
        print(f"Logged in as {self.user}!")

    async def close(self):
        await super().close()
        if self.session:
            await self.session.close()

bot = BotContainer(nation="Panama")
bot.run(os.getenv("TOKEN"))