from database.main import db


def get_ids():
    rows = db.fetch("""
        SELECT universe || '|' || username || '|' || number AS id FROM modified_races
    """)

    return set([row[0] for row in rows])


def get_races():
    return db.fetch("SELECT * FROM modified_races")


def get_race(universe, username, number):
    race = db.fetch("""
        SELECT * FROM modified_races
        WHERE universe = ?
        AND username = ?
        AND number = ?
    """, [universe, username, number])

    if not race:
        return None

    return race[0]


def add_race(universe, username, race_number, wpm_registered, wpm_modified):
    db.run("""
        INSERT OR IGNORE INTO modified_races
        VALUES (?, ?, ?, ?, ?)
    """, [universe, username, race_number, wpm_registered, wpm_modified])
