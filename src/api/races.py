import copy

from api.core import get, timestamp_to_date, date_to_timestamp, get_csv
from database.main import texts
from utils import logs
from utils.stats import calculate_points

text_cache = {}


async def get_races(username, start_time, end_time, races_per_page, universe="play"):
    after = timestamp_to_date(start_time)
    before = timestamp_to_date(end_time)
    result = await get(f"/racers/{username}/races", {
        "universe": universe,
        "after": after,
        "before": before,
        "keylog": "true",
        "n": races_per_page,
    })
    data = result["data"]

    return data


async def get_race(username, race_number, universe="play", get_typos=False, get_keystrokes=False):
    result = await get(f"/racers/{username}/races/{race_number}", {
        "universe": universe,
        "keylog": "true",
    })
    data = result["data"]
    if not data:
        return None

    return await get_race_details(data, get_typos, get_keystrokes)


async def get_races_historical(username, universe, bucket):
    data = await get_csv(f"/racers/{username}/historical/races", {
        "universe": universe,
        "bucket": bucket,
    })

    return data


async def get_race_details(data, get_typos=False, get_keystrokes=False):
    universe = data["univ"]
    global text_cache
    if not text_cache or universe != text_cache["universe"]:
        text_list = texts.get_texts(as_dictionary=True, universe=universe)
        text_cache = {
            "universe": universe,
            "texts": text_list,
        }
    else:
        text_list = text_cache["texts"]

    username = data["user"]
    race_number = data["rn"]
    text_id = data["tid"]
    quote = text_list[text_id]["quote"]
    lagged = data["wpm"]
    accuracy = data["acc"]
    if not accuracy:
        accuracy = 0
    points = data["pts"]
    if points == 0:
        points = calculate_points(quote, lagged)
    race_id = data["rid"]

    details = {
        "universe": universe,
        "username": username,
        "number": race_number,
        "text_id": text_id,
        "wpm": lagged,
        "accuracy": accuracy,
        "points": points,
        "rank": data["r"],
        "racers": data["nr"],
        "race_id": race_id,
        "timestamp": date_to_timestamp(data["t"]),
        "quote": quote,
        "log": data["kl"],
    }

    typing_log = details["log"]
    if not typing_log:
        return details

    return await logs.get_log_details(details, get_keystrokes, get_typos)


async def get_race_by_id(race_id):
    result = await get(f"/races/{race_id}", {
        "keylog": "true"
    })
    data = result["data"]
    if not data:
        return None

    rankings = []
    for race in data:
        race_details = await get_race_details(race, get_keystrokes=True)
        if "keystroke_wpm" not in race_details:
            return None
        race_details["wpm"] = race_details["unlagged"]
        rankings.append(race_details)

    raw_rankings = copy.deepcopy(rankings)
    for race in raw_rankings:
        race["wpm"] = race["raw_unlagged"]
        race["keystroke_wpm"] = race["keystroke_wpm_raw"]

    pauseless_rankings = copy.deepcopy(rankings)
    for race in pauseless_rankings:
        race["wpm"] = race["pauseless_unlagged"]
        race["keystroke_wpm"] = race["keystroke_wpm_pauseless"]

    rankings.sort(key=lambda x: x["wpm"], reverse=True)
    raw_rankings.sort(key=lambda x: x["wpm"], reverse=True)
    pauseless_rankings.sort(key=lambda x: x["wpm"], reverse=True)

    return {
        "quote": rankings[0]["quote"],
        "text_id": rankings[0]["text_id"],
        "timestamp": rankings[0]["timestamp"],
        "rankings": rankings,
        "raw_rankings": raw_rankings,
        "pauseless_rankings": pauseless_rankings,
    }


def get_universe_multiplier(universe):
    if universe == "lang_ko":
        return 24000
    elif universe in ["lang_zh", "lang_zh-tw", "new_lang_zh-tw", "lang_ja"]:
        return 60000
    return 12000
