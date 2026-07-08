from tortoise.transactions import in_transaction

from shared.database import TownTransfer, Players, TownTransferPlayerSnapshot, Sessions
from shared.http_requests import HTTPRequester
from datetime import datetime
from shared.utils import get_valid_data


async def town_transfer_trigger(
    old_mayor: int, new_mayor: int, town: int, requester: HTTPRequester
):
    try:
        old_mayor_db = await Players.filter(id=old_mayor).first()
        difference = 0
        if old_mayor_db:
            old_mayor_data = await get_valid_data(
                requester, "players", [old_mayor_db.uuid]
            )
            if not old_mayor_data:
                print(
                    f"Old mayor {old_mayor_db.username} ({old_mayor_db.uuid}) could not be fetched"
                )
                return

            last_online = old_mayor_data[0]["timestamps"]["lastOnline"]
            last_online_date = datetime.fromtimestamp(last_online / 1000)

            difference = (datetime.now() - last_online_date).days

        town_transfer = TownTransfer(
            old_mayor=old_mayor,
            new_mayor=new_mayor,
            town=town,
            from_inactivity=True if difference > 40 else False,
        )

        async with in_transaction():
            await town_transfer.save()

        players = await Players.all().filter(town=town)
        relevant_sessions = await Sessions.filter(
            player__in=[player.id for player in players]
        )

        player_snapshots = []
        for player in players:
            player_sessions = [
                session for session in relevant_sessions if session.player == player.id
            ]

            sessions_dict = {}
            for session in player_sessions:
                sessions_dict[str(session.id)] = {
                    "start_date": session.start_date.isoformat(),
                    "time": session.total_time,
                }

            player_snapshots.append(
                TownTransferPlayerSnapshot(
                    player=player.id,
                    transfer_event=town_transfer.id,
                    selected=True if player.id == new_mayor else False,
                    sessions=sessions_dict,
                    total_sessions=len(player_sessions),
                    playtime=sum(session["time"] for session in sessions_dict.values()),
                )
            )

        async with in_transaction():
            await TownTransferPlayerSnapshot.bulk_create(player_snapshots)

    except Exception as e:
        print(f"Error in town_transfer_trigger: {e}")
