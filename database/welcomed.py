import database.user_db as db

def get_welcomed():
    welcomed = db.fetch("""
        SELECT * FROM welcomed
    """)

    return [user[0] for user in welcomed]

def add_welcomed(user_id):
    db.run("""
        INSERT OR IGNORE INTO welcomed
        VALUES (?)
    """, [user_id])

    return