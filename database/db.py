import sqlite3
import aiosqlite

file = "./data/typeracerstats.db"
reader = sqlite3.connect(file)
writer = sqlite3.connect(file)
reader.row_factory = sqlite3.Row
writer.row_factory = sqlite3.Row
writer.execute("PRAGMA journal_mode = WAL")

def fetch(query, params=[]):
    cursor = reader.cursor()
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()


async def fetch_async(query, params=[]):
    async with aiosqlite.connect(file) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


def run(query, params=[]):
    cursor = writer.cursor()
    try:
        cursor.execute(query, params)
        writer.commit()
    finally:
        cursor.close()


def run_many(query, data):
    cursor = writer.cursor()
    try:
        cursor.executemany(query, data)
        writer.commit()
    finally:
        cursor.close()