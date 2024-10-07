import asyncio
from datetime import datetime, timezone

import aiohttp
from dateutil.relativedelta import relativedelta

import database.competition_results as competition_results
import database.db as db
import database.important_users as important_users
import database.texts as texts
import database.users as users
from api.competitions import get_competition
from commands.basic.download import run as download
from commands.locks import import_lock
from utils import strings
from utils.logging import log


async def import_competitions():
    grace_period = 21600
    comps = competition_results.get_latest()
    utc = timezone.utc
    now = datetime.now(utc)

    day_end = datetime.fromtimestamp(comps["day"]['end_time'], tz=utc)
    offset = relativedelta(days=1, seconds=grace_period)
    day_check = day_end + offset
    while day_check < now:
        start = day_check - offset
        log(f"Importing new daily competition: {start}")
        competition = await get_competition(start, "day")
        competition_results.add_results(competition)
        day_check += relativedelta(days=1)

    week_end = datetime.fromtimestamp(comps["week"]['end_time'], tz=utc)
    offset = relativedelta(weeks=1, seconds=grace_period)
    week_check = week_end + offset
    while week_check < now:
        start = week_check - offset
        log(f"Importing new weekly competition: {week_check - offset}")
        competition = await get_competition(start, "week")
        competition_results.add_results(competition)
        week_check += relativedelta(weeks=1)

    month_end = datetime.fromtimestamp(comps["month"]['end_time'], tz=utc)
    offset = relativedelta(months=1, seconds=grace_period)
    month_check = month_end + offset
    while month_check < now:
        start = month_check - offset
        log(f"Importing new monthly competition: {month_check - offset}")
        competition = await get_competition(start, "month")
        competition_results.add_results(competition)
        month_check += relativedelta(months=1)

    year_end = datetime.fromtimestamp(comps["year"]['end_time'], tz=utc)
    offset = relativedelta(years=1, seconds=grace_period)
    year_check = year_end + offset
    while year_check < now:
        start = year_check - offset
        log(f"Importing new yearly competition: {year_check - offset}")
        competition = await get_competition(start, "year")
        competition_results.add_results(competition)
        year_check += relativedelta(years=1)

    log("Updating award counts")
    awards_list = await competition_results.get_awards()
    user_list = users.get_users()

    for user in user_list:
        username = user["username"]
        if username not in awards_list.keys():
            continue
        awards = awards_list[username]
        first = awards['day']['first'] + awards['week']['first'] + awards['month']['first'] + awards['year']['first']
        second = awards['day']['second'] + awards['week']['second'] + awards['month']['second'] + awards['year']['second']
        third = awards['day']['third'] + awards['week']['third'] + awards['month']['third'] + awards['year']['third']
        if user["awards_first"] != first or user["awards_second"] != second or user["awards_third"] != third:
            users.update_awards(username, first, second, third)

    log("Imported all new competitions")


async def update_important_users():
    user_list = important_users.get_users()
    log(f"Updating {len(user_list)} important users...")

    leaders = users.get_most("races", 10) + \
              users.get_most_daily_races(10) + \
              users.get_most("characters", 10) + \
              users.get_most("seconds", 10) + \
              users.get_most_total_points(10) + \
              users.get_most_daily_points(10) + \
              users.get_top_text_best(10) + \
              users.get_most("text_wpm_total", 10) + \
              users.get_most("texts_typed", 10) + \
              await users.get_most_text_repeats(10) + \
              users.get_most_awards(10)

    for leader in leaders:
        username = leader["username"]
        if leader["username"] not in user_list:
            log(f"Adding top 10 user {username} to daily imports")
            important_users.add_user(username)
            user_list.append(username)

    await import_lock.acquire()
    for username in user_list:
        await download(username)
    import_lock.release()


async def import_top_ten_users():
    from api.texts import get_top_10_user_stats
    from api.users import get_stats

    unique_users = {}
    text_ids = [str(text["id"]) for text in texts.get_texts(include_disabled=False)]
    partitions = [text_ids[i:i + 100] for i in range(0, len(text_ids), 100)]

    for i in range(len(partitions)):
        log(
            f"Fetching quotes #{partitions[i][0]} - #{partitions[i][-1]} "
            f"({((i + 1) / len(partitions) * 100):,.2f}%)"
        )
        async with aiohttp.ClientSession() as session:
            stats_list = await asyncio.gather(*[get_top_10_user_stats(session, text_id) for text_id in partitions[i]])
            for user_stats in stats_list:
                for stats in user_stats:
                    username = stats["id"][3:]
                    if username not in unique_users:
                        unique_users[username] = stats

    for stats in unique_users.values():
        stats = get_stats(stats=stats)
        if stats is None:
            continue
        async with import_lock:
            await download(stats=stats)


async def update_top_tens():
    import database.text_results as text_results
    from database.alts import get_alts

    await import_top_ten_users()

    alts = get_alts()
    banned = set(users.get_disqualified_users())
    top_10s = {}

    limit = 100000
    offset = 0
    race_list = 1

    while race_list:
        log("Fetching 100,000 races...")
        race_list = await db.fetch_async("""
            SELECT username, text_id, number, wpm, timestamp FROM races
            LIMIT ?, ?
        """, [offset, limit])

        for race in race_list:
            username, text_id, _, wpm, _ = race
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
        offset += limit

    results = []

    disabled_text_ids = texts.get_disabled_text_ids()
    for text_id, top_10 in top_10s.items():
        if int(text_id) in disabled_text_ids:
            continue
        for score in top_10:
            username = score["username"]
            number = score["number"]
            results.append((
                strings.race_id(username, number), score["text_id"],
                username, number, score["wpm"], score["timestamp"],
            ))

    log(f"Adding {len(results)} results")
    text_results.add_results(results)
    log("Added results")
