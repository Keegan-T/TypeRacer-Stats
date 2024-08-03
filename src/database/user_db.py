import sqlite3

db = sqlite3.connect("./data/users.db")
db.row_factory = sqlite3.Row


def fetch(query, params=[]):
    cursor = db.cursor()
    try:
        cursor.execute(query, params)

        return cursor.fetchall()

    finally:
        cursor.close()


def run(query, params=[]):
    cursor = db.cursor()

    try:
        cursor.execute(query, params)
        db.commit()

    finally:
        cursor.close()
