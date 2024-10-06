import copy

from database import db


async def get_competitions(start_date=None, end_date=None):
    start_string = f"AND start_time >= {start_date}" if start_date else ""
    end_string = f"AND end_time < {end_date}" if end_date else ""

    results = await db.fetch_async(f"""
        SELECT * FROM competition_results
        WHERE 1
        {start_string}
        {end_string}
    """)

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


async def get_awards(username=None, start_date=None, end_date=None):
    awards = {}
    ranks = ["first", "second", "third"]

    award_dict = {
        "day": {"first": 0, "second": 0, "third": 0},
        "week": {"first": 0, "second": 0, "third": 0},
        "month": {"first": 0, "second": 0, "third": 0},
        "year": {"first": 0, "second": 0, "third": 0},
        "total": 0
    }

    competitions = await get_competitions(start_date, end_date)
    for competition in competitions:
        kind = competition["type"]
        competitors = competition["competitors"]
        podium = sorted(competitors, key=lambda x: x["points"], reverse=True)[:3]
        for position, competitor in enumerate(podium):
            user = competitor["username"]
            if user not in awards:
                awards[user] = copy.deepcopy(award_dict)
            awards[user][kind][ranks[position]] += 1
            awards[user]["total"] += 1

    if username:
        if username in awards:
            return awards[username]
        else:
            return copy.deepcopy(award_dict)

    awards_list = dict(sorted(awards.items(), key=lambda x: x[1]["total"], reverse=True))

    return awards_list
