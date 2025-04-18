from collections import defaultdict

import database.db as db


def add_alt(main_username, alt_username):
    result = db.fetch("SELECT group_id FROM alts WHERE username = ?", [main_username])
    if not result:
        group_id = db.fetch("SELECT IFNULL(MAX(group_id), 0) + 1 from alts")[0][0]
        db.run("INSERT INTO alts VALUES (?, ?)", [main_username, group_id])
    else:
        group_id = result[0][0]

    db.run("INSERT OR IGNORE INTO alts VALUES (?, ?)", [alt_username, group_id])


def get_alts():
    alt_list = db.fetch("SELECT * FROM alts")
    groups = defaultdict(list)

    for username, group_id in alt_list:
        groups[group_id].append(username)

    alts = {}
    for username, group_id in alt_list:
        alts[username] = groups[group_id]

    return alts


def remove_alt(username):
    db.run("DELETE FROM alts WHERE username = ?", [username])
