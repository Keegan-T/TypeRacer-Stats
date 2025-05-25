from collections import defaultdict

import database.main.db as db


def add_alt(new_username, existing_username):
    exists = db.fetch("SELECT * FROM alts WHERE username = ?", [new_username])
    if exists:
        return False

    result = db.fetch("SELECT group_id FROM alts WHERE username = ?", [existing_username])
    if not result:
        group_id = db.fetch("SELECT IFNULL(MAX(group_id), 0) + 1 from alts")[0][0]
        db.run("INSERT INTO alts VALUES (?, ?)", [existing_username, group_id])
    else:
        group_id = result[0][0]

    db.run("INSERT OR IGNORE INTO alts VALUES (?, ?)", [new_username, group_id])
    return True


def get_alts():
    alt_list = db.fetch("SELECT * FROM alts")
    groups = defaultdict(list)

    for username, group_id in alt_list:
        groups[group_id].append(username)

    alts = {}
    for username, group_id in alt_list:
        alts[username] = groups[group_id]

    return alts

def get_username_alts(username):
    group_id = db.fetch("SELECT group_id FROM alts WHERE username = ?", [username])
    if not group_id:
        return []
    alt_list = db.fetch("SELECT username FROM alts WHERE group_id = ?", [group_id[0][0]])

    return sorted([alt["username"] for alt in alt_list])

def get_groups():
    groups = db.fetch("""
        SELECT group_id, GROUP_CONCAT(username) AS usernames
        FROM alts
        GROUP BY group_id
    """)

    return groups


def remove_alt(username):
    db.run("DELETE FROM alts WHERE username = ?", [username])
