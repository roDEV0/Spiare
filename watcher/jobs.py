from shared.database import Sessions, Players, Towns, Active
import json
import datetime
import time
import os
from PIL import Image
import tortoise
from io import BytesIO

class Session:
    def __init__(self, player: str):
        self.player = player
        self.start_time = time.time()
        self.positions = []
        self.tmp_obj = None

    @classmethod
    async def create(cls, player: str):
        session = cls(player)
        session.tmp_obj = await Active(player=player)
        return session

    @classmethod
    async def load(cls, active):
        session = cls(active.player)
        session.start_time = active.start_date.timestamp()
        session.tmp_obj = active
        session.positions = active.positions
        return session

    async def append_position(self, positions):
        self.positions.append(positions)
        self.tmp_obj.positions = self.positions
        await Active.update_or_create(
            defaults={"positions": self.tmp_obj.positions, "start_date": self.tmp_obj.start_date},
            player=self.tmp_obj.player
        )

    def end(self):
        end_time = time.time()

        # start_date = datetime.datetime.fromtimestamp(self.start_time)
        total_time = end_time - self.start_time

        return self.player, self.start_time, total_time, self.positions

async def check_sessions(requester, tracker):
    try:
        print("Checking for new players...")
        online_players = await requester.get_request("online")
        online_names = {player["uuid"] for player in online_players["players"]}

        new_players = online_names - set(tracker.sessions)
        lost_players = set(tracker.sessions) - online_names

        active_creations = []

        print(f"Found {len(new_players)} new players")

        for player in new_players:
            tracker.sessions[player] = await Session.create(player)
            active_creations.append(tracker.sessions[player].tmp_obj)

        await Active.bulk_create(active_creations, ignore_conflicts=True)

        lost_players_data = await requester.post_request_batch("players", list(lost_players))
        lost_uuid_map = {player["uuid"]: player for player in lost_players_data}

        await Players.bulk_create([Players(uuid=uuid) for uuid in lost_uuid_map.keys()], ignore_conflicts=True)
        lost_player_objects = await Players.filter(uuid__in=lost_uuid_map.keys()).all()
        objects_map = {player.uuid: player for player in lost_player_objects}

        await Towns.bulk_create([Towns(uuid=data["town"]["uuid"]) for data in lost_uuid_map.values() if data["town"]["uuid"]], ignore_conflicts=True)
        lost_town_objects = await Towns.filter(uuid__in=[data["town"]["uuid"] for data in lost_uuid_map.values() if data["town"]["uuid"]]).all()
        towns_map = {town.uuid: town for town in lost_town_objects}

        session_creations = []
        active_deletions = []

        print(f"Found {len(lost_players)} lost players")

        for player in lost_players:
            session = tracker.sessions.pop(player)
            player_name, start_date, total_time, positions = session.end()

            if player_name not in lost_uuid_map:
                print(f"Warning: no API data for {player_name}, skipping session save")
                active_deletions.append(session.tmp_obj.player)
                continue

            player_data = lost_uuid_map[player_name]

            player_obj = objects_map[player_name]

            position_json = json.dumps(positions)
            datetime_start = datetime.datetime.fromtimestamp(start_date, tz=datetime.timezone.utc)

            # The API returns milliseconds which you need to convert to seconds
            first_session = True if (start_date - (player_data["timestamps"]["registered"] / 1000)) < (60 * 5) else False

            if player_data["town"]["name"]:
                is_mayor = player_data["status"]["isMayor"]
                town_uuid = player_data["town"]["uuid"]

                town_obj = towns_map[town_uuid]
                town_obj.name = player_data["town"]["name"]
                if is_mayor:
                    town_obj.mayor = player_obj
                    if not town_obj.previous_mayors or town_obj.previous_mayors[-1] != player_obj.id:
                        town_obj.previous_mayors.append(player_obj.id)
                await town_obj.save()

                player_obj.username = player_data["name"]
                player_obj.town = town_obj
                await player_obj.save()
            else:
                player_obj.username = player_data["name"]
                await player_obj.save()
                town_obj = None

            session_creations.append(Sessions(player=player_obj, town=town_obj if town_obj else None, start_date=datetime_start, total_time=total_time, positions=position_json, first_session=first_session))
            active_deletions.append(session.tmp_obj.player)

        await Sessions.bulk_create(session_creations)
        await Active.filter(player__in=active_deletions).delete()
    except Exception as e:
        print(f"Error in check_sessions: {e}")

async def get_positions(requester, tracker):
    try:
        print("Getting positions...")
        online_data = await requester.map_request()
        for player in online_data["players"]:
            uuid = player["uuid"]
            formatted_uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
            if formatted_uuid in tracker.sessions.keys():
                await tracker.sessions[formatted_uuid].append_position((player["x"], player["y"], player["z"]))
    except Exception as e:
        print(f"Error in get_positions: {e}")

async def update_map(requester):
    print(os.getcwd())
    print("Updating map...")
    os.makedirs("watcher/cache", exist_ok=True)
    full_map = Image.new("RGB", (8 * 512, 4 * 512))

    for x in range(-4, 4):
        for y in range(-2, 2):
            print(f"Downloading {x}_{y}")
            grab_map = await requester.map_tile_request(x, y)
            img = Image.open(BytesIO(grab_map))
            img.save(f'watcher/cache/{x}_{y}.png')
            full_map.paste(img, ((x + 4) * 512, (y + 2) * 512))

    # Top Left corner: 448, 480
    # Bottom Right corner: 8743, 4623

    full_map.save("shared/map.png")

async def check_town_blocks(requester):
    try:
        print("Checking townblocks...")
        towns = await requester.get_request("towns")
        town_data = await requester.post_request_batch("towns", [town["uuid"] for town in towns])

        town_data_map = {town["uuid"]: town for town in town_data}
        town_list = await Towns.filter(uuid__in=list(town_data_map.keys())).all()
        town_objects = {town.uuid: town for town in town_list}

        for uuid, data in town_data_map.items():
            town = town_objects.get(uuid)
            if town is None:
                continue

            town.town_blocks = data["coordinates"]["townBlocks"]
            await town.save()
    except Exception as e:
        print(f"Error in check_town_blocks: {e}")