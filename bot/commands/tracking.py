import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
from shared.database import Players, Sessions, Towns
from PIL import Image, ImageDraw
import asyncio
import tempfile
import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="sessions", description="Shows the most recent sessions of a player"
    )
    async def sessions(self, interaction: discord.Interaction, player: str = None):
        await interaction.response.defer()

        if player:
            player_obj = await Players.get_or_none(username=player)
            if not player_obj:
                await interaction.response.send_message(f"`{player}` is not registered")
                return

            sessions = (
                await Sessions.filter(player=player_obj).order_by("-id").limit(10)
            )
        else:
            sessions = await Sessions.all().order_by("-id").limit(10)

        def format_duration(total_seconds):
            total_seconds = int(total_seconds)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return (
                f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
            )

        lines = []
        for session in sessions:
            start_ts = int(session.start_date.timestamp())
            duration = format_duration(session.total_time)
            if player:
                lines.append(f"`#{session.id}` <t:{start_ts}:f> — {duration}")
            else:
                player_obj = await Players.get(id=session.player)
                lines.append(
                    f"`#{session.id}`: {player_obj.username} - <t:{start_ts}:f> — {duration}"
                )

        description = "\n".join(lines) if lines else "No sessions found."
        embed = discord.Embed(
            title=f"Recent Sessions — {player if player else 'All Sessions'}",
            color=discord.Color.from_rgb(55, 120, 72),
            description=description,
        )

        await interaction.followup.send(embed=embed)
