from database.main import db
from database.main.alts import get_alts
from utils.logging import log


def add_race(username, race_number, race):
    if not race_exists(username, race_number):
        log(f"New 300 WPM! {username}|{race_number}")
        db.run("""
            INSERT INTO club_races VALUES (?, ?, ?, ?)
        """, [
            username, race_number, race["adjusted"], race["timestamp"]
        ])


def race_exists(username, race_number):
    race = db.fetch("""
        SELECT * FROM club_races
        WHERE username = ?
        AND number = ?
    """, [username, race_number])

    return bool(race)


def get_club_scores():
    races = db.fetch("SELECT * FROM club_races ORDER BY wpm_adjusted DESC")

    return filter_scores([dict(race) for race in races])


def filter_scores(scores):
    alts = get_alts()
    top_scores = []
    added_users = set()

    i = 1
    for score in scores:
        username = score["username"]
        alt_accounts = {username} | set(alts.get(username, []))

        if not alt_accounts & added_users:
            score["position"] = i
            top_scores.append(score)
            added_users.update(alt_accounts)
            i += 1

    return top_scores


def delete_user_scores(username):
    db.run("""
        DELETE FROM club_races
        WHERE username = ?
    """, [username])
