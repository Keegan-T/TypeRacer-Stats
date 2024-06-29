from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands
import utils
import errors
from config import prefix
import database.races as races
import database.users as users
from dateutil import parser
from datetime import datetime, timedelta, timezone
from api.users import get_stats
from api.competitions import get_competition_info
from database.bot_users import get_user
from commands.advanced.races import add_stats
from commands.basic.download import run as download

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
}


class Day(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=command["aliases"])
    async def day(self, ctx, *args):
        user = get_user(ctx)

        result = get_args(user, args, command)
        if utils.is_embed(result):
            return await ctx.send(embed=result)

        username, date = result
        await run(ctx, user, username, date)


def get_args(user, args, info):
    params = "username date"

    result = utils.parse_command(user, params, args, info)
    if utils.is_embed(result):
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
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    if not date:
        date = datetime.now(timezone.utc)

    api_stats = get_stats(username)
    await download(stats=api_stats)

    week_commands = ["week", "w", "lastweek", "yesterweek", "lw", "yw", "miniweek", "mw"]
    month_commands = ["month", "m", "lastmonth", "yestermonth", "lm", "ym", "minimonth", "mm"]
    year_commands = ["year", "y", "lastyear", "yesteryear", "ly", "yy", "miniyear", "my"]
    command_name = ctx.invoked_with.lower()

    if command_name in week_commands:
        if command_name in week_commands[2:6]:
            date -= relativedelta(days=7)
        competition = await get_competition_info(date, "week", results_per_page=1)
        start_date = utils.floor_week(date)
        end_date = start_date + relativedelta(days=7)
        start_time = start_date.timestamp()
        end_time = end_date.timestamp()
        date_string = utils.get_display_date_range(start_date, (end_date - relativedelta(days=1)))
        title = f"Weekly Stats - {date_string}"

    elif command_name in month_commands:
        if command_name in month_commands[2:6]:
            date -= relativedelta(months=1)
        competition = await get_competition_info(date, "month", results_per_page=1)
        start_date = utils.floor_month(date)
        end_date = start_date + relativedelta(months=1)
        start_time = start_date.timestamp()
        end_time = end_date.timestamp()
        date_string = date.strftime("%B %Y")
        title = f"Monthly Stats - {date_string}"

    elif command_name in year_commands:
        if command_name in year_commands[2:6]:
            date -= relativedelta(years=1)
        competition = await get_competition_info(date, "year", results_per_page=1)
        start_date = utils.floor_year(date)
        end_date = start_date + relativedelta(years=1)
        start_time = start_date.timestamp()
        end_time = end_date.timestamp()
        date_string = date.year
        title = f"Yearly Stats - {date_string}"

    else:
        if command_name in command["aliases"][3:]:
            date -= timedelta(days=1)
        competition = await get_competition_info(date, "day", results_per_page=1)
        start_time = utils.floor_day(date).timestamp()
        end_time = start_time + 86400
        title = f"Daily Stats - {utils.get_display_date(date)}"

    columns = ["text_id", "number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
    race_list = await races.get_races(username, columns, start_time, end_time)
    race_list.sort(key=lambda x: x[7])

    embed = Embed(title=title, color=user["colors"]["embed"])
    utils.add_profile(embed, api_stats)

    if not race_list:
        embed.description = "No races completed"
        return await ctx.send(embed=embed)

    if competition and competition["competitors"][0]["username"] == username:
        if competition["end_timestamp"] > datetime.now(timezone.utc).timestamp():
            embed.description = f":crown: **Competition Leader** :crown:"
        else:
            embed.description = f":first_place: **Competition Winner** :first_place:"

    mini_commands = ["miniday", "miniyesterday", "miniweek", "minimonth", "miniyear", "md", "myd", "mw", "mm", "my"]
    add_stats(embed, username, race_list, start_time, end_time, mini=ctx.invoked_with in mini_commands)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Day(bot))
