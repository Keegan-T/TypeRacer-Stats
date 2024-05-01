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
    async with aiohttp.ClientSession() as session:
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