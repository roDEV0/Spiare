from tortoise.models import Model
from tortoise import fields
from tortoise.contrib.postgres.fields import ArrayField

class Players(Model):
    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=100)
    town = fields.CharField(max_length=100, null=True)

class Sessions(Model):
    id = fields.IntField(primary_key=True)
    player = fields.ForeignKeyField("models.Players", related_name="sessions")
    town = fields.CharField(max_length=100, null=True)
    start_date = fields.DatetimeField()
    total_time = fields.FloatField()
    positions = fields.JSONField(null=True)
    first_session = fields.BooleanField(default=False)