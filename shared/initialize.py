import asyncpg
import asyncio
import os

TABLES = """
    CREATE SCHEMA IF NOT EXISTS active;
    
    CREATE TABLE IF NOT EXISTS active.players (
        id serial primary key,
        username varchar(100) unique,
        uuid varchar(100) not null unique,
        town int
    );
    
    CREATE TABLE IF NOT EXISTS active.towns (
        id serial primary key,
        name varchar(100) unique,
        uuid varchar(100) not null unique,
        mayor int,
        previous_mayors JSON,
        town_blocks JSON
    );
    
    CREATE TABLE IF NOT EXISTS active.sessions (
        id serial primary key,
        player int not null,
        town int,
        start_date timestamptz,
        total_time float,
        positions JSON,
        first_session boolean default false
    );
    
    CREATE TABLE IF NOT EXISTS active.current_sessions (
        player varchar(100) unique primary key,
        start_date timestamptz,
        positions JSON
    );
    
    ALTER TABLE active.players ADD CONSTRAINT players_town_fkey FOREIGN KEY (town) REFERENCES active.towns(id);
    ALTER TABLE active.towns ADD CONSTRAINT town_mayor_fkey FOREIGN KEY (mayor) REFERENCES active.players(id);
    ALTER TABLE active.sessions ADD CONSTRAINT session_player FOREIGN KEY (player) REFERENCES active.players(id);
    ALTER TABLE active.sessions ADD CONSTRAINT session_town FOREIGN KEY (town) REFERENCES active.towns(id);
    """

async def initialize_db():
    conn = await asyncpg.connect(os.environ.get("DATABASE_URL"))
    try:
        async with conn.transaction():
            await conn.execute(TABLES)
        print("DB initialized successfully")
    finally:
        await conn.close()

asyncio.run(initialize_db())