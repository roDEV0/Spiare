import discord
from discord import app_commands
from discord.ext import commands
from shared.discord_database import Config


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    set_group = app_commands.Group(name="set", description="Change server settings")

    @set_group.command(name="citizen_role", description="Sets the citizen role")
    async def set_citizen_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        config, _ = await Config.get_or_create(server_id=role.guild.id)
        config.citizen_role_id = role.id
        config.name = role.guild.name
        await config.save()
        await interaction.response.send_message(
            f"Citizen successfully changed to {role.mention}"
        )

    @set_group.command(name="admin_role", description="Sets the admin role")
    async def set_admin_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        config, _ = await Config.get_or_create(server_id=role.guild.id)
        config.name = role.guild.name
        config.admin_role_id = role.id
        await config.save()
        await interaction.response.send_message(
            f"Admin successfully changed to {role.mention}"
        )

    @set_group.command(name="foreigner_role", description="Sets the foreigner role")
    async def set_foreigner_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        config, _ = await Config.get_or_create(server_id=role.guild.id)
        config.name = role.guild.name
        config.foreigner_role_id = role.id
        await config.save()
        await interaction.response.send_message(
            f"Foreigner successfully changed to {role.mention}"
        )

    @set_group.command(name="verify_channel", description="Sets the verify channel")
    async def set_verify_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        config, _ = await Config.get_or_create(server_id=channel.guild.id)
        config.name = channel.guild.name
        config.verify_channel_id = channel.id
        await config.save()
        await interaction.response.send_message(
            f"Verify channel successfully changed to {channel.mention}"
        )

    @set_group.command(
        name="notifications_channel", description="Sets the notifications channel"
    )
    async def set_notif_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        config, _ = await Config.get_or_create(server_id=channel.guild.id)
        config.name = channel.guild.name
        config.notif_channel_id = channel.id
        await config.save()
        await interaction.response.send_message(
            f"Notifications channel successfully changed to {channel.mention}"
        )

    @set_group.command(name="nation", description="Sets the server nation")
    async def set_nation(self, interaction: discord.Interaction, nation: str):
        config, _ = await Config.get_or_create(server_id=interaction.guild.id)
        config.name = interaction.guild.name
        config.nation = nation
        await config.save()
        await interaction.response.send_message(
            f"Nation successfully changed to {nation}"
        )
