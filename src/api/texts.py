import aiohttp
import requests
from bs4 import BeautifulSoup

from api.bulk import get_random_user_agent
from utils import urls


def get_quote(text_id):
    url = urls.text_info(text_id)
    html = requests.get(url).text
    if "Text not found." in html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    quote = (soup.find("div", class_="fullTextStr").get_text().strip()
             .replace("\n", " ")
             .replace("\r", ""))

    return quote


async def get_top_10(text_id, universe="play"):
    url = urls.top_10(text_id, universe)
    headers = {"User-Agent": get_random_user_agent()}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            data = await response.json(content_type="text/html")

    await session.close()
    return data[1]


async def get_top_10_user_stats(session, text_id):
    url = urls.top_10(text_id)
    user_stats = []
    async with session.get(url) as response:
        try:
            top_10 = await response.json(content_type="text/html")
            for score in top_10[1]:
                user_stats.append(score[1])
            return user_stats
        except:
            return []


def get_text_list(universe):
    url = urls.trdata_text_list(universe)
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    text_list = []

    table = soup.find("table", class_="stats")
    rows = table.find_all("tr")[1:]
    for i, row in enumerate(rows):
        print(f"Getting text {i:,} of {len(rows):,}")
        columns = row.find_all("td")
        text_id = int(columns[0].get_text()[1:])
        quote = columns[1].get_text().strip()
        if columns[6].get_text() == "0.00":
            username, race_number = get_ghost(text_id, universe)
        else:
            link = columns[5].find("a")["href"].split("=")
            username = link[1].split("&")[0]
            race_number = link[2].split("&")[0]

        text_list.append({
            "text_id": text_id,
            "quote": quote,
            "ghost_username": username,
            "ghost_number": race_number,
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
