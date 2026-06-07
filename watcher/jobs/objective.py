from tortoise.transactions import in_transaction

from shared.database import Sessions, Players, Towns, Active
import json
import datetime
import time
import os
from PIL import Image
import tortoise
from io import BytesIO
import asyncio
from watcher.trigger.transfers import town_transfer_trigger
import traceback
import uuid
from shared.utils import get_valid_data

class Session:
    def __init__(self, player: str):
        self.player = player
        self.start_time = time.time()
        self.positions = []
        self.active_obj = None

    @classmethod
    async def create(cls, player: str):
        session = cls(player)
        session.active_obj = await Active.create(player=player)
        return session

    @classmethod
    async def load(cls, active):
        session = cls(active.player)
        session.start_time = active.start_date.timestamp()
        session.active_obj = active
        session.positions = active.positions
        return session

    async def append_position(self, positions):
        self.positions.append(positions)
        self.active_obj.positions = self.positions
        await Active.update_or_create(
            defaults={"positions": self.active_obj.positions, "start_date": self.active_obj.start_date},
            player=self.active_obj.player
        )

    def end_data(self):
        end_time = time.time()

        # start_date = datetime.datetime.fromtimestamp(self.start_time)
        total_time = end_time - self.start_time

        return self.player, self.start_time, total_time, self.positions

async def check_sessions(requester, tracker):
    async with in_transaction():
        try:
            online_players = await requester.get_request("online")
            if not online_players:
                print("Online players couldn't be fetched")
                return
            online_uuids = {player["uuid"] for player in online_players["players"]}

            new_players = online_uuids - set(tracker.sessions)
            lost_players = set(tracker.sessions) - online_uuids

            for player in new_players:
                tracker.sessions[player] = await Session.create(player)

            # Get lost player data in batches of 100
            if not lost_players:
                return

            results = await asyncio.gather(
                *(get_valid_data(requester, "players", list(lost_players)[i:i + 100])
                  for i in range(0, len(lost_players), 100))
            )

            lost_results, unfetched = zip(*results)

            unfetched_list = [player for lost_result in unfetched for player in lost_result]

            for player in unfetched_list:
                print(f"{player} does not appear to exist on the API")
                if player in tracker.sessions:
                    del tracker.sessions[player]
                    await Active(player=player).delete() if await Active.filter(player=player).exists() else None

            lost_players_data = [player for lost_result in lost_results for player in lost_result]
            lost_uuid_map = {player["uuid"]: player for player in lost_players_data}

            await Players.bulk_create([Players(uuid=uuid) for uuid in lost_uuid_map.keys()], ignore_conflicts=True)
            lost_player_objects = await Players.filter(uuid__in=lost_uuid_map.keys()).all()

            objects_map = {player.uuid: player for player in lost_player_objects}

            seen_town_uuids = set()
            towns_to_create = []
            for data in lost_uuid_map.values():
                t_uuid = data["town"]["uuid"]
                if t_uuid and t_uuid not in seen_town_uuids:
                    seen_town_uuids.add(t_uuid)
                    towns_to_create.append(Towns(uuid=t_uuid))

            await Towns.bulk_create(towns_to_create, ignore_conflicts=True)
            lost_town_objects = await Towns.filter(uuid__in=[data["town"]["uuid"] for data in lost_uuid_map.values() if data["town"]["uuid"]]).all()
            towns_map = {town.uuid: town for town in lost_town_objects}

            session_creations = []

            print(f"Found {len(lost_players)} lost players")

            session_deletions = []

            for player in lost_players:
                # TODO: Check why Keys might be missing here
                try:
                    session = tracker.sessions.pop(player)
                except KeyError:
                    continue
                player_uuid, start_date, total_time, positions = session.end_data()

                if session.active_obj and session.active_obj.player is not None:
                    session_deletions.append(session.active_obj.player)

                if player_uuid not in lost_uuid_map:
                    print(f"Warning: no API data for {player_uuid}, skipping session save")
                    session_deletions.append(session.active_obj.player)
                    continue

                player_data = lost_uuid_map[player_uuid]
                player_obj = objects_map[player_uuid]

                position_json = json.dumps(positions)
                datetime_start = datetime.datetime.fromtimestamp(start_date, tz=datetime.timezone.utc)

                # The API returns milliseconds which you need to convert to seconds
                first_session = True if (start_date - (player_data["timestamps"]["registered"] / 1000)) < (60 * 10) else False

                if player_data["town"]["name"]:
                    town_uuid = player_data["town"]["uuid"]
                    town_obj = towns_map[town_uuid]

                    if town_obj.name != player_data["town"]["name"]:
                        await safe_rename(town_obj, player_data["town"]["name"], requester)

                    if player_data["status"]["isMayor"]:
                        town_obj.mayor = player_obj.id
                        if not town_obj.previous_mayors or town_obj.previous_mayors[-1] != player_obj.id:
                            town_obj.previous_mayors.append(player_obj.id)
                            await town_transfer_trigger(town_obj.previous_mayors[-2], player_obj.id, town_obj.id, requester) if len(town_obj.previous_mayors) > 1 else None
                    await town_obj.save(update_fields=["mayor", "previous_mayors"])

                    player_obj.username = player_data["name"]
                    player_obj.town = town_obj.id
                    await player_obj.save(update_fields=["username", "town"])
                else:
                    player_obj.username = player_data["name"]
                    await player_obj.save(update_fields=["username"])
                    town_obj = None

                session_creations.append(Sessions(
                    player=player_obj.id,
                    town=town_obj.id if town_obj else None,
                    start_date=datetime_start,
                    total_time=total_time,
                    positions=position_json,
                    first_session=first_session
                ))

            await Sessions.bulk_create(session_creations)
            if session_deletions:
                await Active.filter(player__in=session_deletions).delete()
        except Exception as e:
            print(f"Error in check_sessions: {e}")
            traceback.print_exc()

