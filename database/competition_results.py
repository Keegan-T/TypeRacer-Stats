from database import db


def get_competitions():
    results = db.fetch("SELECT * FROM competition_results")

    competitions = {}

    for result in results:
        id = result["id"]
        competitor = {
            "username": result["username"],
            "points": result["points"],
            "races": result["races"],
            "wpm_average": result["wpm_average"],
            "accuracy": result["accuracy"],
        }

        if id in competitions:
            competitions[id]["competitors"].append(competitor)
        else:
            competitions[id] = {
                "id": id,
                "competitors": [competitor],
                "type": result["type"],
                "start_time": result["start_time"],
                "end_time": result["end_time"],
            }

    return competitions.values()


def get_count():
    count = db.fetch("SELECT COUNT(DISTINCT id) AS get_count FROM competition_results")[0]["get_count"]

    return count


def get_latest():
    latest_list = db.fetch("""
        SELECT * FROM (
            SELECT id, type, start_time, end_time, ROW_NUMBER()
            OVER (PARTITION BY type ORDER BY end_time DESC) AS row_num
            FROM competition_results
        ) AS latest
        WHERE row_num = 1
    """)

    latest = {}
    for comp in latest_list:
        latest[comp["type"]] = comp

    return latest


def add_results(competition):
    for result in competition["competitors"]:
        db.run("""
            INSERT INTO competition_results
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            competition["id"], result["username"], result["points"], result["races"],
            result["average_wpm"], result["accuracy"], competition["type"],
            competition["start_time"], competition["end_time"]
        ])


def get_awards(username=None):
    awards = {}
    ranks = ["first", "second", "third"]

    competitions = get_competitions()
    for competition in competitions:
        kind = competition["type"]
        competitors = competition["competitors"]
        podium = sorted(competitors, key=lambda x: x["points"], reverse=True)[:3]
        for position, competitor in enumerate(podium):
            user = competitor['username']
            if user not in awards:
                awards[user] = {
                    'day': {'first': 0, 'second': 0, 'third': 0},
                    'week': {'first': 0, 'second': 0, 'third': 0},
                    'month': {'first': 0, 'second': 0, 'third': 0},
                    'year': {'first': 0, 'second': 0, 'third': 0},
                    'total': 0
                }
            awards[user][kind][ranks[position]] += 1
            awards[user]['total'] += 1

    if username:
        if username in awards:
            return awards[username]
        else:
            return {
                'day': {'first': 0, 'second': 0, 'third': 0},
                'week': {'first': 0, 'second': 0, 'third': 0},
                'month': {'first': 0, 'second': 0, 'third': 0},
                'year': {'first': 0, 'second': 0, 'third': 0},
                'total': 0
            }

    awards_list = dict(sorted(awards.items(), key=lambda x: x[1]["total"], reverse=True))

    return awards_list
