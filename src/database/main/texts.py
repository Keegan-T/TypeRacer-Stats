from database.main import db
from database.main.alts import get_alts
from utils import urls
from utils.text_difficulty import set_difficulties


def text_dict(text):
    return {
        "text_id": text["text_id"],
        "quote": text["quote"],
        "ghost": urls.ghost(text["ghost_username"], text["ghost_number"], text["universe"]),
        "difficulty": text["difficulty"],
        "disabled": text["disabled"],
    }


def add_texts(text_list, universe):
    difficulty = 0
    db.run_many(f"""
        INSERT OR IGNORE INTO texts
        VALUES (?, ?, ?)
    """, [(text["text_id"], text["quote"], difficulty) for text in text_list])

    db.run("""
        INSERT OR IGNORE INTO text_universes
        VALUES (?, ?, ?, ?)
    """, [(universe, text["text_id"], text["username"], text["race_number"]) for text in text_list])


def add_text(text, universe):
    difficulty = 0
    db.run_many(f"""
        INSERT OR IGNORE INTO texts
        VALUES (?, ?, ?)
    """, [text["text_id"], text["quote"], difficulty])

    db.run("""
        INSERT OR IGNORE INTO text_universes
        VALUES (?, ?, ?, ?)
    """, [universe, text["text_id"], text["username"], text["race_number"]])


def get_texts(as_dictionary=False, get_disabled=True, universe="play"):
    texts = db.fetch(f"""
        SELECT texts.*, text_universes.* FROM texts
        JOIN text_universes USING (text_id)
        WHERE universe = ?
        {'AND disabled = 0' * (not get_disabled)}
    """, [universe])

    text_list = [text_dict(text) for text in texts]

    if as_dictionary:
        return {text["text_id"]: text for text in text_list}

    return text_list


def get_text(text_id, universe="play"):
    text = db.fetch(f"""
        SELECT texts.*, text_universes.* FROM texts
        JOIN text_universes USING (text_id)
        WHERE universe = ?
        AND text_id = ?
    """, [universe, text_id])

    if not text:
        return None

    return text_dict(text[0])


def get_text_count(universe="play"):
    text_count = db.fetch(f"""
        SELECT COUNT(*)
        FROM text_universes
        WHERE universe = ?
        AND disabled = 0
    """, [universe])[0][0]

    return text_count


def get_disabled_text_ids():
    texts = db.fetch("""
        SELECT text_id FROM text_universes
        WHERE disabled = 1
    """)

    return [text["text_id"] for text in texts]


def get_top_10(text_id):
    from database.main.users import get_disqualified_users
    results = db.fetch("""
        SELECT * FROM races
        WHERE universe = "play"
        AND text_id = ?
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
    return  # Disabled until needed
    texts = get_texts(get_disabled=False)
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
        text_id = text["text_id"]
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


async def _toggle_text(text_id, state):
    from database.main.text_results import update_results, delete_results
    from database.main.users import update_text_stats

    db.run("""
        UPDATE text_universes
        SET disabled = ?
        WHERE universe = "play"
        AND text_id = ?
    """, [state, text_id])

    if state == 0:
        await update_results(text_id)
    else:
        delete_results(text_id)

    outdated_users = db.fetch("""
        SELECT DISTINCT username
        FROM races
        WHERE universe = "play"
        AND text_id = ?
    """, [text_id])

    for username in outdated_users:
        update_text_stats(str(username[0]), "play")


async def enable_text(text_id):
    await _toggle_text(text_id, 0)


async def disable_text(text_id):
    await _toggle_text(text_id, 1)


def get_text_repeat_leaderboard(text_id, limit):
    leaderboard = db.fetch("""
        SELECT races.username, country, COUNT(*) AS times
        FROM races
        JOIN users ON users.username = races.username
        WHERE text_id = ?
        GROUP BY races.username
        ORDER BY times DESC
        LIMIT ?
    """, [text_id, limit])

    return leaderboard


def filter_disabled(text_list):
    disabled_text_ids = get_disabled_text_ids()

    return [text for text in text_list if text["text_id"] not in disabled_text_ids]


def update_text_difficulties(universe="play"):
    text_list = db.fetch("""
        SELECT * FROM texts
        JOIN text_universes USING(text_id)
        WHERE universe = 'play'
        AND disabled = 0
    """)
    text_list = [dict(text) for text in text_list]
    text_list = set_difficulties(text_list)

    results = [(text["difficulty"], text["text_id"]) for text in text_list]
    db.run_many(f"UPDATE texts SET difficulty = ? WHERE text_id = ?", results)
