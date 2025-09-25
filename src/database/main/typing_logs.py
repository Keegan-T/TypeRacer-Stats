import asyncio
import sqlite3
import zlib

from database.main import db
from utils import logging


def decompress(log):
    return zlib.decompress(log).decode("utf-8")


def add_logs(typing_logs):
    db.run_many(f"""
        INSERT OR IGNORE INTO typing_logs
        VALUES (?, ?, ?, ?, 0)
    """, [(
        race["universe"], race["username"], race["number"], race["typing_log"],
    ) for race in typing_logs])


async def compress_logs(batch_size=1000):
    total_compressed = 0
    last_universe = None
    last_username = None
    last_number = None

    while True:
        if last_universe is None:
            rows = db.fetch("""
                SELECT universe, username, number, log 
                FROM typing_logs
                WHERE compressed = 0 
                ORDER BY universe, username, number
                LIMIT ?
            """, (batch_size,))
        else:
            rows = db.fetch("""
                SELECT universe, username, number, log 
                FROM typing_logs
                WHERE compressed = 0 
                AND (universe > ? 
                     OR (universe = ? AND username > ?)
                     OR (universe = ? AND username = ? AND number > ?))
                ORDER BY universe, username, number
                LIMIT ?
            """, (last_universe, last_universe, last_username,
                  last_universe, last_username, last_number, batch_size))

        if not rows:
            break

        updates = []
        for universe, username, number, log in rows:
            compressed_log = zlib.compress(log.encode("utf-8"), level=1)
            updates.append((
                sqlite3.Binary(compressed_log),
                universe,
                username,
                number
            ))
            last_universe = universe
            last_username = username
            last_number = number

        if updates:
            db.run_many("""
                UPDATE typing_logs 
                SET log = ?, compressed = 1 
                WHERE universe = ? AND username = ? AND number = ?
            """, updates)

            total_compressed += len(updates)
            logging.log(f"Compressed {len(updates):,} logs (total: {total_compressed:,})")

            await asyncio.sleep(0.01)

        del rows, updates
        import gc
        gc.collect()

    logging.log("Finished compressing logs")


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
