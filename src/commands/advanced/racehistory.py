import math
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands

import database.races as races
import database.texts as texts
import database.users as users
from api.users import get_stats
from commands.basic.download import run as download
from database.bot_users import get_user
from utils import errors, urls, strings, dates, embeds
from utils.stats import calculate_seconds

periods = ["races", "day", "week", "month", "year"]
sorts = ["date", "points", "races", "time", "wpm"]
command = {
    "name": "racehistory",
    "aliases": ["rh"],
    "description": "Displays race history for a time period and sort",
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
    ],
}


class RaceHistory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def racehistory(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, time_period, sort = result
        await run(ctx, user, username, time_period, sort)


def get_args(user, args, info):
    params = f"username period:{'|'.join(periods)} sort:{'|'.join(sorts)}"

    return strings.parse_command(user, params, args, info)


async def run(ctx, user, username, time_period, sort):
    universe = user["universe"]
    db_stats = users.get_user(username, universe)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username, universe))
    era_string = strings.get_era_string(user)

    api_stats = get_stats(username, universe=universe)
    await download(stats=api_stats, universe=universe)
    if era_string:
        api_stats = await users.time_travel_stats(api_stats, user)

    if time_period == "races":
        columns = ["number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
        race_list = await races.get_races(
            username, columns=columns, order_by="timestamp",
            limit=20, reverse=True, universe=universe,
            start_date=user["start_date"], end_date=user["end_date"]
        )

        title = "Race History"
        description = ""
        for race in race_list:
            description += (
                f"[#{race['number']:,}]({urls.replay(username, race['number'], universe)}) - "
                f"{race['wpm']:,.2f} WPM - {math.floor(race['accuracy'] * 100):,.0f}% - {race['points']:,.0f} pts - "
                f"{race['rank']}/{race['racers']} - <t:{int(race['timestamp'])}:R>\n"
            )

    else:
        sort_title = sort.title()
        if sort_title == "Wpm":
            sort_title = "WPM"
        title = f"Race History - {time_period.title()}s (By {sort_title})"
        description = ""
        history = await get_history(username, time_period, sort, universe, user["start_date"], user["end_date"])
        for period in history[:10]:
            description += (
                f"**{period[1]}**\n{period[3]:,.0f} pts / {period[2]:,} races - "
                f"{period[4]:,.2f} WPM - {strings.format_duration_short(period[5])}\n\n"
            )

    embed = Embed(
        title=title,
        description=description,
        color=user["colors"]["embed"],
    )
    embeds.add_profile(embed, api_stats, universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed, content=era_string)


async def get_history(username, category, sort, universe, start_date, end_date):
    sort_key = {"points": 3, "races": 2, "time": 5, "wpm": 4}.get(sort, 0)
    columns = ["text_id", "wpm", "points", "timestamp"]
    race_list = await races.get_races(
        username, columns=columns, universe=universe, start_date=start_date, end_date=end_date
    )
    race_list.sort(key=lambda x: x[3])
    text_list = texts.get_texts(as_dictionary=True, include_disabled=True, universe=universe)
    history = []

    for race in race_list:
        text_id, wpm, points, timestamp = race
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
                1, points, wpm, seconds,
            ])

        else:
            history[-1][2] += 1
            history[-1][3] += points
            history[-1][4] += wpm
            history[-1][5] += seconds

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

    history = sorted(history, key=lambda x: x[sort_key], reverse=True)

    return history


async def setup(bot):
    await bot.add_cog(RaceHistory(bot))
