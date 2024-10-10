import json
import urllib.parse

import aiohttp
import requests
from bs4 import BeautifulSoup
from dateutil import parser

from api.bulk import get_random_user_agent
from utils import dates, urls


def get_stats(username=None, stats=None, universe="play"):
    if stats:
        api_data = stats
    else:
        username = urllib.parse.quote(username).lower()
        url = urls.stats(username, universe)
        response = requests.get(url)

        if response.status_code == 500:
            return None
        elif response.status_code != 200:
            raise ConnectionError

        api_data = json.loads(response.text)

    tstats = api_data["tstats"]

    display_name = api_data["name"] if api_data["name"] else ""
    disqualified = False if "disqualified" not in tstats else tstats["disqualified"]

    try:
        stats = {
            "username": api_data["id"][3:],
            "display_name": display_name,
            "country": api_data["country"],
            "premium": api_data["premium"],
            "races": tstats["cg"],
            "wins": tstats["gamesWon"],
            "points": tstats["points"],
            "wpm_average": tstats["wpm"],
            "wpm_last_10": tstats["recentAvgWpm"],
            "wpm_best": tstats["bestGameWpm"],
            "wpm_verified": tstats["certWpm"],
            "has_pic": api_data["hasPic"],
            "avatar": api_data["avatar"],
            "disqualified": disqualified,
        }
        return stats

    except KeyError:
        return None


async def get_joined(username):
    url = urls.profile(username)
    headers = {"User-Agent": get_random_user_agent()}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    join_date_span = soup.find("span", string="Racing Since:")
    if not join_date_span:
        return None
    join_date_text = join_date_span.find_next_sibling("span").get_text(strip=True)
    join_date = dates.floor_day(parser.parse(join_date_text))
    join_timestamp = join_date.timestamp()

    return join_timestamp


def get_latest_race(username, universe="play"):
    url = f"https://data.typeracer.com/games?playerId=tr:{username}&n=1&universe={universe}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    races = json.loads(response.text)

    return races[0]
