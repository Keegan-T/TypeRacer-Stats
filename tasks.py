import database.competition_results as competition_results
import database.users as users
from api.competitions import get_competition
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import database.important_users as important_users
import database.texts as texts


async def import_competitions():
    grace_period = 21600  # Seconds to wait before caching a competition
    comps = competition_results.get_latest()
    utc = timezone.utc
    now = datetime.now(utc)

    day_end = datetime.fromtimestamp(comps["day"]['end_time'], tz=utc)
    offset = relativedelta(days=1, seconds=grace_period)
    day_check = day_end + offset
    while day_check < now:
        start = day_check - offset
        print(f"Importing new daily competition: {start}")
        competition = get_competition(start, "day")
        competition_results.add_results(competition)
        day_check += relativedelta(days=1)

    week_end = datetime.fromtimestamp(comps["week"]['end_time'], tz=utc)
    offset = relativedelta(weeks=1, seconds=grace_period)
    week_check = week_end + offset
    while week_check < now:
        start = week_check - offset
        print(f"Importing new weekly competition: {week_check - offset}")
        competition = get_competition(start, "week")
        competition_results.add_results(competition)
        week_check += relativedelta(weeks=1)

    month_end = datetime.fromtimestamp(comps["month"]['end_time'], tz=utc)
    offset = relativedelta(months=1, seconds=grace_period)
    month_check = month_end + offset
    while month_check < now:
        start = month_check - offset
        print(f"Importing new monthly competition: {month_check - offset}")
        competition = get_competition(start, "month")
        competition_results.add_results(competition)
        month_check += relativedelta(months=1)

    year_end = datetime.fromtimestamp(comps["year"]['end_time'], tz=utc)
    offset = relativedelta(years=1, seconds=grace_period)
    year_check = year_end + offset
    while year_check < now:
        start = year_check - offset
        print(f"Importing new yearly competition: {year_check - offset}")
        competition = get_competition(start, "year")
        competition_results.add_results(competition)
        year_check += relativedelta(years=1)

    print("Updating award counts")
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
            print(f"Updating awards for {username}...")
            users.update_awards(username, first, second, third)

    print("Imported all new competitions")

async def update_important_users():
    from commands.basic.download import run as download
    from commands.locks import import_lock

    user_list = important_users.get_users()
    print(f"Updating {len(user_list)} important users...")

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
            print(f"Adding top 10 user {username} to daily imports")
            important_users.add_user(username)
            user_list.append(username)

    await import_lock.acquire()
    for username in user_list:
        await download(username)
    await import_lock.release()


async def update_top_tens():
    from database.text_results import update_results

    print("Updating top tens...")
    text_ids = [text["id"] for text in texts.get_texts(include_disabled=False)]

    for i, text_id in enumerate(text_ids):
        print(f"Updating text #{text_id} ({i + 1:,}/{len(text_ids):,})")
        await update_results(text_id)

    print("Finished updating top tens")