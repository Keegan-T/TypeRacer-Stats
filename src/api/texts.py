import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from api.core import get
from utils import urls, strings
from utils.logging import log


async def get_text(text_id):
    result = await get(f"/texts/{text_id}")
    data = result["data"]
    if not data:
        return None

    data["text"] = strings.strip_quote(data["text"])
    return data


async def get_top_results(text_id):
    result = await get(f"/texts/{text_id}/top")
    data = result["data"]
    if not data:
        return None
    return data


def get_trdata_top_10(text_id, universe):
    url = f"https://typeracerdata.com/text?id={text_id}&universe={universe}"
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="profile")
    rows = table.find_all("tr")[1:]
    top_10 = []

    for row in rows[:10]:
        columns = row.find_all("td")
        try:
            accuracy = float(columns[3].text.strip("%")) / 100
        except (ValueError, IndexError):
            accuracy = 0.0
        top_10.append({
            "username": re.search(r"username=([^&\"]+)", str(columns[1])).group(1),
            "number": int(re.search(r"game=(\d+)", str(columns[2])).group(1)),
            "wpm": float(columns[2].text.replace(",", "")),
            "accuracy": accuracy,
            "timestamp": datetime.strptime(columns[4].text, "%Y-%m-%d").timestamp(),
        })

    return top_10


def get_text_list(universe):
    url = urls.trdata_text_list(universe)
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    text_list = []

    table = soup.find("table", class_="stats")
    rows = table.find_all("tr")[1:]
    log(f"Fetching {len(rows):,} new texts")
    for i, row in enumerate(rows):
        columns = row.find_all("td")
        text_list.append({
            "text_id": int(columns[0].get_text()[1:]),
            "quote": columns[1].get_text().strip(),
        })

    return text_list


def get_ghost(text_id, universe):
    url = urls.trdata_text(text_id, universe)
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", class_="profile")
    rows = table.find_all("tr")
    columns = rows[1].find_all("td")
    link = columns[2].find("a")["href"].split("=")
    username = link[1].split("&")[0]
    race_number = link[2].split("&")[0]

    return username, race_number
