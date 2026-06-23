from shared.database import TownSnapshot, PlayerSnapshot, Players, Towns, Sessions
import datetime


async def take_player_snapshot():
    snapshot_objects = []
    print("Taking player snapshots...")
    active_players = await Players.filter(active=True)
    time_taken = datetime.datetime.now()
    sessions = await Sessions.filter(
        player__in=[player.id for player in active_players]
    )
    towns = await Towns.all()

    for player in await Players.filter(active=True):

        player_sessions = [
            session for session in sessions if session.player == player.id
        ]
        player_town = [town for town in towns if town.id == player.town]
        player_town = player_town[0] if player_town else None

        player_snapshot = PlayerSnapshot(
            player=player.id,
            town=player_town.id if player_town else None,
            total_sessions=len(player_sessions),
            gold=player.gold,
            date=time_taken,
        )

        snapshot_objects.append(player_snapshot)

    await PlayerSnapshot.bulk_create(snapshot_objects)


async def take_town_snapshot():
    print("Taking town snapshots...")
    snapshot_objects = []
    time_taken = datetime.datetime.now()

    players = await Players.all()

    for town in await Towns.all():
        citizens = [player for player in players if player.town == town.id]

        town_snapshot = TownSnapshot(
            town=town.id,
            mayor=town.mayor,
            town_blocks=town.town_blocks,
            total_citizens=len(citizens),
            gold=town.gold,
            date=time_taken,
        )

        snapshot_objects.append(town_snapshot)

    await TownSnapshot.bulk_create(snapshot_objects)
