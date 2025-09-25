import json
import zlib
from collections import defaultdict

import database.main.users as users
from database.main import db
from utils import logs
from utils.logging import log

with open("./data/maintrack.json", "r") as f:
    maintrack_text_pool = json.load(f)


def add_races(races):
    db.run_many(f"""
        INSERT OR IGNORE INTO races
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [(
        race["universe"], race["username"], race["number"], race["text_id"],
        race["wpm"], race["accuracy"], race["points"], race["characters"],
        race["rank"], race["racers"], race["race_id"], race["timestamp"],
        race["unlagged"], race["adjusted"], race["raw_adjusted"],
        race["pauseless_adjusted"], race["start"], race["duration"],
        race["correction_time"], race["pause_time"]
    ) for race in races])


async def get_races(
    username, columns="*", start_date=None, end_date=None, start_number=None, end_number=None,
    order_by=None, reverse=False, limit=None, universe="play", text_pool="all",
):
    users.update_last_accessed(universe, username)

    wpm_filter = ""
    if columns != "*":
        for column in columns:
            if column in ["wpm_unlagged", "wpm_adjusted", "wpm_raw", "wpm_pauseless"]:
                columns[columns.index(column)] = f"{column} AS wpm"
                if column in ["wpm_raw", "wpm_pauseless"]:
                    wpm_filter = f"AND {column} IS NOT NULL"
        columns = ",".join([c for c in columns])
    order = "DESC" if reverse else "ASC"

    batch_size = 100_000
    offset = 0

    if limit:
        limit_string = f"LIMIT {limit}"
    else:
        limit_string = f"LIMIT {batch_size} OFFSET {offset}"

    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    race_list = []
    while True:
        batch_races = await db.fetch_async(f"""
            SELECT {columns} FROM races
            INDEXED BY idx_races_universe_username
            WHERE universe = ?
            AND username = ?
            {text_pool_string}
            {wpm_filter}
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


def get_text_races(username, text_id, universe, start_date=None, end_date=None, wpm="wpm"):
    wpm_filter = ""
    if wpm in ["wpm_raw", "wpm_pauseless"]:
        wpm_filter = f"AND {wpm} IS NOT NULL"

    races = db.fetch(f"""
        SELECT username, number, text_id, {wpm} AS wpm, timestamp FROM races
        INDEXED BY idx_races_universe_username_text_id
        WHERE universe = ?
        AND username = ?
        AND text_id = ?
        {wpm_filter}
        {f'AND timestamp >= {start_date}' if start_date else ''}
        {f'AND timestamp < {end_date}' if end_date else ''}
        ORDER BY timestamp ASC
    """, [universe, username, text_id])

    return races


async def get_encounters(username1, username2, universe, wpm="wpm", text_pool="all"):
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    columns = (
        f"username, number, {wpm} AS wpm, wpm_raw, accuracy,"
        f"correction_time, total_time, rank, racers, race_id, timestamp"
    )

    wpm_filter = ""
    for wpm in ["wpm_raw", "wpm_pauseless"]:
        if wpm in columns:
            wpm_filter = f"AND {wpm} IS NOT NULL"

    races = db.fetch(f"""
        SELECT {columns}
        FROM races
        WHERE race_id IN (
            SELECT race_id
            FROM races
            WHERE universe = ?
            AND username IN (?, ?)
            {text_pool_string} 
            {wpm_filter}
            GROUP BY race_id
            HAVING COUNT(DISTINCT username) = 2
        )
        AND username IN (?, ?)
    """, [universe, username1, username2, username1, username2])

    encounters = defaultdict(list)
    for race in races:
        encounters[race["race_id"]].append(race)

    return [
        sorted(r, key=lambda row: row["username"] == username2)
        for r in encounters.values()
    ]


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
