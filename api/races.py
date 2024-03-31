import aiohttp
import requests
import json
import re
from bs4 import BeautifulSoup
import utils
from dateutil import parser

async def get_races(username, start_date, end_date, races_per_page):
    url = f"https://data.typeracer.com/games?playerId=tr:{username}&startDate={start_date}&endDate={end_date}&n={races_per_page}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 404:
                return []
            elif response.status != 200:
                return -1

            data = await response.json(content_type="text/html")

    return data

async def get_race_info(username, race_number, get_lagged=True, get_raw=False, get_opponents=False, universe="play"):
    url = f"https://data.typeracer.com/pit/result?id={universe}|tr:{username}|{race_number}&allowDisqualified=true"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            status_code = response.status
            if status_code != 200:
                print(f"Failed to fetch race {username}|{race_number}. Status: {status_code}")
                return status_code
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    details = {}

    # Scraping race information
    date_td = soup.find("td", string="Date")
    if not date_td:
        return None

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
    accuracy = float(accuracy_string[:-1]) / 100
    details["accuracy"] = accuracy

    # Getting details from API
    if get_lagged:
        race = get_race(username, race_number, timestamp, universe)
        if not race:
            return None
        lagged = race["wpm"]

        details["lagged"] = lagged
        details["rank"] = race["r"]
        details["racers"] = race["np"]
        if race["pts"] == 0:
            race["pts"] = utils.calculate_points(quote, lagged)
        details["points"] = race["pts"]

    # Getting log details
    log_script = soup.find('script', text=lambda x: x and 'var typingLog =' in x)
    try:
        typing_log = str(log_script).rsplit('var typingLog = "', 1)[1].rsplit('"', 1)[0]
    except IndexError:
        return details

    universe_multiplier = utils.get_universe_multiplier(universe)
    delay_data = ",".join(typing_log.split("|")[0].split(",")[3:])
    log_details = utils.get_log_details(delay_data, universe_multiplier)
    for key, value in log_details.items():
        details[key] = value

    lagged = details["lagged"]
    lagged_ms = universe_multiplier * len(details["quote"]) / lagged if lagged > 0 else 0
    ping = round(lagged_ms) - details['ms']
    lag = details['unlagged'] - lagged

    details["ping"] = ping
    details["lag"] = lag

    delays = log_details["delays"]

    wpm_over_keystrokes = utils.get_wpm_over_keystrokes(delays)
    wpm_adjusted_over_keystrokes, instant_chars = utils.get_adjusted_wpm_over_keystrokes(delays)

    details["wpm_over_keystrokes"] = wpm_over_keystrokes
    details["wpm_adjusted_over_keystrokes"] = wpm_adjusted_over_keystrokes
    details["instant_chars"] = instant_chars

    # Calculating raw speeds
    if get_raw:
        raw_speeds = utils.get_raw_speeds(typing_log)
        duration = raw_speeds["duration"]
        raw_duration = raw_speeds["raw_duration"]
        correction = duration - raw_duration
        raw_unlagged = universe_multiplier * len(delays) / raw_duration
        raw_adjusted = universe_multiplier * (len(delays) - 1) / (raw_duration - raw_speeds["raw_start"])
        details["correction"] = correction
        details["raw_unlagged"] = raw_unlagged
        details["raw_adjusted"] = raw_adjusted
        raw_delays = raw_speeds["delays"]

        raw_wpm_over_keystrokes = utils.get_wpm_over_keystrokes(raw_delays)
        raw_wpm_adjusted_over_keystrokes, instant_chars = utils.get_adjusted_wpm_over_keystrokes(raw_delays)

        details["raw_wpm_over_keystrokes"] = raw_wpm_over_keystrokes
        details["raw_wpm_adjusted_over_keystrokes"] = raw_wpm_adjusted_over_keystrokes
        details["instant_chars"] = instant_chars

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

def get_race(username, race_number, timestamp, universe="play"):
    url = (f"https://data.typeracer.com/games?playerId=tr:{username}"
           f"&n=20&startDate={timestamp - 5}&endDate={timestamp + 5}&universe={universe}")
    response = requests.get(url)
    races = json.loads(response.text)
    for race in races:
        if race["gn"] == race_number:
            return race
    return None

async def get_match(username, race_number, universe="play"):
    match = await get_race_info(username, race_number, get_opponents=True, universe=universe)

    if not match or "unlagged" not in match:
        return None

    rankings = [{
        "username": username,
        "race_number": race_number,
        "wpm": match["unlagged"],
        "accuracy": match["accuracy"],
        "start": match["start"],
        "average_wpm": match["wpm_over_keystrokes"],
    }]

    if "opponents" in match:
        for opponent in match["opponents"][:9]:
            opp_username = opponent[0]
            opp_race_number = opponent[2]
            opp_race_info = await get_race_info(opp_username, opp_race_number, universe=universe)
            rankings.append({
                "username": opp_username,
                "race_number": opp_race_number,
                "wpm": opp_race_info["unlagged"],
                "accuracy": opp_race_info["accuracy"],
                "start": opp_race_info["start"],
                "average_wpm": opp_race_info["wpm_over_keystrokes"],
            })

    rankings = sorted(rankings, key=lambda x: x["wpm"], reverse=True)

    return {
        "quote": match["quote"],
        "text_id": match["text_id"],
        "timestamp": match["timestamp"],
        "rankings": rankings,
    }