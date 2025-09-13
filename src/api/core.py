import asyncio
import base64
import csv
from datetime import datetime, timezone
from io import StringIO

import aiohttp

from api.bulk import get_random_user_agent
from config import api_credentials

base_url = "https://data.typeracer.com/api/v1"
session = None
auth_index = 0
index_lock = asyncio.Lock()


def auth_header(creds):
    token = base64.b64encode(creds.encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "User-Agent": get_random_user_agent(),
    }


async def cycle_auth():
    global auth_index
    async with index_lock:
        creds = api_credentials[auth_index]
        auth_index = (auth_index + 1) % len(api_credentials)
    return auth_header(creds)


async def start_session():
    global session
    session = aiohttp.ClientSession()


async def end_session():
    global session
    await session.close()


def date_to_timestamp(date):
    return datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f").timestamp()


def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


async def get(endpoint, params=None):
    url = base_url + endpoint
    headers = await cycle_auth()
    async with session.get(url, params=params, headers=headers) as response:
        response.raise_for_status()
        return await response.json()


async def get_csv(endpoint, params=None):
    url = base_url + endpoint
    headers = await cycle_auth() | {"Accept": "text/csv"}
    async with session.get(url, headers=headers, params=params) as response:
        response.raise_for_status()
        text = await response.text(encoding="utf-8", errors="replace")
        return csv_to_dict(text)


def csv_to_dict(text):
    race_list = []
    reader = csv.DictReader(StringIO(text))
    rows = list(reader)
    for row in rows:
        if float(row["WPM"]) == 0.0:
            continue
        race_list.append({
            "univ": row["Universe"],
            "rid": row["Race ID"],
            "tid": int(row["Text ID"]),
            "sl": row["Skill Level"],
            "t": date_to_timestamp(row["Date/Time (UTC)"]),
            "acc": 0.0 if row["Accuracy"] == "None" else float(row["Accuracy"]),
            "wpm": float(row["WPM"]),
            "pts": float(row["Points"]),
            "rn": int(row["Race #"]),
            "nr": int(row["# Racers"]),
            "r": int(row["Rank"]),
            "kl": row["Keylog"],
        })

    return race_list
