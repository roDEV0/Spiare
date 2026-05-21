import os
import asyncpg

# TODO: Rewrite to use Tortoise connections

class Notifier:
    def __init__(self):
        self.pool = None

    async def create(self):
        database_url = os.environ.get("DATABASE_URL")
        self.pool = await asyncpg.create_pool(dsn=database_url)

    async def send_notification(self, channel, payload):
        async with self.pool.acquire() as conn:
            await conn.execute(f"""NOTIFY {channel} {payload}""")