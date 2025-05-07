from datetime import datetime, timedelta, timezone

from dateutil import parser
from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands

import database.races as races
import database.users as users
from api.competitions import get_competition_info
from api.users import get_stats
from commands.advanced.races import add_stats
from commands.account.download import run as download
from config import prefix
from database.bot_users import get_user
from utils import errors, strings, dates, embeds

command = {
    "name": "day",
    "aliases": ["d", "miniday", "md", "yesterday", "yd", "miniyesterday", "myd"],
    "description": "Displays a user's stats for a given day\n"
                   f"`{prefix}yesterday [username]` shows stats for the previous day\n"
                   f"`{prefix}miniday [username]` will only show basic stats",
    "parameters": "[username] <date>",
    "defaults": {
        "date": "today"
    },
    "usages": ["day keegant 2021-01-01"],
    "temporal": False,
}


class Day(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def day(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if embeds.is_embed(result):
            return await ctx.send(embed=result)

        username, date = result
        await run(ctx, user, username, date)


def get_args(user, args, info):
    params = "username date"

    result = strings.parse_command(user, params, args, info)
    if embeds.is_embed(result):
        return result

    username, date = result

    # Shorthand (-day 1/1/24)
    if user["username"] and ("/" in username or "-" in username):
        try:
            date = parser.parse(username)
            username = user["username"]
        except ValueError:
            pass

    return username, date


async def run(ctx, user, username, date):
    universe = user["universe"]
    stats = users.get_user(username, universe)
    if not stats:
        return await ctx.send(embed=errors.import_required(username, universe))

    if not date:
        date = datetime.now(timezone.utc)

    api_stats = get_stats(username, universe=universe)
    await download(stats=api_stats, universe=universe)

    command_name = strings.get_category([
        "day", "yesterday", "miniday", "miniyesterday",
        "week", "lastweek", "miniweek",
        "month", "lastmonth", "minimonth",
        "year", "lastyear", "miniyear",
    ], ctx.invoked_with.lower())

    mini = command_name.startswith("mini")
    previous = command_name.startswith("last") or "yester" in command_name
    period = "day"
    if "week" in command_name:
        period = "week"
    elif "month" in command_name:
        period = "month"
    elif "year" in command_name:
        period = "year"

    if period == "week":
        if previous:
            date -= relativedelta(weeks=1)
        start_date = dates.floor_week(date)
        end_date = start_date + relativedelta(weeks=1)
        date_string = strings.get_display_date_range(start_date, (end_date - relativedelta(days=1)))
        title = f"Weekly Stats - {date_string}"

    elif period == "month":
        if previous:
            date -= relativedelta(months=1)
        start_date = dates.floor_month(date)
        end_date = start_date + relativedelta(months=1)
        date_string = date.strftime("%B %Y")
        title = f"Monthly Stats - {date_string}"

    elif period == "year":
        if previous:
            date -= relativedelta(years=1)
        start_date = dates.floor_year(date)
        end_date = start_date + relativedelta(years=1)
        date_string = date.year
        title = f"Yearly Stats - {date_string}"

    else:
        if previous:
            date -= timedelta(days=1)
        start_date = dates.floor_day(date)
        end_date = start_date + relativedelta(days=1)
        title = f"Daily Stats - {strings.get_display_date(date)}"

    competition = await get_competition_info(date, period, results_per_page=1, universe=universe)
    start_time = start_date.timestamp()
    end_time = end_date.timestamp()

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(username, columns, start_time, end_time, universe=universe)
    race_list.sort(key=lambda x: x[7])

    embed = Embed(title=title, color=user["colors"]["embed"])
    embeds.add_profile(embed, api_stats, universe)

    if not race_list:
        embed.description = "No races completed"
        embeds.add_universe(embed, universe)
        return await ctx.send(embed=embed)

    if competition and competition["competitors"][0]["username"] == username:
        if competition["end_timestamp"] > datetime.now(timezone.utc).timestamp():
            embed.description = f":crown: **Competition Leader** :crown:"
        else:
            embed.description = f":first_place: **Competition Winner** :first_place:"

    add_stats(embed, username, race_list, start_time, end_time, mini=mini, universe=universe)
    embeds.add_universe(embed, universe)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Day(bot))
