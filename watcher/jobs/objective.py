from tortoise.transactions import in_transaction

from shared.database import Towns, Active, Players, Sessions
import os
from PIL import Image
from io import BytesIO
import asyncio
import traceback
from shared.utils import get_valid_data
from watcher.jobs.check_sessions import (
    handle_memory_sessions,
    get_lost_player_data,
    setup_lost_sessions,
    create_sessions,
)
import datetime


async def check_sessions(requester, tracker):
    try:
        lost_players = await handle_memory_sessions(requester, tracker)
        if not lost_players:
            return
        data, unfetched = await get_lost_player_data(lost_players, requester)
        data_map, rows_map, towns_map = await setup_lost_sessions(data, unfetched)
        await create_sessions(data_map, towns_map, rows_map, requester, tracker)
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

    tasks = [
        append_position(
            format_uuid(player["uuid"]),
            (player["x"], player["y"], player["z"]),
            tracker,
        )
        for player in online_data["players"]
    ]

    await asyncio.gather(*tasks)
