import asyncio
from collections import defaultdict

import api.texts as texts_api
import database.main.texts as texts
from api.core import date_to_timestamp
from api.users import get_stats
from database.main import deleted_races, db
from database.main.alts import get_alts
from database.main.users import get_disqualified_users


def add_results(results):
    db.run_many("""
        INSERT OR IGNORE INTO text_results
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, results)


def get_count():
    return db.fetch("SELECT COUNT(DISTINCT text_id) FROM text_results")[0][0]


def get_top_10s():
    results = db.fetch("SELECT * FROM text_results")
    alts = get_alts()

    top_10s = defaultdict(list)
    for result in results:
        top_10s[result["text_id"]].append(result)

    filtered_top_10s = {}
    for text_id, scores in top_10s.items():
        scores.sort(key=lambda x: x["wpm"], reverse=True)

        unique_scores = []
        for score in scores:
            username = score["username"]
            if username in alts:
                existing_score = next((score for score in unique_scores if score["username"] in alts[username]), None)
            else:
                existing_score = next((score for score in unique_scores if score["username"] == username), None)

            if not existing_score:
                unique_scores.append(score)

        filtered_top_10s[text_id] = unique_scores[:10]

    return filtered_top_10s


def get_top_n(text_id, n=10):
    results = db.fetch("""
        SELECT * FROM text_results
        WHERE text_id = ?
        ORDER BY wpm DESC
    """, [text_id])

    top_10 = []
    alts = get_alts()

    for result in results:
        username = result["username"]
        if username in alts:
            existing_score = next((score for score in top_10 if score["username"] in alts[username]), None)
        else:
            existing_score = next((score for score in top_10 if score["username"] == username), None)
        if existing_score:
            continue
        top_10.append(result)
        if len(top_10) == n:
            break

    return top_10


def get_top_10_counts(username):
    top_10s = get_top_10s()
    top_10_counts = [0] * 10

    for top_10 in top_10s.values():
        usernames = [race["username"] for race in top_10]
        if username in usernames:
            top_10_counts[usernames.index(username)] += 1

    return top_10_counts


def get_top_n_counts(n=10):
    top_10_users = defaultdict(int)

    top_10s = get_top_10s()
    for top_10 in top_10s.values():
        for race in top_10[:n]:
            top_10_users[race["username"]] += 1

    sorted_users = sorted(top_10_users.items(), key=lambda x: x[1], reverse=True)

    return sorted_users, len(top_10s)


async def import_users():
    from commands.account.download import run as download
    usernames = db.fetch("""
        SELECT DISTINCT username FROM text_results
        WHERE wpm_raw IS NULL
    """)

    for row in usernames:
        username = row["username"]
        stats = get_stats(username, universe="play")
        if not stats:
            continue
        await download(racer=stats, universe="play")
        await asyncio.sleep(5)


async def update_results(text_id):
    text_id = int(text_id)
    disabled_text_ids = texts.get_disabled_text_ids()
    if text_id in disabled_text_ids:
        return

    scores = []
    top_10_database = texts.get_top_10(text_id)
    for score in top_10_database:
        scores.append((
            text_id, score["username"], score["number"], score["wpm_adjusted"],
            score["wpm_raw"], score["accuracy"], score["timestamp"],
        ))

    database_ids = set([
        f"{race['universe']}|{race['username']}|{race['number']}"
        for race in top_10_database
    ])
    exclusions = deleted_races.get_ids() | database_ids
    banned_users = get_disqualified_users()
    top_10_api = await texts_api.get_top_results(text_id)
    for score in top_10_api:
        username = score["user"]
        number = score["rn"]
        if f"play|{username}|{number}" in exclusions or username in banned_users:
            continue

        scores.append((
            text_id, username, number, score["wpm"],
            None, score.get("ac", None), date_to_timestamp(score["t"]),
        ))

    add_results(scores)


def delete_result(username, race_number):
    db.run("""
        DELETE FROM text_results
        WHERE username = ?
        AND number = ?
    """, [username, race_number])


def delete_results(text_id):
    db.run("""
        DELETE FROM text_results
        WHERE text_id = ?
    """, [text_id])


def delete_user_results(username):
    db.run("""
        DELETE FROM text_results
        WHERE username = ?
    """, [username])
