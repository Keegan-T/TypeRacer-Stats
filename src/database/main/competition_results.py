import copy
from collections import defaultdict

from database.main import db


async def get_competitions(start_date=None, end_date=None):
    start_string = f"AND start_time >= {start_date}" if start_date else ""
    end_string = f"AND end_time < {end_date}" if end_date else ""

    results = await db.fetch_async(f"""
        SELECT * FROM competition_results
        WHERE 1
        {start_string}
        {end_string}
    """)

    competitions = defaultdict(lambda: {
        "start_time": None,
        "end_time": None,
        "period": None,
        "competitors": []
    })

    for result in results:
        key = (result["start_time"], result["end_time"], result["period"])
        comp = competitions[key]
        comp["start_time"], comp["end_time"], comp["period"] = key
        comp["competitors"].append({
            "username": result["username"],
            "points": result["points"],
            "races": result["races"],
            "wpm_average": result["wpm_average"],
            "accuracy": result["accuracy"],
        })

    return competitions.values()


def get_competition_count():
    count = db.fetch("""
        SELECT COUNT(DISTINCT start_time || "-" || end_time || "-" || period) AS competition_count
        FROM competition_results
    """)[0]["competition_count"]

    return count


def get_latest_competitions():
    latest = {}
    for period in "day", "week", "month", "year":
        end_time = db.fetch(f"""
            SELECT end_time FROM competition_results
            WHERE period = '{period}'
            ORDER BY end_time DESC
            LIMIT 1
        """)[0]
        latest[period] = end_time

    return latest


def add_results(competition):
    results = []
    for result in competition["competitors"]:
        results.append((
            competition["start_time"], competition["end_time"], competition["period"],
            result["username"], result["points"], result["races"],
            result["average_wpm"], result["accuracy"],
        ))

    db.run_many("""
        INSERT INTO competition_results
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, results)


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
        period = competition["period"]
        competitors = competition["competitors"]
        podium = sorted(competitors, key=lambda x: x["points"], reverse=True)[:3]
        for position, competitor in enumerate(podium):
            user = competitor["username"]
            if user not in awards:
                awards[user] = copy.deepcopy(award_dict)
            awards[user][period][ranks[position]] += 1
            awards[user]["total"] += 1

    if username:
        if username in awards:
            return awards[username]
        else:
            return copy.deepcopy(award_dict)

    awards_list = dict(sorted(awards.items(), key=lambda x: x[1]["total"], reverse=True))

    return awards_list
