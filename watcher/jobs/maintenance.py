import tortoise
from tortoise.transactions import in_transaction
from PIL import Image
from io import BytesIO
import asyncio
import os
import datetime
from shared.utils import get_valid_data
from shared.database import Players, Sessions, Towns, Active


async def clean_dead_sessions(requester):
    print("Doing some spring cleaning...")
    online_players = await requester.get_request("online")
    if not online_players:
        print("Online players couldn't be fetched")
        return
    await Active.filter(
        player__not_in={player["uuid"] for player in online_players["players"]}
    ).delete()
    print(f"Removed dead sessions")


async def check_active_players():
    print("Checking active players...")
    async with in_transaction():
        players = await Players.all()
        sessions = await Sessions.filter(
            start_date__gte=datetime.datetime.now() - datetime.timedelta(days=7)
        )
        print(f"Found {len(players)} players and {len(sessions)} sessions")

    for player in players:
        if player.id not in [session.player for session in sessions]:
            player.active = False
            print(f"Player {player.username} is no longer active")
        else:
            player.active = True
            print(f"Player {player.username} is still active")

    async with in_transaction():
        await Players.bulk_update(players, fields=["active"], batch_size=100)


async def update_map(requester):
    print("Updating map...")
    os.makedirs("watcher/cache", exist_ok=True)
    full_map = Image.new("RGB", (8 * 512, 4 * 512))

    for x in range(-4, 4):
        for y in range(-2, 2):
            grab_map = await requester.map_tile_request(x, y)
            img = Image.open(BytesIO(grab_map))
            img.save(f"watcher/cache/{x}_{y}.png")
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
            town_data, _ = await get_valid_data(
                requester, "towns", [town["uuid"] for town in town_list]
            )

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
        await asyncio.gather(
            *(update_town_blocks(towns[i : i + 100]) for i in range(0, len(towns), 100))
        )

    except Exception as e:
        print(f"Error in check_town_blocks: {e}")
