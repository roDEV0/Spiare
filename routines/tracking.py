import discord
from discord import app_commands
from discord.ext import commands, tasks
import time
import datetime
from utils.database import Players, Sessions
import json
from PIL import Image, ImageDraw

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

    def cog_load(self):
        self.check_sessions.start()
        self.get_positions.start()
        self.update_map.start()

    @app_commands.command(name="sessions", description="Shows the most recent sessions of a player")
    async def sessions(self, interaction: discord.Interaction, player: str):
        player_obj = await Players.get_or_none(username=player)
        if not player_obj:
            await interaction.response.send_message(f"`{player}` is not registered")
            return

        sessions = await Sessions.filter(player=player_obj).order_by('-start_date').limit(10)

        def format_duration(total_seconds):
            total_seconds = int(total_seconds)
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        lines = []
        for session in sessions:
            start_ts = int(session.start_date.timestamp())
            duration = format_duration(session.total_time)
            lines.append(f"`#{session.id}` <t:{start_ts}:f> — {duration}")

        description = "\n".join(lines) if lines else "No sessions found."
        embed = discord.Embed(
            title=f"Recent Sessions — {player}",
            color=discord.Color.from_rgb(55, 120, 72),
            description=description,
        )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="replay-session", description="Replay a user's session using the session ID")
    async def replay_session(self, interaction: discord.Interaction, session_id: int):
        await interaction.response.defer()

        map_img = Image.open("map.png")
        draw_map = ImageDraw.Draw(map_img)

        session = await Sessions.get(id=session_id)
        player = await session.player
        positions = session.positions

        # EMC size: 66,360 x 33,148
        # Image size: 8,295 x 4,143

        prev_coords = None
        frames = []

        for index, position in reversed(list(enumerate(positions))):

            x_scaled = (position[0] * (8295 / 66360)) + 4147
            z_scaled = (position[2] * (4143 / 33148)) + 2071

            print(f"x: {x_scaled}, z: {z_scaled}")

            print(f"Original: {position}")

            if prev_coords:
                vertices = [(x_scaled, z_scaled), (prev_coords[0], prev_coords[1])]
                draw_map.line(vertices, fill=(0, 0, 0), width=4)

            draw_map.rounded_rectangle([(x_scaled-15, z_scaled-15), (x_scaled+15, z_scaled+15)], 5, (55, 148, 117) if index == (len(positions)-1) else (59, 34, 97), (0, 0, 0), 2)
            prev_coords = (x_scaled, z_scaled)

            resized_img = map_img.resize((2304, 1280), Image.Resampling.LANCZOS)
            frames.append(resized_img)

        durations = [700] * len(frames)
        durations[-1] = 1500

        frames[0].save(
            "animation.gif",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0
        )

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
        embed.add_field(name="Town", value=session.town or "None", inline=True)
        embed.add_field(name="Duration", value=duration_str, inline=True)
        embed.add_field(name="Positions Recorded", value=str(len(positions)), inline=True)
        embed.add_field(name="Started", value=f"<t:{start_ts}:F>", inline=False)
        if session.first_session:
            embed.set_footer(text="First session")
        embed.set_image(url="attachment://animation.gif")

        image_file = discord.File("animation.gif", filename="animation.gif")
        await interaction.followup.send(embed=embed, file=image_file)

    @tasks.loop(minutes=5)
    async def check_sessions(self):
        print("Checking for new players...")
        online_players = await self.bot.http_requester.get_request("online")
        online_names = {player["name"] for player in online_players["players"]}

        new_players = online_names - set(self.sessions)
        lost_players = set(self.sessions) - online_names

        for player in new_players:
            print(f"New player detected: {player}")
            self.sessions[player] = Session(player)

        # lost_players_data = await self.bot.http_requester.post_request_batch("players", lost_players)

        for player in lost_players:
            print(f"Player left: {player}")
            session = self.sessions.pop(player)
            player_name, start_date, total_time, positions = session.end()
            player_data = await self.bot.http_requester.post_request("players", player_name)
            print(f"player_data: {player_data}")

            player_town = player_data[0]["town"]["name"]

            player_obj, _ = await Players.get_or_create(username=player_name)
            player_obj.town = player_town
            await player_obj.save()

            position_json = json.dumps(positions)
            datetime_start = datetime.datetime.fromtimestamp(start_date)

            # The API returns milliseconds which you need to convert to seconds
            first_session = True if (start_date - (player_data[0]["timestamps"]["registered"]/1000)) < (60 * 5) else False

            await Sessions.create(player=player_obj, town=player_town, start_date=datetime_start, total_time=total_time, positions=position_json, first_session=first_session)
            print("Created sessions")

    @tasks.loop(seconds=30)
    async def get_positions(self):
        print("Getting positions...")
        online_data = await self.bot.http_requester.map_request()
        for player in online_data["players"]:
            if player["name"] in self.sessions:
                self.sessions[player["name"]].positions.append((player["x"], player["y"], player["z"]))


    @tasks.loop(hours=12)
    async def update_map(self):
        print("Updating map...")
        full_map = Image.new("RGB", (18 * 512, 10 * 512))

        for x in range(-9, 9):
            for y in range(-5, 5):
                with open(f'cache/{x}_{y}.png', 'wb') as f:
                    print(f"Downloading {x}_{y}")
                    grab_map = await self.bot.http_requester.map_tile_request(x, y)
                    f.write(grab_map)
                print(f"Placing {x}_{y}")
                full_map.paste(Image.open(f'cache/{x}_{y}.png'), ((x + 9) * 512, (y + 5) * 512))

        # Top Left corner: 448, 480
        # Bottom Right corner: 8743, 4623

        full_map.crop((448, 480, 8743, 4623)).save("map.png")

    @check_sessions.before_loop
    async def before_update_inactive(self):
        print("Withholding Check Sessions loop until bot is ready...")
        await self.bot.wait_until_ready()

    @get_positions.before_loop
    async def before_update_inactive(self):
        print("Withholding Get Positions loop until bot is ready...")
        await self.bot.wait_until_ready()

    @update_map.before_loop
    async def before_update_inactive(self):
        print("Withholding Update Map loop until bot is ready...")
        await self.bot.wait_until_ready()