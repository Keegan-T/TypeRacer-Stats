import json
import re

import aiohttp
import requests
from bs4 import BeautifulSoup
from dateutil import parser

import api.bulk as bulk
from api.users import get_stats
from database.main import club_races
from utils import logs, urls
from utils.stats import calculate_points


async def get_races(username, start_time, end_time, races_per_page, universe="play"):
    url = urls.games(username, start_time, end_time, races_per_page, universe)
    headers = {"User-Agent": bulk.get_random_user_agent()}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            if response.status == 404:
                return []
            elif response.status != 200:
                raise ConnectionError

            data = await response.json(content_type="text/html")

    return data


async def get_race(username, race_number, get_opponents=False, universe="play", get_typos=False):
    html = await get_race_html(username, race_number, universe)

    return await get_race_details(html, get_opponents, universe, get_typos)


async def get_race_html(username, race_number, universe="play"):
    url = urls.replay(username, race_number, universe, dq=True)
    headers = {"User-Agent": bulk.get_random_user_agent()}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            html = await response.text()

    return html


async def get_race_html_bulk(urls):
    return await bulk.fetch(urls)


async def get_race_details(html, get_opponents=False, universe="play", get_typos=False):
    soup = BeautifulSoup(html, "html.parser")
    details = {}

    # Scraping race information
    username_td = soup.find("td", string="Racer")
    if not username_td:
        return None

    racer = username_td.find_next_sibling("td").find("a").get("href")
    username = racer.split("=")[1]

    number_td = soup.find("td", string="Race Number")
    race_number = int(number_td.find_next_sibling("td").get_text(strip=True))

    date_td = soup.find("td", string="Date")
    date_string = date_td.find_next_sibling('td').get_text(strip=True)
    timestamp = parser.parse(date_string).timestamp()
    details["timestamp"] = timestamp

    quote = soup.find("div", class_="fullTextStr").get_text(strip=True)
    text_link = soup.find('a', href=lambda x: x and 'text_info?id=' in x)
    text_id = text_link['href'].split('=')[1]
    details["quote"] = quote
    details["text_id"] = text_id

    # Scraping accuracy for higher precision
    accuracy_td = soup.find("td", string="Accuracy")
    accuracy_string = accuracy_td.find_next_sibling("td").get_text(strip=True)
    try:
        accuracy = float(accuracy_string[:-1]) / 100
    except ValueError:
        accuracy = 0
    details["accuracy"] = accuracy

    # Getting details from API
    race = find_race(username, race_number, timestamp, universe)
    if not race:
        return None
    lagged = race["wpm"]

    details["lagged"] = lagged
    details["rank"] = race["r"]
    details["racers"] = race["np"]
    if race["pts"] == 0:
        race["pts"] = calculate_points(quote, lagged)
    details["points"] = race["pts"]

    # Getting log details
    log_script = soup.find('script', text=lambda x: x and 'var typingLog =' in x)
    try:
        typing_log = str(log_script).rsplit('var typingLog = "', 1)[1].rsplit('"', 1)[0]
    except IndexError:
        return details

    multiplier = get_universe_multiplier(universe)
    log_details = logs.get_log_details(typing_log, multiplier, get_typos)
    for key, value in log_details.items():
        details[key] = value

    lagged = details["lagged"]
    lagged_ms = multiplier * len(details["quote"]) / lagged if lagged > 0 else 0
    ping = round(lagged_ms) - details['duration']
    lag = details['unlagged'] - lagged
    details["ping"] = ping
    details["lag"] = lag

    # Adding new 300 WPM races
    if universe == "play" and 300 <= details["adjusted"] <= 450:
        stats = get_stats(username)
        if not stats["disqualified"]:
            club_races.add_race(username, race_number, details)

    delays = log_details["delays"]
    details["keystroke_wpm"] = logs.get_keystroke_wpm(delays, multiplier)
    details["keystroke_wpm_adjusted"] = logs.get_keystroke_wpm(delays, multiplier, adjusted=True)

    if log_details.get("raw_unlagged", None):
        raw_delays = log_details["raw_delays"]
        details["keystroke_wpm_raw"] = logs.get_keystroke_wpm(raw_delays, multiplier)
        details["keystroke_wpm_raw_adjusted"] = logs.get_keystroke_wpm(raw_delays, multiplier, adjusted=True)

        pauseless_delays = log_details["pauseless_delays"]
        details["keystroke_wpm_pauseless"] = logs.get_keystroke_wpm(pauseless_delays, multiplier)
        details["keystroke_wpm_pauseless_adjusted"] = logs.get_keystroke_wpm(pauseless_delays, multiplier, adjusted=True)

    # Getting opponent information
    if get_opponents:
        opponents_td = soup.find("td", string="Opponents")
        if opponents_td:
            opponents = {}
            opponents_string = opponents_td.find_next_sibling("td")
            for a in opponents_string.find_all("a"):
                opponents[a.text] = (int(a.get("href").split("|")[-1]),)

            for opponent in opponents_string.get_text(strip=True).split(")")[:-1]:
                username, rank_string = opponent.split("(")
                rank = int(re.findall(r"\d+", rank_string)[0])
                opponents[username] += (rank,)

            opponents = sorted(list(opponents.items()), key=lambda x: x[1][1])
            opponents = [(opp[0], opp[1][1], opp[1][0]) for opp in opponents]

            details["opponents"] = opponents

    return details


