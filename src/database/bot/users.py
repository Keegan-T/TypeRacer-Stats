import json

from discord.ext import commands

import database.bot.db as db
from utils import dates
from utils.colors import default_colors


def get_users():
    users = db.fetch("SELECT * FROM users")

    return users


def get_user_ids():
    users = db.fetch("SELECT id FROM users")

    return [int(user[0]) for user in users]


def get_user(ctx, auto_add=True):
    if isinstance(ctx, commands.Context):
        user_id = str(ctx.author.id)
    else:
        user_id = str(ctx)

    user = db.fetch("""
        SELECT * FROM users
        WHERE id = ?
    """, [user_id])

    if not user:
        if auto_add:
            return add_user(user_id)
        return None

    user = dict(user[0])
    user["colors"] = json.loads(user["colors"])
    user["commands"] = json.loads(user["commands"])

    return user


def get_all_commands():
    all_commands = db.fetch("""
        SELECT id, commands FROM users
    """)

    return [{
        "id": user["id"],
        "commands": json.loads(user["commands"])
    } for user in all_commands]


def get_total_commands():
    all_commands = db.fetch("""
        SELECT commands FROM users
    """)

    total_commands = {}
    for user in all_commands:
        user_commands = json.loads(user["commands"])
        for command in user_commands:
            if command in total_commands:
                total_commands[command] += user_commands[command]
            else:
                total_commands[command] = user_commands[command]

    return total_commands


def get_commands(user_id):
    user = db.fetch("""
        SELECT commands FROM users
        WHERE id = ?
    """, [user_id])

    if not user:
        return None

    user_commands = json.loads(user[0]["commands"])

    return user_commands


def get_top_users():
    users = db.fetch("SELECT id, commands FROM users")
    top_users = []
    for discord_id, commands in users:
        total_commands = sum(json.loads(commands).values())
        top_users.append((discord_id, total_commands))

    top_users.sort(key=lambda x: x[1], reverse=True)

    return top_users


def add_user(id):
    user = {
        "id": id,
        "username": None,
        "universe": "play",
        "colors": default_colors,
        "commands": {},
        "start_date": None,
        "end_date": None,
        "joined": round(dates.now().timestamp()),
    }

    db.run("""
        INSERT INTO users
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        user["id"], user["username"], user["universe"], json.dumps(user["colors"]),
        "{}", user["start_date"], user["end_date"], user["joined"]
    ])

    return user


def update_username(id, username):
    db.run("""
        UPDATE users
        SET username = ?
        WHERE id = ?
    """, [username, id])


def update_colors(id, colors):
    db.run("""
        UPDATE users
        SET colors = ?
        WHERE id = ?
    """, [json.dumps(colors), id])


def update_universe(id, universe):
    db.run("""
        UPDATE users
        SET universe = ?
        WHERE id = ?
    """, [universe, id])


def update_commands(user_id, command, value=None):
    user_id = str(user_id)

    user_commands = db.fetch("""
        SELECT commands FROM users
        WHERE id = ?
    """, [user_id])[0][0]

    user_commands = json.loads(user_commands)

    if value is not None:
      user_commands[command] = value
    elif command in user_commands:
        user_commands[command] += 1
    else:
        user_commands[command] = 1

    db.run("""
        UPDATE users
        SET commands = ?
        WHERE id = ?
    """, [json.dumps(user_commands), user_id])


def update_date_range(user_id, start_date, end_date):
    start_time = None
    if start_date:
        start_time = start_date.timestamp()
    end_time = None
    if end_date:
        end_time = end_date.timestamp()

    db.run("""
        UPDATE USERS
        SET start_date = ?, end_date = ?
        WHERE id = ?
    """, [start_time, end_time, user_id])
