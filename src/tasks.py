import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from aiohttp import ClientResponseError
from dateutil.relativedelta import relativedelta

import database.main.competition_results as competition_results
import database.main.texts as texts
import database.main.users as users
from api.competitions import get_competition
from api.core import date_to_timestamp
from api.texts import get_text
from commands.account.download import run as download
from commands.locks import import_lock
from database.main import db, text_results
from utils.logging import log


async def import_competitions():
    log("Importing competitions")
    grace_period = 21600
    latest = competition_results.get_latest_competitions()
    utc = timezone.utc
    now = datetime.now(utc)
    podium_users = set()
    get_podium = lambda comp: [user["username"] for user in comp["competitors"][:3]]

    day_end = datetime.fromtimestamp(latest["day"]["end_time"], tz=utc)
    offset = relativedelta(days=1, seconds=grace_period)
    day_check = day_end + offset
    while day_check < now:
        start = day_check - offset
        log(f"Importing new daily competition: {start}")
        competition = await get_competition(start, "day")
        competition_results.add_results(competition)
        podium_users.update(get_podium(competition))
        day_check += relativedelta(days=1)

    week_end = datetime.fromtimestamp(latest["week"]["end_time"], tz=utc)
    offset = relativedelta(weeks=1, seconds=grace_period)
    week_check = week_end + offset
    while week_check < now:
        start = week_check - offset
        log(f"Importing new weekly competition: {week_check - offset}")
        competition = await get_competition(start, "week")
        competition_results.add_results(competition)
        podium_users.update(get_podium(competition))
        week_check += relativedelta(weeks=1)

    month_end = datetime.fromtimestamp(latest["month"]["end_time"], tz=utc)
    offset = relativedelta(months=1, seconds=grace_period)
    month_check = month_end + offset
    while month_check < now:
        start = month_check - offset
        log(f"Importing new monthly competition: {month_check - offset}")
        competition = await get_competition(start, "month")
        competition_results.add_results(competition)
        podium_users.update(get_podium(competition))
        month_check += relativedelta(months=1)

    year_end = datetime.fromtimestamp(latest["year"]["end_time"], tz=utc)
    offset = relativedelta(years=1, seconds=grace_period)
    year_check = year_end + offset
    while year_check < now:
        start = year_check - offset
        log(f"Importing new yearly competition: {year_check - offset}")
        competition = await get_competition(start, "year")
        competition_results.add_results(competition)
        podium_users.update(get_podium(competition))
        year_check += relativedelta(years=1)

    log("Updating award counts")
    awards_list = await competition_results.get_awards()
    for username in podium_users:
        awards = awards_list[username]
        first = awards["day"]["first"] + awards["week"]["first"] + awards["month"]["first"] + awards["year"]["first"]
        second = awards["day"]["second"] + awards["week"]["second"] + awards["month"]["second"] + awards["year"]["second"]
        third = awards["day"]["third"] + awards["week"]["third"] + awards["month"]["third"] + awards["year"]["third"]
        users.update_awards(username, first, second, third)

    log("Finished importing competitions")


async def update_important_users():
    log(f"Updating important users")

    important_users = await users.get_important_users()
    async with import_lock:
        for username in important_users:
            await download(username)
            await asyncio.sleep(3)

    log("Finished updating important users")


async def import_top_tens():
    from api.texts import get_top_results

    text_ids = [str(text["text_id"]) for text in texts.get_texts(get_disabled=False)]
    for text_id in text_ids:
        top_10 = await get_top_results(text_id)
        results = [(
            text_id, score["user"], score["wpm"], score["wpm"],
            None, score["acc"], date_to_timestamp(score["t"]),
        ) for score in top_10]
        text_results.add_results(results)


async def update_top_tens():
    from database.main.users import get_text_bests
    from database.main.alts import get_alts

    log("Updating top tens")
    await import_top_tens()
    await text_results.import_users()
    top_10s = text_results.get_top_10s()
    user_list = set()
    for top_10 in top_10s.values():
        for score in top_10:
            user_list.add(score["username"])

    alts = get_alts()
    alt_map = {}
    for primary, group in alts.items():
        for user in group:
            alt_map[user] = primary
        alt_map[primary] = primary

    top_10s = defaultdict(list)
    banned = set(users.get_disqualified_users())
    user_list = [user for user in user_list if user not in banned]

    log("Calculating top tens")
    for username in user_list:
        text_bests = get_text_bests(username, race_stats=True)
        for race in text_bests:
            text_id = race["text_id"]
            wpm = race["wpm"]
            race = (
                text_id, username, race["number"], wpm, None,
                race["accuracy"], race["timestamp"]
            )

            if username in banned:
                continue
            if text_id not in top_10s:
                top_10s[text_id] = []

            if username in alts:
                existing_score = next((score for score in top_10s[text_id] if score[0] in alts[username]), None)
            else:
                existing_score = next((score for score in top_10s[text_id] if score[0] == username), None)

            if existing_score:
                if wpm > existing_score[3]:
                    top_10s[text_id].remove(existing_score)
                    top_10s[text_id].append(race)
                    top_10s[text_id] = sorted(top_10s[text_id], key=lambda x: x[3], reverse=True)[:10]
            else:
                top_10s[text_id].append(race)
                top_10s[text_id] = sorted(top_10s[text_id], key=lambda x: x[3], reverse=True)[:10]

    results = []
    disabled_text_ids = texts.get_disabled_text_ids()
    for text_id, top_10 in top_10s.items():
        if int(text_id) not in disabled_text_ids:
            results += top_10

    log(f"Adding {len(results):,} results")
    text_results.add_results(results)
    log(f"Finished updating top tens")


async def update_texts():
    log(f"Updating new texts")
    missing_texts = db.fetch("""
        SELECT * FROM texts
        WHERE title IS NULL
    """)

    for text in missing_texts:
        text_id = text["text_id"]
        log(f"Updating text #{text_id}")
        try:
            text_info = await get_text(text_id)
        except ClientResponseError as e:
            log(f"Exception: {e.message}")
            continue
        texts.update_text(text_info)
        await asyncio.sleep(1)

    log(f"Finished updating new texts")
