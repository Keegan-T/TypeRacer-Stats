import math
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from discord.ext import commands

import database.main.races as races
import database.main.texts as texts
import database.main.users as users
from api.users import get_stats
from commands.account.download import run as download
from database.bot.users import get_user
from utils import errors, urls, strings, dates
from utils.embeds import Message, get_pages, is_embed
from utils.stats import calculate_seconds

periods = ["races", "day", "week", "month", "year"]
sorts = ["date", "points", "races", "time", "wpm", "accuracy"]
command = {
    "name": "racehistory",
    "aliases": ["rh"],
    "description": "Displays race history for a time period and sort\n"
                   "Add `least` at the end to sort in reverse order",
    "parameters": "[username] <period> <sort>",
    "defaults": {
        "time_period": "races",
        "sort": "date",
    },
    "usages": [
        "racehistory keegant",
        "racehistory keegant day wpm",
        "racehistory keegant week points",
        "racehistory keegant month races",
        "racehistory keegant year time",
        "racehistory keegant day accuracy worst",
    ],
}


class RaceHistory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def racehistory(self, ctx, *args):
        user = get_user(ctx)
        reverse = True
        if args and args[-1] in ["worst", "least", "oldest", "old", "reverse"]:
            reverse = False
            args = args[:-1]

        result = get_args(user, args, command)
        if is_embed(result):
            return await ctx.send(embed=result)

        username, time_period, sort = result
        await run(ctx, user, username, time_period, sort, reverse)


def get_args(user, args, info):
    params = f"username period:{'|'.join(periods)} sort:{'|'.join(sorts)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, time_period, sort, reverse):
    universe = user["universe"]
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    api_stats = get_stats(username, universe=universe)
    await download(stats=api_stats, universe=universe)

    if time_period == "races":
        columns = ["number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
        race_list = await races.get_races(
            username, columns=columns, order_by="timestamp",
            limit=200, reverse=reverse, universe=universe,
            start_date=user["start_date"], end_date=user["end_date"],
        )

        def formatter(race):
            return (
                f"[#{race['number']:,}]({urls.replay(username, race['number'], universe)}) - "
                f"{race['wpm']:,.2f} WPM - {math.floor(race['accuracy'] * 100):,.0f}% - {race['points']:,.0f} pts - "
                f"{race['rank']}/{race['racers']} - <t:{int(race['timestamp'])}:R>\n"
            )

        title = "Race History"
        pages = get_pages(race_list, formatter, page_count=10, per_page=20)

    else:
        def formatter(period):
            return (
                f"**{period[1]}**\n"
                f"{period[2]:,} Races / {period[3]:,.0f} Points / "
                f"{strings.format_duration_short(period[5])}\n"
                f"{period[4]:,.2f} WPM ({period[6]:.2%} Accuracy)\n\n"
            )

        sort_title = {"wpm": "WPM"}.get(sort, sort.title())
        reverse_title = "" if reverse else ("Oldest " if sort == "date" else "Least ")
        title = f"Race History - {time_period.title()}s (By {reverse_title}{sort_title})"
        history = await get_history(username, time_period, sort, universe, user["start_date"], user["end_date"], reverse)
        pages = get_pages(history, formatter, page_count=20, per_page=5)

    message = Message(
        ctx, user, pages,
        title=title,
        profile=api_stats,
        universe=universe,
    )

    await message.send()


async def get_history(username, category, sort, universe, start_date, end_date, reverse):
    sort_key = {"points": 3, "races": 2, "time": 5, "wpm": 4, "accuracy": 6}.get(sort, 0)
    columns = ["text_id", "wpm", "points", "timestamp", "accuracy"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe, start_date=start_date, end_date=end_date
    )
    race_list.sort(key=lambda x: x[3])
    text_list = texts.get_texts(as_dictionary=True, get_disabled=True, universe=universe)
    history = []

    for race in race_list:
        text_id, wpm, points, timestamp, accuracy = race
        seconds = calculate_seconds(text_list[text_id]["quote"], wpm)

        if len(history) == 0 or timestamp > history[-1][1]:
            if category == "day":
                start = dates.floor_day(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = start.timestamp() + 86400
            elif category == "week":
                start = dates.floor_week(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = start.timestamp() + 86400 * 7
            elif category == "month":
                start = dates.floor_month(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = (start + relativedelta(months=1)).timestamp()
            else:
                start = dates.floor_year(datetime.fromtimestamp(timestamp, tz=timezone.utc))
                end = (start + relativedelta(years=1)).timestamp()

            history.append([
                start.timestamp(), end,
                1, points, wpm, seconds, accuracy
            ])

        else:
            history[-1][2] += 1
            history[-1][3] += points
            history[-1][4] += wpm
            history[-1][5] += seconds
            history[-1][6] += accuracy

    for stats in history:
        start = datetime.fromtimestamp(stats[0], tz=timezone.utc)
        end = datetime.fromtimestamp(stats[1], tz=timezone.utc)
        if category == "day":
            stats[1] = strings.get_display_date(start)
        elif category == "week":
            stats[1] = strings.get_display_date_range(start, end - relativedelta(days=1))
        elif category == "month":
            stats[1] = start.strftime("%B %Y")
        else:
            stats[1] = start.strftime("%Y")
        stats[4] = stats[4] / stats[2]
        stats[6] = stats[6] / stats[2]

    history = sorted(history, key=lambda x: x[sort_key], reverse=reverse)

    return history


async def setup(bot):
    await bot.add_cog(RaceHistory(bot))
