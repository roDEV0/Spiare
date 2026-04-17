import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
import datetime
from shared.database import Players, Sessions, Towns
import json
from PIL import Image, ImageDraw
import asyncio
import tempfile
import os

class Session:
    def __init__(self, player: str):
        self.player = player
        self.start_time = time.time()
        self.positions = []

    def end(self):
        end_time = time.time()

        # start_date = datetime.datetime.fromtimestamp(self.start_time)
        total_time = end_time - self.start_time

        return self.player, self.start_time, total_time, self.positions

class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sessions = {}
        self.online_players = []

    @app_commands.command(name="sessions", description="Shows the most recent sessions of a player")
    async def sessions(self, interaction: discord.Interaction, player: str = None):
        await interaction.response.defer()

        if player:
            player_obj = await Players.get_or_none(username=player)
            if not player_obj:
                await interaction.response.send_message(f"`{player}` is not registered")
                return

            sessions = await Sessions.filter(player=player_obj).order_by('-id').limit(10)
        else:
            sessions = await Sessions.all().prefetch_related("player").order_by('-id').limit(10)

        def format_duration(total_seconds):
            total_seconds = int(total_seconds)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        lines = []
        for session in sessions:
            start_ts = int(session.start_date.timestamp())
            duration = format_duration(session.total_time)
            if player:
                lines.append(f"`#{session.id}` <t:{start_ts}:f> — {duration}")
            else:
                player_obj = session.player
                lines.append(f"`#{session.id}`: {player_obj.username} - <t:{start_ts}:f> — {duration}")

        description = "\n".join(lines) if lines else "No sessions found."
        embed = discord.Embed(
            title=f"Recent Sessions — {player if player else 'All Sessions'}",
            color=discord.Color.from_rgb(55, 120, 72),
            description=description,
        )

        await interaction.followup.send(embed=embed)


    @app_commands.command(name="replay-session", description="Replay a user's session using the session ID")
    async def replay_session(self, interaction: discord.Interaction, session_id: int):
        await interaction.response.defer()

        session = await Sessions.get_or_none(id=session_id).prefetch_related("player", "town")
        if not session:
            await interaction.followup.send("Session does not exist")
            return

        player = session.player
        positions = session.positions

        # EMC size: 129,024 x 64,512
        # Image size: 4096 x 2048

        gif_path = await asyncio.to_thread(self._generate_map, positions)

        total_seconds = int(session.total_time)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        start_ts = int(session.start_date.timestamp())

        embed = discord.Embed(
            title=f"Session #{session_id} Replay",
            color=discord.Color.from_rgb(55, 120, 72),
        )
        embed.set_author(name=player.username)
        embed.add_field(name="Town", value=session.town.name or "None", inline=True)
        embed.add_field(name="Duration", value=duration_str, inline=True)
        embed.add_field(name="Positions Recorded", value=str(len(positions)), inline=True)
        embed.add_field(name="Started", value=f"<t:{start_ts}:F>", inline=False)
        if session.first_session:
            embed.set_footer(text="First session")
        embed.set_image(url="attachment://animation.gif")

        image_file = discord.File(gif_path, filename="animation.gif")
        await interaction.followup.send(embed=embed, file=image_file)
        os.remove(gif_path)

    def _generate_map(self, positions: list):
        map_img = Image.open("shared/map.png")
        draw_map = ImageDraw.Draw(map_img)

        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
            tmp_path = tmp.name

        prev_coords = None
        frames = []

        if len(positions) > 100:
            step = len(positions) / 100
            positions = [positions[int(i * step)] for i in range(100)]

        for index, position in (enumerate(positions)):

            x_scaled = (position[0] * (4096 / 129024)) + 2058
            z_scaled = (position[2] * (2048 / 64512)) + 1024

            print(f"x: {x_scaled}, z: {z_scaled}")

            print(f"Original: {position}")

            if prev_coords:
                vertices = [(x_scaled, z_scaled), (prev_coords[0], prev_coords[1])]
                draw_map.line(vertices, fill=(0, 0, 0), width=4)

            draw_map.rounded_rectangle([(x_scaled - 15, z_scaled - 15), (x_scaled + 15, z_scaled + 15)], 5, (55, 148, 117) if index == 0 else (59, 34, 97), (0, 0, 0), 2)
            prev_coords = (x_scaled, z_scaled)

            frames.append(map_img.copy())

        if not frames:
            frames.append(map_img)

        durations = [700] * len(frames)
        durations[-1] = 1500

        frames[0].save(
            tmp_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0
        )

        return tmp_path