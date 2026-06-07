from shared.database import Towns, Active
import os
from PIL import Image
from io import BytesIO
import asyncio
import traceback
from shared.utils import get_valid_data
from watcher.jobs.check_sessions import handle_memory_sessions, get_lost_player_data, setup_lost_sessions, create_sessions

async def check_sessions(requester, tracker):
    try:
        lost_players = await handle_memory_sessions(requester, tracker)
        if not lost_players:
            return
        data, unfetched = await get_lost_player_data(lost_players, requester)
        data_map, rows_map, towns_map = await setup_lost_sessions(data, unfetched)
        await create_sessions(data_map, towns_map, rows_map, tracker)
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