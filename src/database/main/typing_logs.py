import sqlite3
import zlib

from database.main import db


async def decompress(log):
    return zlib.decompress(log).decode("utf-8")


def add_logs(typing_logs):
    batch_size = 1000
    for i in range(0, len(typing_logs), batch_size):
        batch = typing_logs[i:i + batch_size]
        db.run_many("""
            INSERT OR IGNORE INTO typing_logs
            VALUES (?, ?, ?, ?, 0)
        """, [(
            r["universe"], r["username"], r["number"], r["typing_log"]
        ) for r in batch])


async def compress_logs():
    rows = db.fetch("""
        SELECT universe, username, number, log FROM typing_logs
        WHERE compressed = 0
    """)

    updates = [
        (sqlite3.Binary(zlib.compress(log.encode("utf-8"), level=6)), universe, username, number)
        for universe, username, number, log in rows
    ]

    db.run_many("""
        UPDATE typing_logs
        SET log = ?, compressed = 1
        WHERE universe = ? AND username = ? AND number = ?
    """, updates)

    db.run("VACUUM")


async def get_logs(username, universe):
    batch_size = 100_000
    offset = 0
    logs = []

    while True:
        batch_rows = await db.fetch_async(f"""
            SELECT * FROM typing_logs
            INDEXED BY idx_typing_logs_universe_username
            WHERE universe = ?
            AND username = ?
            LIMIT ? OFFSET ?
        """, [universe, username, batch_size, offset])

        if not batch_rows:
            break

        for universe, username, number, blob, compressed in batch_rows:
            logs.append({
                "universe": universe,
                "username": username,
                "number": number,
                "typing_log": decompress(blob) if compressed else blob,
            })

        offset += batch_size

    return logs


async def get_log(username, number, universe):
    race = db.fetch("""
        SELECT log, compressed
        FROM typing_logs
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [universe, username, number])[0]

    if not race:
        return None

    return decompress(race["log"]) if race["compressed"] else race["log"]
