from database.main import db
from database.main.alts import get_alts
from utils import urls
from utils.text_difficulty import set_difficulties


def add_texts(text_list, universe):
    text_list = set_difficulties(text_list)
    db.run_many("""
        INSERT OR IGNORE INTO texts
        (text_id, quote)
        VALUES (?, ?)
    """, [(text["text_id"], text["quote"]) for text in text_list])

    db.run_many("""
        INSERT OR IGNORE INTO text_universes
        VALUES (?, ?, ?, ?)
    """, [(universe, text["text_id"], 0, text["difficulty"]) for text in text_list])


def add_text(text, universe):
    db.run(f"""
        INSERT OR IGNORE INTO texts
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        text["tid"], text["text"], text["type"], text["title"], text["author"],
        text["language"], text["min_skill"], text["max_skill"], text["contributor"]
    ])

    db.run("""
        INSERT OR IGNORE INTO text_universes
        VALUES (?, ?, ?, ?)
    """, [universe, text["tid"], 0, 0])

    update_text_difficulties(universe)


def update_text(text):
    db.run("""
        UPDATE texts
        SET quote = ?, media = ?, title = ?, author = ?,
        language = ?, min_skill = ?, max_skill = ?, contributor = ?
        WHERE text_id = ?
    """, [
        text["text"], text["type"], text["title"], text["author"], text["language"],
        text["min_skill"], text["max_skill"], text["contributor"], text["tid"],
    ])

    universes = db.fetch("""
        SELECT DISTINCT(universe) FROM text_universes
        WHERE text_id = ?
    """, [text["tid"]])

    for universe in universes:
        update_text_difficulties(universe[0])


def get_texts(as_dictionary=False, get_disabled=True, universe="play", text_pool="all"):
    from database.main.races import maintrack_text_pool
    text_pool_string = (
        f"AND text_id IN ({",".join([str(tid) for tid in maintrack_text_pool])})"
        if text_pool != "all" and universe == "play" else ""
    )

    texts = db.fetch(f"""
        SELECT texts.*, text_universes.* FROM texts
        JOIN text_universes USING (text_id)
        WHERE universe = ?
        {'AND disabled = 0' * (not get_disabled)}
        {text_pool_string}
    """, [universe])

    text_list = []
    for text in texts:
        text = dict(text)
        text["ghost"] = urls.ghost(text["text_id"], universe)
        text_list.append(text)

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

    text = dict(text[0])
    text["ghost"] = urls.ghost(text["text_id"], universe)
    return text


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

    results.sort(key=lambda x: x["wpm_adjusted"], reverse=True)

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


async def get_text_repeat_leaderboard(text_id, limit):
    leaderboard = await db.fetch_async("""
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


def update_text_difficulties(universe):
    text_list = db.fetch("""
        SELECT * FROM texts
        JOIN text_universes USING(text_id)
        WHERE universe = ?
        AND disabled = 0
    """, [universe])
    text_list = [dict(text) for text in text_list]
    text_list = set_difficulties(text_list)
    results = [(text["difficulty"], universe, text["text_id"]) for text in text_list]
    db.run_many(f"""
        UPDATE text_universes
        SET difficulty = ?
        WHERE universe = ?
        AND text_id = ?
    """, results)
