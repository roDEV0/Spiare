import asyncio
import tortoise

from tortoise.transactions import in_transaction

from shared.database import Sessions, Players, Towns, Active
from watcher.trigger.transfers import town_transfer_trigger
import time
from shared.utils import get_valid_data
import json
import datetime
import uuid

class Session:
    def __init__(self, player: str):
        self.player = player
        self.start_date = time.time()
        self.positions = []
        self.active_obj = None

    @classmethod
    async def create(cls, player: str):
        session = cls(player)
        start_date = time.time()
        session.start_date = start_date
        session.active_obj = await Active.create(
            player=player,
            positions=[],
            start_date=start_date
        )
        return session

    @classmethod
    async def load(cls, active):
        session = cls(active.player)
        session.start_date = active.start_date.timestamp()
        session.active_obj = active
        session.positions = active.positions
        return session

    async def append_position(self, positions):
        self.positions.append(positions)
        self.active_obj.positions = self.positions

        await self.active_obj.save(update_fields=["positions"])

    def end_data(self):
        end_date = time.time()

        # start_date = datetime.datetime.fromtimestamp(self.start_time)
        total_time = end_date - self.start_date

        return self.player, self.start_date, total_time, self.positions

async def handle_memory_sessions(requester, tracker):
    try:
        # Fetch the online player data
        online_players = await requester.get_request("online")

        # TODO: Create some sort of fallback incase this cannot be fetched
        if not online_players:
            print("Online players couldn't be fetched")
            return []

        online_uuids = set([player["uuid"] for player in online_players["players"]])
        logged_uuids = tracker.get_sessions()

        new_players = online_uuids - logged_uuids
        lost_players = logged_uuids - online_uuids

        for uuid in new_players:
            tracker.sessions[uuid] = await Session.create(uuid)

        # Get lost player data in batches of 100
        if not lost_players:
            print("No lost players")
            return []

        return lost_players
    except Exception as e:
        print(f"Error in handle_memory_sessions: {e}")

async def get_lost_player_data(lost_players, requester):
    try:
        results = await asyncio.gather(
            *(get_valid_data(requester, "players", list(lost_players)[i:i + 100])
              for i in range(0, len(lost_players), 100))
        )

        if not results:
            return [], []

        lost_results, unfetched = zip(*results)

        unfetched_list = [player for lost_result in unfetched for player in lost_result]
        lost_players_data = [player for lost_result in lost_results for player in lost_result]

        return lost_players_data, unfetched_list
    except Exception as e:
        print(f"Error in get_lost_player_data: {e}")

async def setup_lost_sessions(lost_results, unfetched_list):
    try:
        async with in_transaction():
            await Active.filter(player__in=unfetched_list).delete()

        data_map = {player["uuid"]: player for player in lost_results}

        async with in_transaction():
            await Players.bulk_create([Players(uuid=uuid) for uuid in data_map.keys()], ignore_conflicts=True)
            player_db_rows = await Players.filter(uuid__in=data_map.keys()).all()

        rows_map = {player.uuid: player for player in player_db_rows}

        seen_towns = set()
        towns_to_create = []
        for data in lost_results:
            t_uuid = data.get("town", {}) and data["town"].get("uuid")
            if t_uuid and t_uuid not in seen_towns:
                seen_towns.add(t_uuid)
                towns_to_create.append(Towns(uuid=t_uuid))

        await Towns.bulk_create(towns_to_create, ignore_conflicts=True)
        town_objects = await Towns.filter(uuid__in=seen_towns).all()
        towns_map = {town.uuid: town for town in town_objects}

        return data_map, rows_map, towns_map
    except Exception as e:
        print(f"Error in setup_lost_sessions: {e}")

async def create_sessions(data_map, towns_map, rows_map, tracker):
    try:
        mem_sessions = [tracker.sessions.pop(player, None) for player in data_map.keys()]
        sessions_data = [session.end_data() for session in mem_sessions if session]

        info_map = {}

        for session in sessions_data:
            player, start_date, total_time, positions = session
            first_session = True if (start_date - (data_map[player]["timestamps"]["registered"] / 1000)) < (60 * 9) else False
            town_obj = towns_map[data_map[player]["town"]["uuid"]] if data_map[player]["town"]["uuid"] else None

            if town_obj.name != data_map[player]["town"]["name"]:
                await safe_rename(town_obj, data_map[player]["town"]["name"], tracker.requester)

            if (data_map[player]["status"]["isMayor"]) and (town_obj.mayor != data_map[player]["id"]):
                await update_mayor(town_obj, tracker.requester)

            info_map[player] = {
                "town": town_obj.id if town_obj else None,
                "first_session": first_session
            }

        async with in_transaction():
            await Sessions.bulk_create([Sessions(
                player=rows_map[player].id,
                start_date=datetime.datetime.fromtimestamp(start_date, tz=datetime.timezone.utc),
                town=info_map[player]["town"],
                first_session=info_map[player]["first_session"],
                total_time=total_time,
                positions=positions)
                for player, start_date, total_time, positions in sessions_data])
            await Active.filter(player__in=data_map.keys()).delete()

        return sessions_data
    except Exception as e:
        print(f"Error in create_sessions: {e}")

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

async def update_mayor(town_obj, requester):
    town_data = await requester.post_request("towns", town_obj.uuid)
    if town_obj.mayor != town_data[0]["mayor"]:
        await town_transfer_trigger(town_obj.mayor, town_data[0]["mayor"], town_obj.id, requester)
        town_obj.previous_mayors.append(town_obj.mayor)
        town_obj.mayor = town_data[0]["mayor"]

        async with in_transaction():
            await town_obj.save(update_fields=["mayor", "previous_mayors"])