import requests
from bs4 import BeautifulSoup

def get_universe_list():
    url = "https://typeracerdata.com/universes"

    html = requests.get(url).text

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", class_="stats").find("table", class_="stats")
    universes = []

    for row in table.find_all("tr")[1:]:
        universe = row.find_all("td")[0].text
        universes.append(universe)

    return universes