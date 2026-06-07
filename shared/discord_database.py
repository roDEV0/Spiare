from tortoise import fields
from tortoise.models import Model


class Config(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=True)
    server_id = fields.CharField(max_length=255, null=False)
    citizen_role_id = fields.CharField(max_length=255, null=True)
    admin_role_id = fields.CharField(max_length=255, null=True)
    foreigner_role_id = fields.CharField(max_length=255, null=True)
    notif_channel_id = fields.CharField(max_length=255, null=True)
    verify_channel_id = fields.CharField(max_length=255, null=True)
    active_notifs = fields.JSONField(null=True, default={})
    allowed = fields.BooleanField(default=True)
    nation = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "servers"
        schema = "configs"


class Verifications(Model):
    id = fields.IntField(pk=True)
    user_id = fields.CharField(max_length=255, null=False)
    username = fields.CharField(max_length=255, null=False)
    minecraft_username = fields.CharField(max_length=255, null=False)
    minecraft_uuid = fields.CharField(max_length=255, null=False)
    town = fields.CharField(max_length=255, null=False)
    date_of_verification = fields.DatetimeField(auto_now_add=True)
    server = fields.IntField()
    citizen = fields.BooleanField(default=False)

    class Meta:
        table = "verifications"
        schema = "verifications"
