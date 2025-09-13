import asyncio
import zlib

import database.main.users as users
from database.main import db
from utils import logs
from utils.logging import log


async def add_races(races):
    batch_size = 1000
    sleep_time = 1 if len(races) > 10000 else 0
    for i in range(0, len(races), batch_size):
        batch = races[i:i + batch_size]
        db.run_many("""
            INSERT OR IGNORE INTO races
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [(
            race["universe"], race["username"], race["number"], race["text_id"],
            race["wpm"], race["accuracy"], race["points"], race["characters"],
            race["rank"], race["racers"], race["race_id"], race["timestamp"],
            race["unlagged"], race["adjusted"], race["raw_adjusted"],
            race["pauseless_adjusted"], race["start"], race["duration"],
            race["correction_time"], race["pause_time"]
        ) for race in batch])
        await asyncio.sleep(sleep_time)


def add_temporary_races(username, races):
    db.run_many("""
        INSERT OR IGNORE INTO temporary_races
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(
        race["univ"], username, race["rid"], race["tid"],
        race["sl"], race["t"], race["acc"], race["wpm"],
        race["pts"], race["rn"], race["nr"], race["r"], race["kl"],
    ) for race in races])


def get_temporary_races(universe, username):
    races = db.fetch(f"""
        SELECT * FROM temporary_races
        WHERE univ = ?
        AND user = ?
    """, [universe, username])

    return [dict(race) for race in races]


def delete_temporary_races(universe, username):
    db.run("""
        DELETE FROM temporary_races
        WHERE univ = ?
        AND user = ?
    """, [universe, username])


async def get_races(
        username, columns="*", start_date=None, end_date=None, start_number=None, end_number=None,
        order_by=None, reverse=False, limit=None, universe="play"
):
    users.update_last_accessed(universe, username)

    if columns != "*":
        columns = ["wpm_adjusted AS wpm" if column == "wpm" else column for column in columns]
        columns = ",".join([c for c in columns])
    order = "DESC" if reverse else "ASC"

    batch_size = 100_000
    offset = 0

    if limit:
        limit_string = f"LIMIT {limit}"
    else:
        limit_string = f"LIMIT {batch_size} OFFSET {offset}"

    race_list = []
    while True:
        batch_races = await db.fetch_async(f"""
            SELECT {columns} FROM races
            INDEXED BY idx_races_universe_username
            WHERE universe = ?
            AND username = ?
            {f'AND number >= {start_number}' if start_number else ''}
            {f'AND number <= {end_number}' if end_number else ''}
            {f'AND timestamp >= {start_date}' if start_date else ''}
            {f'AND timestamp < {end_date}' if end_date else ''}
            {f'ORDER BY {order_by} {order}' if order_by else ''}
            {limit_string}
        """, [universe, username])

        race_list += batch_races

        if limit or not batch_races:
            break

        offset += batch_size
        limit_string = f"LIMIT {batch_size} OFFSET {offset}"

    return race_list


def get_race(username, number, universe, get_log=False, get_keystrokes=False, get_typos=False):
    params = [universe, username, number]

    if get_log:
        race = db.fetch("""
            SELECT r.*, tl.log, tl.compressed, t.quote
            FROM races r
            LEFT JOIN typing_logs tl
            ON tl.universe = r.universe
            AND tl.username = r.username
            AND tl.number = r.number
            JOIN texts t
            ON t.text_id = r.text_id
            WHERE r.universe = ?
            AND r.username = ?
            AND r.number = ?
        """, params)

        if not race or race[0]["log"] is None:
            return None

        race = dict(race[0])
        if race["compressed"]:
            race["log"] = zlib.decompress(race["log"]).decode("utf-8")

        return logs.get_log_details(race, get_keystrokes, get_typos)

    else:
        race = db.fetch(f"""
            SELECT * FROM races
            WHERE universe = ?
            AND username = ?
            AND number = ?
        """, params)

        if not race:
            return None

        return dict(race[0])


def get_latest_text_id(username, universe):
    text_id = db.fetch("""
        SELECT text_id FROM races
        WHERE universe = ?
        AND username = ?
        ORDER BY timestamp
        DESC LIMIT 1
    """, [universe, username])

    if not text_id:
        return None

    return text_id[0][0]


def get_text_races(username, text_id, universe, start_date=None, end_date=None):
    races = db.fetch(f"""
        SELECT * FROM races
        INDEXED BY idx_races_universe_username_text_id
        WHERE universe = ?
        AND username = ?
        AND text_id = ?
        {f'AND timestamp >= {start_date}' if start_date else ''}
        {f'AND timestamp < {end_date}' if end_date else ''}
        ORDER BY timestamp ASC
    """, [universe, username, text_id])

    return races


async def delete_race(username, race_number, universe="play"):
    log(f"Deleting race {universe}|{username}|{race_number}")
    race = get_race(username, race_number, universe, get_log=True)

    db.run("""
        INSERT OR IGNORE INTO deleted_races (universe, username, number, typing_log)
        VALUES (?, ?, ?, ?)
    """, [universe, username, race_number, race["log"]])

    db.run("""
        DELETE FROM races
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [universe, username, race_number])

    if universe == "play":
        db.run("""
            DELETE FROM text_results
            WHERE username = ?
            AND number = ?
        """, [username, race_number])
