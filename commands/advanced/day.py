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

info = {
    "name": "day",
    "aliases": ["d", "yesterday", "yd"],
    "description": "Displays a user's stats for a given day\n"
                   f"`{prefix}yesterday [username]` shows stats for the previous day",
    "parameters": "[username] <date>",
    "defaults": {
        "date": "today"
    },
    "usages": ["day keegant 2021-01-01"],
    "import": True,
}


class Day(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def day(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, date = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, date)


async def get_params(ctx, user, params, command=info):
    username = user["username"]
    date = datetime.now(timezone.utc)

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) == 1:
        date_string = " ".join(params)
        if "/" in date_string or "-" in date_string:
            try:
                date = parser.parse(date_string)
                username = user["username"]
            except ValueError:
                pass

    if len(params) > 1:
        try:
            date = parser.parse(" ".join(params[1:]))
        except ValueError:
            await ctx.send(embed=errors.invalid_date())
            raise

    if not username:
        await ctx.send(embed=errors.missing_param(command))
        raise ValueError

    return username.lower(), date


async def run(ctx, user, username, date):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    api_stats = get_stats(username)
    await download(stats=api_stats)

    week_commands = ["week", "w", "lastweek", "yesterweek", "lw", "yw"]
    month_commands = ["month", "m", "lastmonth", "yestermonth", "lm", "ym"]
    year_commands = ["year", "y", "lastyear", "yesteryear", "ly", "yy"]
    command = ctx.invoked_with

    if command in week_commands:
        if command in week_commands[2:]:
            date -= relativedelta(days=7)
        competition = get_competition_info(date, "week", results_per_page=1)
        start_date = utils.floor_week(date)
        end_date = start_date + relativedelta(days=7)
        start_time = start_date.timestamp()
        end_time = end_date.timestamp()
        date_string = utils.get_display_date_range(start_date, (end_date - relativedelta(days=1)))
        title = f"Weekly Stats - {date_string}"

    elif command in month_commands:
        if command in month_commands[2:]:
            date -= relativedelta(months=1)
        competition = get_competition_info(date, "month", results_per_page=1)
        start_date = utils.floor_month(date)
        end_date = start_date + relativedelta(months=1)
        start_time = start_date.timestamp()
        end_time = end_date.timestamp()
        date_string = date.strftime("%B %Y")
        title = f"Monthly Stats - {date_string}"

    elif command in year_commands:
        if command in year_commands[2:]:
            date -= relativedelta(years=1)
        competition = get_competition_info(date, "year", results_per_page=1)
        start_date = utils.floor_year(date)
        end_date = start_date + relativedelta(years=1)
        start_time = start_date.timestamp()
        end_time = end_date.timestamp()
        date_string = date.year
        title = f"Yearly Stats - {date_string}"

    else:
        if command in info["aliases"][1:]:
            date -= timedelta(days=1)
        competition = get_competition_info(date, "day", results_per_page=1)
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

    add_stats(embed, username, race_list, start_time, end_time)

    await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Day(bot))
