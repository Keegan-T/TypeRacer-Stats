import sqlite3

db = sqlite3.connect("./data/typeracerstats.db")
db.row_factory = sqlite3.Row

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

def run(query, params=[]):
    cursor = db.cursor()

    try:
        cursor.execute(query, params)
        db.commit()

    except Exception as e:
        print(f"Error executing query: {e}")
        raise

    finally:
        cursor.close()