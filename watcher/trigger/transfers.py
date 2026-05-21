from shared.database import TownTransfer, Players, TownTransferPlayerSnapshot, Sessions
from shared.http_requests import HTTPRequester
from datetime import datetime

async def town_transfer_trigger(old_mayor: int, new_mayor: int, town: int, requester: HTTPRequester):
    old_mayor_db = await Players.get(id=old_mayor)
    old_mayor_data = await requester.post_request("players", old_mayor_db.uuid)

    last_online = old_mayor_data[0]["timestamps"]["lastOnline"]
    last_online_date = datetime.fromtimestamp(last_online / 1000)

    days_difference = (datetime.now() - last_online_date).days

    town_transfer = TownTransfer(
        old_mayor=old_mayor,
        new_mayor=new_mayor,
        town=town,
        from_inactivity=True if days_difference > 40 else False
    )

    await town_transfer.save()

    player_snapshots = []

    for player in await Players.all().filter(town=town):
        sessions = await Sessions.filter(player=player.id)

        sessions_dict = {}
        for session in sessions:
            sessions_dict[str(session.id)] = {
                "start_date": session.start_date.isoformat(),
                "time": session.total_time
            }

        snapshot = TownTransferPlayerSnapshot(
            player=player.id,
            transfer_event=town_transfer.id,
            selected=True if player.id == new_mayor else False,
            sessions=sessions_dict,
            total_sessions=len(sessions_dict),
            playtime=sum(session["time"] for session in sessions_dict.values())
        )

        player_snapshots.append(snapshot)

    await TownTransferPlayerSnapshot.bulk_create(player_snapshots)