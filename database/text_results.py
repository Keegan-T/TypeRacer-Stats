from database import db
from collections import defaultdict
import api.texts as texts_api
import database.modified_races as modified_races
import database.texts as texts
import utils


def get_count():
    number = db.fetch("SELECT COUNT(DISTINCT text_id) FROM text_results")[0][0]

    return number

def get_top_10s():
    results = db.fetch("SELECT * FROM text_results")

    top_10s = defaultdict(list)
    for result in results:
        top_10s[result["text_id"]].append(result)

    filtered_top_10s = {}
    for text_id, scores in top_10s.items():
        scores.sort(key=lambda x: x["wpm"], reverse=True)

        unique_scores = {}
        for score in scores:
            username = score["username"]
            if username not in unique_scores:
                unique_scores[username] = score

        filtered_top_10s[text_id] = [score for score in unique_scores.values()][:10]

    return filtered_top_10s

def get_top_10(text_id):
    top_10 = db.fetch("""
        SELECT * FROM text_results
        WHERE text_id = ?
        AND (username, wpm) IN (
            SELECT username, MAX(wpm)
            FROM text_results
            WHERE text_id = ?
            GROUP BY username
        )
        ORDER BY wpm DESC
        LIMIT 10
    """, [text_id, text_id])

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
    modified_ids = modified_races.get_ids()
    utils.time_start()
    api_top_10 = await texts_api.get_top_10(text_id)
    utils.time_end()

    scores = []

    ids = []
    for score in api_top_10:
        race, user = score
        username = user["id"][3:]
        number = race["gn"]
        id = f"{username}|{number}"

        if id in modified_ids:
            continue

        scores.append({
            "id": id,
            "username": username,
            "number": number,
            "wpm": race["wpm"],
            "timestamp": race["t"],
        })
        ids.append(id)

    top_10_database = texts.get_top_10(text_id)

    new_scores = [score for score in top_10_database if score["id"] not in ids]
    for score in new_scores:
        scores.append({
            "id": score["id"],
            "username": score["username"],
            "number": score["number"],
            "wpm": score["wpm"],
            "timestamp": score["timestamp"],
        })

    top_10 = sorted(scores, key=lambda x: x["wpm"], reverse=True)[:10]
    params = []
    for score in top_10:
        params += [score["id"], int(text_id), score["username"],
                   score["number"], score["wpm"], score["timestamp"]]

    value_string = ("(?, ?, ?, ?, ?, ?)," * (len(top_10)))[:-1]

    db.run(f"""
        INSERT OR IGNORE INTO text_results
        VALUES {value_string}
    """, params)

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