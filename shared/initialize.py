import asyncpg
import asyncio
import os

TABLES = """
CREATE SCHEMA IF NOT EXISTS partman;
CREATE EXTENSION IF NOT EXISTS pg_partman SCHEMA partman;

CREATE SCHEMA IF NOT EXISTS players;
CREATE SCHEMA IF NOT EXISTS towns;
CREATE SCHEMA IF NOT EXISTS sessions;
CREATE SCHEMA IF NOT EXISTS active;
CREATE SCHEMA IF NOT EXISTS shopping;
CREATE SCHEMA IF NOT EXISTS transfers;
CREATE SCHEMA IF NOT EXISTS player_snapshots;
CREATE SCHEMA IF NOT EXISTS town_snapshots;

CREATE TABLE IF NOT EXISTS players.players (
   id serial primary key,
   username varchar(100) unique,
   uuid varchar(100) not null unique,
   town int,
   gold int,
   active boolean default true
);

CREATE TABLE IF NOT EXISTS towns.towns (
    id serial primary key,
    name varchar(100) unique,
    uuid varchar(100) not null unique,
    mayor int,
    previous_mayors JSON,
    gold int,
    town_blocks JSON
);

CREATE TABLE IF NOT EXISTS sessions.sessions (
    id serial,
    player int not null,
    town int,
    start_date timestamptz not null,
    total_time float,
    positions JSON,
    first_session boolean default false,
    PRIMARY KEY (id, start_date)
) PARTITION BY RANGE (start_date);

CREATE TABLE IF NOT EXISTS active.sessions (
    player varchar(100) unique primary key,
    start_date timestamptz,
    positions JSON
);

CREATE TABLE IF NOT EXISTS shopping.item_purchases (
    id serial,
    date timestamptz NOT NULL DEFAULT now(),
    player int NOT NULL,
    item int NOT NULL,
    amount int NOT NULL,
    price int NOT NULL,
    town int NOT NULL,
    owner int NOT NULL,
    PRIMARY KEY (id, date)
) PARTITION BY RANGE (date);

CREATE TABLE IF NOT EXISTS shopping.items (
    id serial PRIMARY KEY,
    item varchar(250) NOT NULL,
    avg_price float4,
    price_history json,
    avg_amount float4
);

CREATE TABLE IF NOT EXISTS transfers.town_transfers (
    id serial primary key,
    old_mayor int,
    new_mayor int not null,
    town int not null,
    date timestamptz not null default now(),
    from_inactivity boolean default false
);

CREATE TABLE IF NOT EXISTS transfers.town_transfer_snapshots (
    id serial,
    player int not null,
    transfer_event int not null,
    selected boolean not null,
    sessions json,
    total_sessions int,
    playtime float,
    date timestamptz not null default now(),
    PRIMARY KEY (id, date)
) PARTITION BY RANGE (date);

CREATE TABLE IF NOT EXISTS player_snapshots.player_snapshots (
    id serial,
    player int not null,
    town int,
    total_sessions int,
    gold int,
    date timestamptz not null default now(),
    PRIMARY KEY (id, date)
) PARTITION BY RANGE (date);

CREATE TABLE IF NOT EXISTS town_snapshots.town_snapshots (
    id serial,
    town int not null,
    mayor int,
    previous_mayors JSON,
    town_blocks JSON,
    total_town_blocks int,
    total_citizens int,
    gold int,
    date timestamptz not null default now(),
    PRIMARY KEY (id, date)
) PARTITION BY RANGE (date);

ALTER TABLE shopping.item_purchases ADD CONSTRAINT purchase_player_fkey FOREIGN KEY (player) REFERENCES players.players(id);
ALTER TABLE shopping.item_purchases ADD CONSTRAINT purchase_item_fkey FOREIGN KEY (item) REFERENCES shopping.items(id);
ALTER TABLE shopping.item_purchases ADD CONSTRAINT purchase_town_fkey FOREIGN KEY (town) REFERENCES towns.towns(id);
ALTER TABLE shopping.item_purchases ADD CONSTRAINT purchase_owner_fkey FOREIGN KEY (owner) REFERENCES players.players(id);

ALTER TABLE players.players ADD CONSTRAINT players_town_fkey FOREIGN KEY (town) REFERENCES towns.towns(id);
ALTER TABLE towns.towns ADD CONSTRAINT town_mayor_fkey FOREIGN KEY (mayor) REFERENCES players.players(id);
ALTER TABLE sessions.sessions ADD CONSTRAINT session_player FOREIGN KEY (player) REFERENCES players.players(id);
ALTER TABLE sessions.sessions ADD CONSTRAINT session_town FOREIGN KEY (town) REFERENCES towns.towns(id);

ALTER TABLE transfers.town_transfers ADD CONSTRAINT town_transfer_old_mayor FOREIGN KEY (old_mayor) REFERENCES players.players(id);
ALTER TABLE transfers.town_transfers ADD CONSTRAINT town_transfer_new_mayor FOREIGN KEY (new_mayor) REFERENCES players.players(id);
ALTER TABLE transfers.town_transfers ADD CONSTRAINT town_transfer_town FOREIGN KEY (town) REFERENCES towns.towns(id);
ALTER TABLE transfers.town_transfer_snapshots ADD CONSTRAINT town_transfer_player FOREIGN KEY (player) REFERENCES players.players(id);
ALTER TABLE transfers.town_transfer_snapshots ADD CONSTRAINT town_transfer_event FOREIGN KEY (transfer_event) REFERENCES transfers.town_transfers(id);

ALTER TABLE player_snapshots.player_snapshots ADD CONSTRAINT player_snapshot_player FOREIGN KEY (player) REFERENCES players.players(id);
ALTER TABLE player_snapshots.player_snapshots ADD CONSTRAINT player_snapshot_town FOREIGN KEY (town) REFERENCES towns.towns(id);
ALTER TABLE town_snapshots.town_snapshots ADD CONSTRAINT town_snapshot_town FOREIGN KEY (town) REFERENCES towns.towns(id);
ALTER TABLE town_snapshots.town_snapshots ADD CONSTRAINT town_snapshot_mayor FOREIGN KEY (mayor) REFERENCES players.players(id);


SELECT partman.create_parent(
p_parent_table := 'sessions.sessions',
p_control := 'start_date',
p_interval := '1 month');

SELECT partman.create_parent(
p_parent_table := 'shopping.item_purchases',
p_control := 'date',
p_interval := '1 month');

SELECT partman.create_parent(
p_parent_table := 'transfers.town_transfer_snapshots',
p_control := 'date',
p_interval := '1 month');

SELECT partman.create_parent(
p_parent_table := 'player_snapshots.player_snapshots',
p_control := 'date',
p_interval := '1 month');

SELECT partman.create_parent(
p_parent_table := 'town_snapshots.town_snapshots',
p_control := 'date',
p_interval := '1 month');
"""

DISCORD_TABLES = """
CREATE SCHEMA IF NOT EXISTS configs;
CREATE SCHEMA IF NOT EXISTS verifications;

CREATE TABLE IF NOT EXISTS configs.servers (
    id serial primary key,
    name varchar(255),
    server_id varchar(255) NOT NULL,
    citizen_role_id varchar(255),
    admin_role_id varchar(255),
    foreigner_role_id varchar(255),
    notif_channel_id varchar(255),
    active_notifs JSON,
    allowed boolean default true,
    nation varchar(255)
);

CREATE TABLE IF NOT EXISTS verifications.verifications (
    id serial primary key,
    user_id varchar(255) NOT NULL,
    username varchar(255) NOT NULL,
    minecraft_username varchar(255) NOT NULL,
    minecraft_uuid varchar(255) NOT NULL,
    town varchar(255) NOT NULL,
    date_of_verification timestamptz NOT NULL default now(),
    server int NOT NULL,
    citizen boolean NOT NULL default false
);

ALTER TABLE verifications.verifications ADD CONSTRAINT fk_verifications_servers FOREIGN KEY (server) REFERENCES configs.servers(id);
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
