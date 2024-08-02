import database.user_db as db


def get_users():
    users = db.fetch("SELECT * FROM important_users")

    return [user['username'] for user in users]


def add_user(username):
    db.run("""
        INSERT OR IGNORE INTO important_users
        VALUES (?)
    """, [username])


def remove_user(username):
    db.run("""
        DELETE FROM important_users
        WHERE username = ?
    """, [username])
