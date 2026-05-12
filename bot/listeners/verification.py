import discord
from discord.ext import tasks, commands
from discord import app_commands
from shared.discord_database import Config, Verifications

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        server_config = await Config.get_or_none(server_id=message.guild.id)
        if str(message.channel.id) != str(server_config.verify_channel_id):
            return

        username = message.content.split("\n")[0].strip()
        player_data = await self.bot.http_requester.post_request("players", username)

        channel = message.channel
        guild = message.guild


        if not player_data:
            await channel.send(f"**{username}** is not registered on the server")
            return

        is_citizen = (
                not server_config.nation
                or player_data[0]["nation"]["name"] == server_config.nation
        )

        minecraft_verified = await Verifications.filter(minecraft_uuid=player_data[0]["uuid"], server=server_config.id)
        discord_verified = await Verifications.filter(username=message.author.name, server=server_config.id)
        if minecraft_verified:
            await channel.send(f"**{username}** is already verified")
            return
        if discord_verified:
            await channel.send(f"You are already verified as **{discord_verified[0].minecraft_username}**")
            return

        if not is_citizen:
            await channel.send(f"Verifying **{username}** as a foreign citizen")
            await Verifications.create(
                user_id=message.author.id,
                username=message.author.name,
                minecraft_username=player_data[0]["name"],
                minecraft_uuid=player_data[0]["uuid"],
                town=player_data[0]["town"]["name"],
                server=server_config.id,
                citizen=False
            )
            role = discord.utils.get(guild.roles, id=server_config.foreigner_role_id)
        else:
            await channel.send(
                f"Verifying **{username}** as a citizen of {player_data[0]["nation"]["name"]}"
            )
            await Verifications.create(
                user_id=message.author.id,
                username=message.author.name,
                minecraft_username=player_data[0]["name"],
                minecraft_uuid=player_data[0]["uuid"],
                town=player_data[0]["town"]["name"],
                server=server_config.id,
                citizen=True
            )
            role = discord.utils.get(guild.roles, id=server_config.citizen_role_id)

        if role:
            member = await guild.fetch_member(message.author.id)
            nick = f"{player_data[0]['name']} | {player_data[0]["town"]["name"]}"
            await member.add_roles(role, reason="Verified")
            await member.edit(nick=nick)