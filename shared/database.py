from tortoise import fields
from tortoise.models import Model

class Towns(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True, null=True)
    uuid = fields.CharField(max_length=100, unique=True)
    mayor = fields.ForeignKeyField(
        "models.Players",
        related_name="mayored_towns",
        null=True,
        source_field="mayor"
    )
    previous_mayors = fields.JSONField(null=True, default=[])
    town_blocks = fields.JSONField(null=True, default=[])

    class Meta:
        table = "towns"
        schema = "active"


class Players(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=100, unique=True, null=True)
    uuid = fields.CharField(max_length=100, unique=True)
    town = fields.ForeignKeyField(
        "models.Towns",
        related_name="players",
        null=True,
        source_field="town"
    )

    class Meta:
        table = "players"
        schema = "active"


class Sessions(Model):
    id = fields.IntField(pk=True)
    player = fields.ForeignKeyField(
        "models.Players",
        related_name="sessions",
        source_field="player"
    )
    town = fields.ForeignKeyField(
        "models.Towns",
        related_name="sessions",
        null=True,
        source_field="town"
    )
    start_date = fields.DatetimeField(null=True)
    total_time = fields.FloatField(null=True)
    positions = fields.JSONField(null=True, default=[])
    first_session = fields.BooleanField(default=False)

    class Meta:
        table = "sessions"
        schema = "active"


class Active(Model):
    player = fields.CharField(max_length=100, pk=True)
    start_date = fields.DatetimeField(auto_now_add=True)
    positions = fields.JSONField(null=True, default=[])

    class Meta:
        table = "current_sessions"
        schema = "active"