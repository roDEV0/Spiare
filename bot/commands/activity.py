from discord.ext import commands
from bot.main import BotContainer

class Activity(commands.Cog):
    def __init__(self, bot: BotContainer):
        self.bot = bot

    @commands.command(name="most-active", description="Shows the most active player in a given town")
    async def most_active(self, ctx, town: str):
        town_data = await self.bot.http_requester.post_request(self.bot, "towns", town)

        most_active = (None, None)

        for resident in town_data["residents"]:
            resident_data = await self.bot.http_requester.post_request(self.bot, "players", resident["name"])

            if resident_data["timestamps"]["lastOnline"] > most_active[1]:
                most_active = (resident["name"], resident_data["timestamps"]["lastOnline"])

        await ctx.send(f"The most active player in ```{town}``` is ```{most_active[0]}```")