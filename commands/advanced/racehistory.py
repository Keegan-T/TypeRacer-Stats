import math
from datetime import datetime

from dateutil.relativedelta import relativedelta
from discord import Embed
from discord.ext import commands
import utils
import errors
import urls
import database.users as users
import database.races as races
import database.texts as texts
from database.bot_users import get_user
from api.users import get_stats
from commands.basic.download import download, update_text_stats

categories = ["races", "day", "week", "month", "year"]
sorts = ["points", "races", "time", "wpm", "date"]
info = {
    "name": "racehistory",
    "aliases": ["rh"],
    "description": "Displays race history for a time period and sort",
    "parameters": "[username] <time_period> <sort>",
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
    "import": True,
}


class RaceHistory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def racehistory(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, category, sort = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, category, sort)


async def get_params(ctx, user, params):
    username = user["username"]
    category = "races"
    sort = "date"

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        category = utils.get_category(categories, params[1])
        if not category:
            await ctx.send(embed=errors.invalid_option("category", categories))
            raise ValueError

    if len(params) > 2:
        sort = utils.get_category(sorts, params[2])
        if not sort:
            await ctx.send(embed=errors.invalid_option("sort", sorts))
            raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), category, sort


async def run(ctx, user, username, category, sort):
    db_stats = users.get_user(username)
    if not db_stats:
        return await ctx.send(embed=errors.import_required(username))

    api_stats = get_stats(username)
    new_races = await download(stats=api_stats)

    if category == "races":
        columns = ["number", "wpm", "accuracy", "points", "rank", "racers", "timestamp"]
        race_list = await races.get_races(username, columns=columns, order_by="timestamp", limit=20, reverse=True)

        title = "Race History"
        description = ""
        for race in race_list:
            description += (
                f"[#{race['number']:,}]({urls.replay(username, race['number'])}) - "
                f"{race['wpm']:,.2f} WPM - {math.floor(race['accuracy'] * 100):,.0f}% - {race['points']:,.0f} pts - "
                f"{race['rank']}/{race['racers']} - <t:{int(race['timestamp'])}:R>\n"
            )

    else:
        title = f"Race History - {category.title()}s (By {utils.get_sort_title(sort)})"
        description = ""
        history = await get_history(username, category, sort)
        for period in history[:10]:
            description += (
                f"**{period[1]}**\n{period[3]:,.0f} pts / {period[2]:,} races - "
                f"{period[4]:,.2f} WPM - {utils.format_duration_short(period[5])}\n\n"
            )

    embed = Embed(
        title=title,
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, api_stats)

    await ctx.send(embed=embed)

    if new_races:
        update_text_stats(username)

async def get_history(username, category, sort):
    sort_key = {"points": 3, "races": 2, "time": 5, "wpm": 4}.get(sort, 0)
    columns = ["text_id", "wpm", "points", "timestamp"]
    race_list = sorted(await races.get_races(username, columns=columns), key=lambda x: x[3])
    text_list = texts.get_texts(as_dictionary=True, include_disabled=True)

    history = []

    for race in race_list:
        text_id, wpm, points, timestamp = race
        seconds = utils.calculate_seconds(text_list[text_id]["quote"], wpm)

        if len(history) == 0 or timestamp > history[-1][1]:
            if category == "day":
                start = utils.floor_day(datetime.utcfromtimestamp(timestamp))
                end = start.timestamp() + 86400
            elif category == "week":
                start = utils.floor_week(datetime.utcfromtimestamp(timestamp))
                end = start.timestamp() + 86400 * 7
            elif category == "month":
                start = utils.floor_month(datetime.utcfromtimestamp(timestamp))
                end = (start + relativedelta(months=1)).timestamp()
            else:
                start = utils.floor_year(datetime.utcfromtimestamp(timestamp))
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
        start = datetime.utcfromtimestamp(stats[0])
        end = datetime.utcfromtimestamp(stats[1])
        if category == "day":
            stats[1] = start.strftime("%#m/%#d/%Y")
        elif category == "week":
            stats[1] = utils.get_display_date_range(start, end - relativedelta(days=1))
        elif category == "month":
            stats[1] = start.strftime("%B %Y")
        else:
            stats[1] = start.strftime("%Y")
        stats[4] = stats[4] / stats[2]

    history = sorted(history, key=lambda x: x[sort_key], reverse=True)

    return history


async def setup(bot):
    await bot.add_cog(RaceHistory(bot))
