from database import db


def add_race(race):
    db.run("""
            INSERT INTO races_300
            VALUES (?, ?, ?, ?, ?)
        """,
           [
            race["username"], race["number"], race["timestamp"], race["wpm"], race["wpm_adjusted"]
        ]
           )

def get_races():
    races = db.fetch("""
        SELECT *
        FROM races_300
    """)

    return races

def get_races_unique_usernames():
    races = db.fetch("""
        WITH Club AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY username ORDER BY wpm_adjusted DESC) AS rank
            FROM races_300
        )
        SELECT *
        FROM Club
        WHERE rank = 1
        ORDER BY wpm_adjusted DESC
    """)

    return [dict(race) for race in races]

def update_race(score):
    db.run(
        """
            UPDATE races_300
            SET race_id = ?
            WHERE username = ?
        """,
        [
            score['race_id'], score['username']
        ]
    )