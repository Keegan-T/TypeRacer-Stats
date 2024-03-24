from database import db


def add_race(username, number, race):
    race_id = f"{username}|{number}"
    db.run("""
        INSERT INTO real_speeds
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        race_id, username, race["text_id"], number, race["lagged"],
        race["unlagged"], race["adjusted"], race["ping"], race["start"]
    ])