def find_race(username, race_number, timestamp, universe="play"):
    url = urls.games(username, timestamp - 5, timestamp + 5, 20, universe)
    response = requests.get(url)
    races = json.loads(response.text)
    return next((race for race in races if race["gn"] == race_number), None)


async def get_match(username, race_number, universe="play"):
    match = await get_race(username, race_number, get_opponents=True, universe=universe)

    if not match or isinstance(match, int) or "unlagged" not in match:
        return None

    user = {
        "username": username,
        "race_number": race_number,
        "wpm": match["unlagged"],
        "accuracy": match["accuracy"],
        "start": match["start"],
        "keystroke_wpm": match["keystroke_wpm"],
    }
    rankings = [user]
    raw_rankings = [{
        **user,
        "wpm": match["raw_unlagged"],
        "keystroke_wpm": match["keystroke_wpm_raw"],
        "correction_percent": match["correction_percent"],
        "pause_percent": match["pause_percent"],
    }]
    pauseless_rankings = [{
        **user,
        "wpm": match["pauseless_unlagged"],
        "keystroke_wpm": match["keystroke_wpm_pauseless"],
        "correction_percent": match["correction_percent"],
        "pause_percent": match["pause_percent"],
    }]

    if "opponents" in match:
        for opponent in match["opponents"][:9]:
            opp_username = opponent[0]
            opp_race_number = opponent[2]
            opp_race_info = await get_race(opp_username, opp_race_number, universe=universe)
            if not opp_race_info or isinstance(opp_race_info, int):
                continue
            user = {
                "username": opp_username,
                "race_number": opp_race_number,
                "wpm": opp_race_info["unlagged"],
                "accuracy": opp_race_info["accuracy"],
                "start": opp_race_info["start"],
                "keystroke_wpm": opp_race_info["keystroke_wpm"],
            }
            rankings.append(user)
            raw_rankings.append({
                **user,
                "wpm": opp_race_info["raw_unlagged"],
                "keystroke_wpm": opp_race_info["keystroke_wpm_raw"],
                "correction_percent": opp_race_info["correction_percent"],
                "pause_percent": opp_race_info["pause_percent"],
            })
            pauseless_rankings.append({
                **user,
                "wpm": opp_race_info["pauseless_unlagged"],
                "keystroke_wpm": opp_race_info["keystroke_wpm_pauseless"],
                "correction_percent": opp_race_info["correction_percent"],
                "pause_percent": opp_race_info["pause_percent"],
            })

    rankings.sort(key=lambda x: x["wpm"], reverse=True)
    raw_rankings.sort(key=lambda x: x["wpm"], reverse=True)

    return {
        "quote": match["quote"],
        "text_id": match["text_id"],
        "timestamp": match["timestamp"],
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
