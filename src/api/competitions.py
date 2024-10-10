import re

import aiohttp
from bs4 import BeautifulSoup

from api.bulk import get_random_user_agent
from utils import urls, dates


async def get_competition_info(date, period, sort="points", results_per_page=20, universe="play"):
    url = urls.competition(date, period, sort, results_per_page, universe)
    headers = {"User-Agent": get_random_user_agent()}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            html = await response.text()

    if "No results" in html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="scoresTable")

    competitors = []
    for row in table.find_all("tr")[1:]:
        columns = row.find_all("td")
        country = None
        country_div = columns[1].find("div")
        if country_div:
            country = re.search(r"flag-squared flag-(\w+)", str(country_div)).group(1)

        username = columns[1].find("a").text.strip()
        races = int(columns[6].text.strip().replace(",", ""))
        points = int(columns[2].text.strip().replace(",", ""))
        accuracy = round(float(columns[5].text.strip().replace("%", "")) / 100, 3)
        best_wpm = float(columns[4].text.strip().split()[0])
        average_wpm = float(columns[3].text.strip().split()[0])

        user_data = {
            "username": username,
            "country": country,
            "races": races,
            "points": points,
            "accuracy": accuracy,
            "best_wpm": best_wpm,
            "average_wpm": average_wpm
        }

        competitors.append(user_data)

    end = dates.get_start_end(date, period)[1]

    return {
        "competitors": competitors,
        "end_timestamp": end.timestamp(),
    }


async def get_competition(date, period):
    point_competition = await get_competition_info(date, period, "points", 100)
    race_competition = await get_competition_info(date, period, "races", 100)
    point_leaders = point_competition["competitors"]
    race_leaders = race_competition["competitors"]

    competitors_dict = {}
    for racer in point_leaders + race_leaders:
        competitors_dict[racer["username"]] = racer

    competitors = list(competitors_dict.values())
    start, end = dates.get_start_end(date, period)
    competition_id = f"{period[0].upper()}{start.strftime('%Y-%m-%d')}"

    return {
        "id": competition_id,
        "competitors": competitors,
        "type": period,
        "start_time": start.timestamp(),
        "end_time": end.timestamp(),
    }