def format_uuid(uuid: str) -> str:
    if "-" in uuid:
        return uuid
    return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"

async def append_position(player: str, position: tuple, tracker):
    try:
        if player in tracker.sessions:
            if position is None:
                await tracker.sessions[player].append_position([None, None, None])
            else:
                await tracker.sessions[player].append_position(position)
    except Exception as e:
        print(f"Error in append_position: {e}")

async def get_positions(requester, tracker):
    print("Getting positions...")
    online_data = await requester.map_request()
    if not online_data:
        print("Online data couldn't be fetched")
        return

    tasks = [append_position(format_uuid(player["uuid"]), (player["x"], player["y"], player["z"]), tracker) for player in online_data["players"]]

    await asyncio.gather(*tasks)

async def update_map(requester):
    print("Updating map...")
    os.makedirs("watcher/cache", exist_ok=True)
    full_map = Image.new("RGB", (8 * 512, 4 * 512))

    for x in range(-4, 4):
        for y in range(-2, 2):
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
        if not towns:
            print("Towns couldn't be fetched")
            return

        async def update_town_blocks(town_list: list):
            town_data, _ = await get_valid_data(requester, "towns", [town["uuid"] for town in town_list])

            town_data_map = {town["uuid"]: town for town in town_data}
            town_list = await Towns.filter(uuid__in=list(town_data_map.keys())).all()
            town_objects = {town.uuid: town for town in town_list}

            to_update = []

            for uuid, data in town_data_map.items():
                town = town_objects.get(uuid)
                if town is None:
                    continue

                town.town_blocks = data["coordinates"]["townBlocks"]
                to_update.append(town)

            if to_update:
                await Towns.bulk_update(to_update, fields=["town_blocks"])

        # Do in batches of 100 since it limits the amount of information you can be given at a time
        await asyncio.gather(*(update_town_blocks(towns[i:i+100]) for i in range(0, len(towns), 100)))

    except Exception as e:
        print(f"Error in check_town_blocks: {e}")

async def clean_dead_sessions(requester):
    print("Doing some spring cleaning...")
    online_players = await requester.get_request("online")
    if not online_players:
        print("Online players couldn't be fetched")
        return
    await Active.filter(player__not_in={player["uuid"] for player in online_players["players"]}).delete()
    print(f"Removed dead sessions")

async def safe_rename(town_obj : Towns, new_name, requester):
    print(f"Renaming {town_obj.name} to {new_name}")
    try:
        town_obj.name = f"tmp_{uuid.uuid4().hex}"
        await town_obj.save(update_fields=["name"])

        other_obj = await Towns.get(name=new_name)
        other_data = await requester.post_request("towns", other_obj.uuid)

        if not other_data:
            other_obj.name = f"deleted_{other_obj.name}"
            await other_obj.save(update_fields=["name"])
        else:
            other_obj.name = other_data[0]["name"]
            await other_obj.save(update_fields=["name"])

        town_obj.name = new_name
        await town_obj.save(update_fields=["name"])
    except tortoise.exceptions.DoesNotExist:
        town_obj.name = new_name
        await town_obj.save(update_fields=["name"])
