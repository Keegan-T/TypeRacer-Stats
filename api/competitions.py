import aiohttp
from datetime import timezone
from bs4 import BeautifulSoup
from dateutil import parser
from dateutil.relativedelta import relativedelta
import re


async def get_competition_info(date, kind, sort="points", results_per_page=20, universe="play"):
    sort_names = {
        "races": "gamesFinished",
        "points": "points",
        "wpm": "wpm",
        "fastest": "bestGameWpm",
        "accuracy": "accuracy",
    }
    sort = sort_names[sort]

    date_string = date.strftime('%Y-%m-%d')
    url = (f"https://data.typeracer.com/pit/competitions?date={date_string}&sort={sort}"
           f"&kind={kind}&n={results_per_page}&universe={universe}")
    async with aiohttp.ClientSession() as session:
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

        username = columns[1].find('a').text.strip()
        races = int(columns[6].text.strip().replace(',', ''))
        points = int(columns[2].text.strip().replace(',', ''))
        accuracy = round(float(columns[5].text.strip().replace('%', '')) / 100, 3)
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

    end_span = soup.find("span", style="font-weight: bold;")
    end_string = end_span.get_text(strip=True)
    end_string = " ".join(end_string.split(" ")[:3])
    end_timestamp = parser.parse(end_string).replace(tzinfo=timezone.utc).timestamp()

    return {
        "competitors": competitors,
        "end_timestamp": end_timestamp,
    }


async def get_competition(date, kind):
    duration = relativedelta(days=1)
    if kind == "week":
        duration = relativedelta(weeks=1)
    elif kind == "month":
        duration = relativedelta(months=1)
    elif kind == "year":
        duration = relativedelta(years=1)

    point_competition = await get_competition_info(date, kind, "points", 100)
    point_leaders = point_competition["competitors"]
    race_competition = await get_competition_info(date, kind, "races", 100)
    race_leaders = race_competition["competitors"]
    competitors_dict = {}

    for racer in point_leaders:
        competitors_dict[racer['username']] = racer

    for racer in race_leaders:
        competitors_dict[racer['username']] = racer

    competitors = list(competitors_dict.values())

    start_time = date.timestamp()
    end_time = (date + duration).timestamp()

    return {
        "id": f"{kind[0].upper()}{date.strftime('%Y-%m-%d')}",
        "competitors": competitors,
        "type": kind,
        "start_time": start_time,
        "end_time": end_time,
    }
