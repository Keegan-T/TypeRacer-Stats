from database import db


def add_race(race):
    db.run("""
        INSERT INTO races_300
        VALUES (?, ?, ?, ?, ?)
    """, [
        race["username"], race["number"], race["timestamp"],
        race["wpm"], race["wpm_adjusted"]
    ])

def add_new_race(username, race_number, race_info):
    race_list = get_races()
    in_list = False
    for race in race_list:
        if race["username"] == username and race["number"] == race_number:
            in_list = True
            break

    if not in_list:
        print(f"New 300 WPM! {username}|{race_number}")
        add_race({
            "username": username,
            "number": race_number,
            "timestamp": race_info["timestamp"],
            "wpm": race_info["lagged"],
            "wpm_adjusted": race_info["adjusted"],
        })


def get_races():
    races = db.fetch("SELECT * FROM races_300")

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

def delete_user_scores(username):
    db.run("""
        DELETE FROM races_300
        WHERE username = ?
    """, [username])