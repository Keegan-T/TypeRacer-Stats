from database import db
from collections import defaultdict
import api.texts as texts_api
import database.modified_races as modified_races
import database.texts as texts
from database.alts import get_alts


def add_results(results):
    db.run_many("""
        INSERT OR IGNORE INTO text_results
        VALUES (?, ?, ?, ?, ?, ?)
    """, results)


def get_count():
    number = db.fetch("SELECT COUNT(DISTINCT text_id) FROM text_results")[0][0]

    return number


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


def get_top_10(text_id):
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
        if len(top_10) == 10:
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

    return sorted_users[:10], len(top_10s)


async def update_results(text_id):
    text_id = int(text_id)
    disabled_text_ids = texts.get_disabled_text_ids()
    if text_id in disabled_text_ids:
        return

    scores = []

    top_10_database = texts.get_top_10(text_id)
    for score in top_10_database:
        scores.append((
            score["id"], text_id, score["username"],
            score["number"], score["wpm"], score["timestamp"],
        ))

    top_10_api = await texts_api.get_top_10(text_id)
    modified_ids = modified_races.get_ids()
    for score in top_10_api:
        race, user = score
        username = user["id"][3:]
        number = race["gn"]
        id = f"{username}|{number}"

        if id in modified_ids:
            continue

        scores.append((
            id, text_id, username,
            number, race["wpm"], race["t"],
        ))

    print(f"Adding {len(scores)} scores")
    add_results(scores)
    print("Added scores.")


def delete_result(id):
    db.run("""
        DELETE FROM text_results
        WHERE id = ?
    """, [id])


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
