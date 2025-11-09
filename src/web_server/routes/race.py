from datetime import datetime

import aiohttp_jinja2

from api.users import get_stats
from commands.account.download import run as download
from database.main import users, races, texts


@aiohttp_jinja2.template("race.html")
async def race_page(request):
    username = request.match_info.get("username")
    race_number = request.match_info.get("number")

    universe = request.query.get("universe")
    if not universe:
        universe = "play"

    db_stats = users.get_user(username, universe)
    if not db_stats:
        raise ValueError("Import Required")

    stats = await get_stats(username, universe=universe)
    await download(racer=stats, universe=universe)

    try:
        race_number = int(race_number)
        race_info = await races.get_race(username, race_number, universe, get_log=True)
        if not race_info:
            raise ValueError
    except ValueError:
        raise ValueError("Race Not Found")

    quote = texts.get_text(race_info["text_id"], universe)["quote"]

    data = {
        "username": username,
        "race_number": race_number,
        "race_number_formatted": f"{race_number:,}",
        "universe": universe,
        "date": datetime.fromtimestamp(race_info["timestamp"]).strftime("%b %d %Y, %I:%M:%S %p"),
        "points": f"{race_info["points"]:,.0f}",
        "rank": race_info["rank"],
        "racers": race_info["racers"],
        "wpm_unlagged": f"{race_info["wpm_unlagged"]:,.2f}",
        "wpm_adjusted": f"{race_info["wpm_adjusted"]:,.2f}",
        "accuracy": f"{race_info["accuracy"]:.2%}",
        "start_time": f"{race_info["start_time"] / 1000:,.3f}",
        "total_time": f"{race_info["total_time"] / 1000:,.2f}",
        "text_id": race_info["text_id"],
        "quote": quote,
    }

    if "raw_unlagged" in race_info:
        data |= {
            "raw_unlagged": f"{race_info["raw_unlagged"]:,.2f}",
            "raw_adjusted": f"{race_info["raw_adjusted"]:,.2f}",
            "correction_time": f"{race_info["correction_time"] / 1000:,.2f}",
            "correction_percent": f"{race_info["correction_percent"]:.2%}",
            "pauseless_adjusted": f"{race_info["pauseless_adjusted"]:,.2f}",
            "pause_time": f"{race_info["pause_time"] / 1000:,.2f}",
            "pause_percent": f"{race_info["pause_percent"]:.2%}",
            "characters": [char for char in quote],
            "delays": race_info["delays"],
            "typing_log": race_info["log"],
        }

    return data