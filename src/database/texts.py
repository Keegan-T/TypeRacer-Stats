import sqlite3

from database import db
from database.alts import get_alts
from utils import urls
from utils.text_difficulty import set_difficulties


def table_name(universe):
    table = "texts"
    if universe != "play":
        table += f"_{universe}"

    return table.replace("-", "_")


def create_table(universe):
    db.run(f"""
        CREATE TABLE {table_name(universe)} (
            id INTEGER PRIMARY KEY,
            quote TEXT,
            disabled INTEGER,
            ghost TEXT,
            difficulty REAL
        )    
    """)


def add_texts(text_list, universe):
    db.run_many(f"""
        INSERT OR IGNORE INTO {table_name(universe)}
        VALUES (?, ?, ?, ?, NULL)
    """, text_list)


def get_texts(as_dictionary=False, include_disabled=True, universe="play"):
    table = table_name(universe)
    texts = db.fetch(f"""
        SELECT * FROM {table}
        {'WHERE disabled = 0' * (not include_disabled)}
        ORDER BY id ASC
    """)

    if as_dictionary:
        return {
            t["id"]: {
                "quote": t["quote"],
                "disabled": t["disabled"],
                "ghost": t["ghost"],
                "difficulty": t["difficulty"],
            } for t in texts
        }

    return [dict(text) for text in texts]


def get_text(text_id, universe="play"):
    table = table_name(universe)
    text = db.fetch(f"""
        SELECT * FROM {table}
        WHERE id = ?
    """, [text_id])

    if not text:
        return None

    return text[0]


def get_text_count(universe="play"):
    table = table_name(universe)
    text_count = db.fetch(f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE disabled = 0
    """)[0][0]

    return text_count


def get_disabled_text_ids():
    texts = db.fetch("""
        SELECT id FROM texts
        WHERE disabled = 1
    """)

    return [text[0] for text in texts]


def add_text(text, universe):
    table = table_name(universe)
    db.run(f"""
        INSERT INTO {table}
        VALUES (?, ?, ?, ?, ?)
    """, [text["id"], text["quote"], False, text["ghost"], text["difficulty"]])


def update_text(text_id, quote):
    db.run("""
        UPDATE texts
        SET quote = ?
        WHERE id = ? 
    """, [quote, text_id])


def get_top_10(text_id):
    from database.users import get_disqualified_users
    results = db.fetch("""
        SELECT * FROM races
        WHERE text_id = ?
    """, [text_id])

    results.sort(key=lambda x: x["wpm"], reverse=True)

    top_10 = []
    alts = get_alts()
    banned = set(get_disqualified_users())

    for result in results:
        username = result["username"]
        if username in banned:
            continue
        if username in alts:
            existing_score = next((score for score in top_10 if score["username"] in alts[username]), None)
        else:
            existing_score = next((score for score in top_10 if score["username"] == username), None)
        if existing_score:
            continue
        top_10.append(result)
        if len(top_10) == 10:
            break

    return top_10


def update_slow_ghosts():
    texts = get_texts(include_disabled=False)
    ghosts = {}

    with open("./data/slow_ghosts.txt", "r") as slow_ghosts:
        lines = slow_ghosts.readlines()

    for ghost in lines:
        text_id, username, race_number = ghost.strip().split(",")
        ghosts[text_id] = (username, race_number)

    slow_texts = db.fetch("""
        SELECT * FROM races
        WHERE username = 'slowtexts'
        AND wpm < 100
    """)

    for text in texts:
        text_id = text["id"]
        if str(text_id) not in ghosts:
            race = next((race for race in slow_texts if race["text_id"] == text_id), None)
            if not race:
                community_worst = db.fetch("""
                    SELECT username, number
                    FROM races
                    WHERE text_id = ?
                    ORDER BY wpm ASC
                    LIMIT 1
                """, [text_id])
                if community_worst:
                    race = community_worst

            if race:
                link = urls.ghost(race["username"], race["number"])
                db.run("UPDATE texts SET ghost = ? WHERE id = ?", [link, text_id])


async def enable_text(text_id):
    from database.text_results import update_results
    from database.users import update_text_stats

    db.run("""
        UPDATE texts
        SET disabled = 0
        WHERE id = ?
    """, [text_id])

    await update_results(text_id)

    outdated_users = db.fetch("""
        SELECT DISTINCT username
        FROM races
        WHERE text_id = ?
    """, [text_id])

    for username in outdated_users:
        username = str(username[0])
        update_text_stats(username)


def disable_text(text_id):
    from database.text_results import delete_results
    from database.users import update_text_stats

    db.run("""
        UPDATE texts
        SET disabled = 1
        WHERE id = ?
    """, [text_id])

    delete_results(text_id)

    outdated_users = db.fetch("""
        SELECT DISTINCT username
        FROM races
        WHERE text_id = ?
    """, [text_id])

    for username in outdated_users:
        username = str(username[0])
        update_text_stats(username, "play")


def get_text_repeat_leaderboard(text_id):
    leaderboard = db.fetch("""
        SELECT races.username, country, COUNT(*) AS times
        FROM races
        JOIN users ON users.username = races.username
        WHERE text_id = ?
        GROUP BY races.username
        ORDER BY times DESC
        LIMIT 10
    """, [text_id])

    return leaderboard


def universe_exists(universe):
    table = table_name(universe)
    try:
        db.fetch(f"SELECT * FROM {table}")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return False

    return True


def filter_disabled_texts(text_list):
    disabled_text_ids = get_disabled_text_ids()

    return [text for text in text_list if text["text_id"] not in disabled_text_ids]


def update_text_difficulties(universe="play"):
    print(f"Updating text difficulties for {universe}... ")
    table = table_name(universe)
    text_list = get_texts(include_disabled=False, universe=universe)
    if not text_list:
        return
    text_list = set_difficulties(text_list)
    results = [(text["difficulty"], text["id"]) for text in text_list]

    db.run_many(f"""
        UPDATE {table} SET difficulty = ? WHERE id = ?
    """, results)


async def update_all_text_difficulties():
    update_text_difficulties("play")
    table_list = db.fetch("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'texts_%'")
    for table in table_list:
        update_text_difficulties("_".join(table["name"].split("_")[1:]))
