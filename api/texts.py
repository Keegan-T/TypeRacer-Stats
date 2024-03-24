import json

import aiohttp
import requests
import urls
from bs4 import BeautifulSoup

def get_quote(text_id):
    url = f"https://data.typeracer.com/pit/text_info?id={text_id}"
    html = requests.get(url).text
    if "Text not found." in html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    quote = (soup.find("div", class_="fullTextStr").get_text().strip()
             .replace("\n", " ")
             .replace("\r", ""))

    return quote

async def get_top_10(text_id):
    url = urls.top_10(text_id)
    # data = requests.get(url).json()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json(content_type="text/html")

    await session.close()
    return data[1]

# def scrape_top_10(text_id): # async
#     url = f"https://data.typeracer.com/pit/text_info?id={text_id}"
#     html = requests.get(url).text
#     if "Text not found." in html:
#         return None
#
#     soup = BeautifulSoup(html, "html.parser")
#     quote = (soup.find("div", class_="fullTextStr").get_text().strip()
#              .replace("\n", " ")
#              .replace("\r", ""))
#
#     scores_table = soup.find("table", class_="scoresTable")
#
#     for row in scores_table.find_all("tr")[1:]:
#         columns = row.find_all("td")
#         username = columns[1].get_text()
#         wpm = columns[2].get_text()[:-4]
#         # country_div = columns[1].find("div")
#
#     return quote