from tortoise import fields
from tortoise.models import Model

# OBJECTIVES

class Towns(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True, null=True)
    uuid = fields.CharField(max_length=100, unique=True)
    mayor = fields.IntField(null=True)
    previous_mayors = fields.JSONField(null=True, default=[])
    town_blocks = fields.JSONField(null=True, default=[])

    class Meta:
        table = "towns"
        schema = "towns"


class Players(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=100, unique=True, null=True)
    uuid = fields.CharField(max_length=100, unique=True)
    town = fields.IntField(null=True)
    active = fields.BooleanField(default=True)

    class Meta:
        table = "players"
        schema = "players"

# SESSIONS

class Sessions(Model):
    id = fields.IntField(pk=True)
    player = fields.IntField()
    town = fields.IntField(null=True)
    start_date = fields.DatetimeField(null=True)
    total_time = fields.FloatField(null=True)
    positions = fields.JSONField(null=True, default=[])
    first_session = fields.BooleanField(default=False)

    class Meta:
        table = "sessions"
        schema = "sessions"


class Active(Model):
    player = fields.CharField(max_length=100, pk=True)
    start_date = fields.DatetimeField(auto_now_add=True)
    positions = fields.JSONField(null=True, default=[])

    class Meta:
        table = "sessions"
        schema = "active"

# EVENTS

class TownTransfer(Model):
    id = fields.IntField(pk=True)
    old_mayor = fields.IntField()
    new_mayor = fields.IntField()
    town = fields.IntField()
    date = fields.DatetimeField(auto_now_add=True)
    from_inactivity = fields.BooleanField(default=False)

    class Meta:
        table = "town_transfers"
        schema = "transfers"

class TownTransferPlayerSnapshot(Model):
    id = fields.IntField(pk=True)
    player = fields.IntField()
    transfer_event = fields.IntField()
    selected = fields.BooleanField(default=False)
    sessions = fields.JSONField(null=True, default=[])
    playtime = fields.FloatField(null=True)
    total_sessions = fields.IntField(null=True)
    date = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "town_transfer_snapshots"
        schema = "transfers"

# SNAPSHOTS

class PlayerSnapshot(Model):
    id = fields.IntField(pk=True)
    player = fields.IntField()
    town = fields.IntField(null=True)
    sessions = fields.JSONField(null=True, default=[])
    total_sessions = fields.IntField(null=True)
    date = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "player_snapshots"
        schema = "player_snapshots"

class TownSnapshot(Model):
    id = fields.IntField(pk=True)
    town = fields.IntField()
    mayor = fields.IntField(null=True)
    previous_mayors = fields.JSONField(null=True, default=[])
    town_blocks = fields.JSONField(null=True, default=[])
    total_town_blocks = fields.IntField(null=True)
    total_citizens = fields.IntField(null=True)
    date = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "town_snapshots"
        schema = "town_snapshots"

# SHOPPING

# class Items(Model):
#     id = fields.IntField(pk=True)
#     item = fields.CharField(max_length=250)
#     avg_price = fields.FloatField()
#     avg_amount = fields.FloatField()

# class Purchases(Model):
#     id = fields.IntField(pk=True)
#     date = fields.DatetimeField(auto_now_add=True)
#     player = fields.ForeignKeyField(
#         "models.Players",
#         related_name="purchases",
#         source_field="player"
#     )
#     item = fields.ForeignKeyField()