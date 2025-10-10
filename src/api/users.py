import json

import requests
from aiohttp import ClientResponseError

from api.core import get, date_to_timestamp


async def get_racer_data(username):
    result = await get(f"/racers/{username}")

    data = result["data"]
    if not data:
        return None

    data["joined_at"] = date_to_timestamp(data["joined_at"])

    return data


async def get_racer_stats(username, universe="play"):
    result = await get(f"/racers/{username}/stats", {
        "universe": universe,
    })

    data = result["data"]
    if not data:
        return None

    return data[0]


async def get_racer(username, universe):
    try:
        racer_data = await get_racer_data(username)
        racer_stats = await get_racer_stats(username, universe)
        if racer_stats is None:
            racer_stats = {
                "total_races": 0, "total_wins": 0, "points": 0,
                "avg_wpm": 0, "best_wpm": 0, "cert_wpm": 0, "dqd": False,
            }
    except ClientResponseError as e:
        if e.status == 404:
            return None
        else:
            raise e

    return racer_data | racer_stats


async def get_stats(username=None, stats=None, universe="play"):
    if stats:
        api_data = stats
    else:
        api_data = await get_racer_data(username)
        if not api_data:
            return None

    try:
        tstats = api_data["stats"]
        stats = dict(
            username=api_data["username"],
            universe=universe,
            display_name=api_data["name"] if api_data["name"] else "",
            country=api_data["country"],
            premium=api_data["premium"],
            races=tstats["total_races"],
            wins=tstats["total_wins"],
            points=tstats["points"],
            wpm_average=tstats["avg_wpm"],
            wpm_best=tstats["best_wpm"],
            wpm_verified=tstats["cert_wpm"],
            avatar=api_data["avatar"],
            disqualified=tstats.get("dqd", False),
        )
        return stats
    except KeyError:
        return None


async def get_joined(username):
    data = await get_racer_data(username)
    return data["joined_at"]


def get_latest_race(username, universe="play"):
    url = f"https://data.typeracer.com/games?playerId=tr:{username}&n=1&universe={universe}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    races = json.loads(response.text)

    return races[0]
