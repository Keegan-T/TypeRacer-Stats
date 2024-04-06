import sqlite3
import threading

import aiosqlite

db = sqlite3.connect("./data/typeracerstats.db")
db.row_factory = sqlite3.Row
db_lock = threading.Lock()


def fetch(query, params=[]):
    cursor = db.cursor()
    try:
        cursor.execute(query, params)

        return cursor.fetchall()

    except Exception as e:
        print(f"Error executing query: {e}")
        raise

    finally:
        cursor.close()


async def fetch_async(query, params=[]):
    async with aiosqlite.connect("./data/typeracerstats.db") as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


def run(query, params=[]):
    try:
        with db_lock:
            cursor = db.cursor()
            cursor.execute(query, params)
            db.commit()

    except Exception as e:
        print(f"Error executing query: {e}")
        raise

    finally:
        cursor.close()


def run_many(query, data):
    try:
        with db_lock:
            cursor = db.cursor()
            cursor.executemany(query, data)
            db.commit()

    except Exception as e:
        print(f"Error executing query: {e}")
        raise

    finally:
        cursor.close()