from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tortoise import Tortoise
import aiohttp
import os
from shared.http_requests import HTTPRequester
from watcher.jobs.objective import check_sessions, get_positions, update_map, check_town_blocks
import asyncio
from shared.database import Active
from watcher.jobs.objective import Session
from watcher.jobs.snapshots import take_player_snapshot, take_town_snapshot
from apscheduler.events import EVENT_JOB_ERROR

from watcher.notify import Notifier

scheduler = AsyncIOScheduler()

class Tracker:
    def __init__(self):
        self.sessions = {}

async def load_sessions(tracker):
    active_sessions = await Active.all()
    for session in active_sessions:
        tracker.sessions[session.player] = await Session.load(session)
    print(f"Loaded {len(active_sessions)} active sessions")

async def main():
    database_url = os.environ.get("DATABASE_URL")
    timeout = aiohttp.ClientTimeout(total=30)
    session = aiohttp.ClientSession(timeout=timeout)
    requester = HTTPRequester(session)
    notifier = Notifier()
    await notifier.create()

    tracker = Tracker()

    await Tortoise.init(db_url=database_url, modules={"models": ["shared.database"]})
    print("DB initialized successfully")

    check_sessions_job = scheduler.add_job(check_sessions, "interval", minutes=5, args=[requester, tracker])
    get_positions_job = scheduler.add_job(get_positions, "interval", seconds=30, args=[requester, tracker])
    update_map_job = scheduler.add_job(update_map, "interval", hours=12, args=[requester])
    check_town_blocks_job = scheduler.add_job(check_town_blocks, "interval", minutes=10, args=[requester])

    player_snapshot_job = scheduler.add_job(take_player_snapshot, "cron", hour=12, minute=0, second=0)
    town_snapshot_job = scheduler.add_job(take_town_snapshot, "cron", hour=12, minute=0, second=0)

    await load_sessions(tracker)

    await check_sessions(requester, tracker)
    await get_positions(requester, tracker)
    await update_map(requester)
    await check_town_blocks(requester)

    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)

    scheduler.start()

    try:
        await asyncio.Event().wait()  # Block forever
    finally:
        scheduler.shutdown()
        await Tortoise.close_connections()
        await session.close()

def job_error_listener(event):
    if event.exception:
        print(f"Job {event.job_id} failed with error: {event.exception}")

asyncio.run(main())




