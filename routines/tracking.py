from discord.ext import commands, tasks
import time
import datetime
from utils.database import Players, Sessions
import json

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
            first_session = True if (start_date - (player_data[0]["timestamps"]["registered"]/1000)) < (60 * 10) else False

            await Sessions.create(player=player_obj, town=player_town, start_date=datetime_start, total_time=total_time, positions=position_json, first_session=first_session)

    @tasks.loop(seconds=10)
    async def get_positions(self):
        print("Getting positions...")
        online_data = await self.bot.http_requester.map_request()
        for player in online_data["players"]:
            if player["name"] in self.sessions:
                self.sessions[player["name"]].positions.append((player["x"], player["y"], player["z"]))

    @check_sessions.before_loop
    async def before_update_inactive(self):
        print("Withholding Check Sessions loop until bot is ready...")
        await self.bot.wait_until_ready()

    @get_positions.before_loop
    async def before_update_inactive(self):
        print("Withholding Get Positions loop until bot is ready...")
        await self.bot.wait_until_ready()