from database import db


def get_races():
    races = db.fetch("SELECT * FROM modified_races")

    race_list = []
    for race in races:
        race_list.append({
            "username": race["username"],
            "number": race["number"],
            "wpm": race["wpm"],
        })

    return race_list

def get_ids():
    rows = db.fetch("SELECT id FROM modified_races")
    ids = [row[0] for row in rows]

    return ids

def get_race(username, number):
    race = db.fetch("""
        SELECT * FROM modified_races
        WHERE username = ?
        AND number = ?
    """, [username, number])

    if not race:
        return None

    return race[0]

def add_race(username, race_number, wpm, unlagged_wpm):
    db.run("""
        INSERT OR IGNORE INTO modified_races
        VALUES (?, ?, ?, ?, ?)
    """, [f"{username}|{race_number}", username, race_number, wpm, unlagged_wpm])

def add_cheated_race(username, race):
    number = race["gn"]
    id = f"{username}|{number}"
    db.run("""
        INSERT OR IGNORE INTO modified_races
        VALUES (?, ?, ?, ?, ?)
    """, [id, username, number, race["wpm"], None])