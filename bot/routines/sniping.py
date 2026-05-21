from discord.ext import tasks, commands
from shared.http_requests import post_request, get_request
import time
from bot.main import BotContainer

class Sniping(commands.Cog):
    def __init__(self, bot: BotContainer):
        self.bot = bot
        self.snipe_towns = {}

        self.current_time = time.time()

        self.check_snipes.start()

    def cog_unload(self):
        self.snipe_towns.clear()

    @tasks.loop(hours=12)
    async def check_snipes(self):
        self.snipe_towns.clear()
        self.current_time = time.time()
        towns = await get_request(self.bot, "towns")

        for town in towns:
            town_data = await post_request(self.bot, "towns", town["name"])

            last_player = town_data["mayor"]["name"]
            player_data = await post_request(self.bot, "players", last_player)

            days_left = ((60 * 60 * 24 * 42) - (self.current_time - player_data["timestamps"]["lastOnline"])) / (60 * 60 * 24)

            self.snipe_towns[town_data["name"]] = (days_left, len(town_data["residents"]))