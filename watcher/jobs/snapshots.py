from shared.database import TownSnapshot, PlayerSnapshot, Players, Towns, Sessions

async def take_player_snapshot():
    snapshot_objects = []
    print("Taking player snapshots...")
    for player in await Players.all():

        sessions = await Sessions.filter(player=player.id)

        player_town = await Towns.filter(id=player.town).first()

        sessions_dict = {}
        for session in sessions:
            sessions_dict[str(session.id)] = {
                "positions": session.positions,
                "start_date": session.start_date,
                "total_time": session.total_time
            }

        player_snapshot = PlayerSnapshot(
            player=player.id,
            town=player_town.id if player_town else None,
            sessions=sessions_dict,
            total_sessions=len(sessions_dict)
        )

        snapshot_objects.append(player_snapshot)

    await PlayerSnapshot.bulk_create(snapshot_objects)


async def take_town_snapshot():
    print("Taking town snapshots...")
    snapshot_objects = []

    for town in await Towns.all():
        citizens = await Players.filter(town=town.id)

        town_snapshot = TownSnapshot(
            name=town.name,
            town=town.id,
            mayor=town.mayor,
            previous_mayors=town.previous_mayors,
            town_blocks=town.town_blocks,
            total_town_blocks=len(town.town_blocks),
            total_citizens=len(citizens)
        )

        snapshot_objects.append(town_snapshot)

    await TownSnapshot.bulk_create(snapshot_objects)