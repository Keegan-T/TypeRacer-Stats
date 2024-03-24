import database.user_db as db


def get_banned():
    users = db.fetch("SELECT * FROM banned_users")

    return [user['id'] for user in users]


def ban(id):
    db.run("""
        INSERT OR IGNORE INTO banned_users
        VALUES (?)
    """, [id])


def unban(id):
    db.run("""
        DELETE FROM banned_users
        WHERE id = ?
    """, [id])