from discord.ext import tasks, commands
import time
from bot.main import BotContainer

class Citizens(commands.Cog):
    def __init__(self, bot: BotContainer):
        self.bot = bot

        self.citizen_list = []
        self.inactive_list = []
        self.current_time = time.time()

        self.check_citizens.start()
        self.update_inactive.start()

    def cog_unload(self):
        self.citizen_list.clear()
        self.inactive_list.clear()

    @tasks.loop(minutes=10)
    async def check_citizens(self):
        nation_data = await self.bot.http_requester.post_request("nations", self.bot.nation)
        updated_list = [resident["name"] for resident in nation_data["residents"]]
        active_citizens = list(set(self.citizen_list) - set(self.inactive_list))

        new_citizens = list(set(updated_list) - set(active_citizens)) # Players who have joined
        lost_citizens = list(set(active_citizens) - set(updated_list)) # Players who have left via /t leave

        # 42 days inactive
        new_inactive = []

        self.current_time = time.time()
        for citizen in active_citizens:
            player_data = await self.bot.http_requester.post_request("players", citizen)

            if self.current_time - player_data["timestamps"]["lastOnline"] > (60 * 60 * 24 * 42): # 42 days
                new_inactive.append(citizen)

        self.inactive_list = self.inactive_list + new_inactive

    @tasks.loop(hours=12)
    async def update_inactive(self):
        self.current_time = time.time()

        returning_citizens = []

        for inactive in self.inactive_list:
            player_data = await self.bot.http_requester.post_request("players", inactive)
            if self.current_time - player_data["timestamps"]["lastOnline"] < (60 * 60 * 24 * 42):
                returning_citizens.append(inactive)

        self.inactive_list = [c for c in self.inactive_list if c not in returning_citizens]

    @check_citizens.before_loop
    async def before_check_citizens(self):
        print("Withholding Check Citizen loop until bot is ready...")
        await self.bot.wait_until_ready()
        nation_data = await self.bot.http_requester.post_request("nations", self.bot.nation)
        self.citizen_list = [resident["name"] for resident in nation_data["residents"]]

    @update_inactive.before_loop
    async def before_update_inactive(self):
        print("Withholding Update Inactive loop until bot is ready...")
        await self.bot.wait_until_ready()