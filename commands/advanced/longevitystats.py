from discord import Embed
from discord.ext import commands
import utils
import errors
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database.bot_users import get_user
import database.races as races
import database.users as users

types = ["day", "week", "month", "year"]
info = {
    "name": "longevitystats",
    "aliases": ["ginoo75", "ginoo", "wellknown", "ls"],
    "description": "Displays the number of times a user has completed n races in a time period",
    "parameters": "[username] <n> <type>",
    "defaults": {
        "n": 1000,
        "type": "month",
    },
    "usages": [
        "longevitystats ginoo75",
        "longevitystats mark40511 1",
        "longevitystats keegant 1k day"
    ],
    "import": True,
}

class LongevityStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=info["aliases"])
    async def longevitystats(self, ctx, *params):
        user = get_user(ctx)

        try:
            username, kind, n = await get_params(ctx, user, params)
        except ValueError:
            return

        await run(ctx, user, username, kind, n)

async def get_params(ctx, user, params):
    username = user["username"]
    n = 1000
    kind = "month"

    if params and params[0].lower() != "me":
        username = params[0]

    if len(params) > 1:
        try:
            n = utils.parse_value_string(params[1])
        except ValueError:
            await ctx.send(embed=errors.invalid_number_format())
            raise

    if len(params) > 2:
        kind = utils.get_category(types, params[2])
        if not kind:
            await ctx.send(embed=errors.invalid_option("type", types))
            raise ValueError

    if n < 1:
        await ctx.send(embed=errors.greater_than(0))
        raise ValueError

    if not username:
        await ctx.send(embed=errors.missing_param(info))
        raise ValueError

    return username.lower(), kind, n

async def run(ctx, user, username, kind, n):
    stats = users.get_user(username)
    if not stats:
        return await ctx.send(embed=errors.import_required(username))

    all_history = await get_history(username, kind)
    history = [period for period in all_history if period[2] >= n]
    over = len(history)

    # streak, start date, end date
    current_streak = [0, 0, 0]
    best_streak = [0, 0, 0]

    for i in range(len(history)):
        period = history[i]
        prev_period = history[i - 1]

        if period[0] == prev_period[1]:
            current_streak = [current_streak[0] + 1, current_streak[1], period[0]]

        else:
            current_streak = [1, period[0], period[0]]

        if current_streak[0] > best_streak[0]:
            best_streak = current_streak

    if best_streak[0] == 0:
        description = f"User has not achieved this many races in a {kind}"

    else:
        best_streak_range = get_streak_string(best_streak[1], best_streak[2], kind)

        description = f"**Best Streak:** {best_streak[0]:,} ({best_streak_range})\n"

        streak_end = current_streak[2]
        if kind == "day":
            now = utils.floor_day(utils.now())
            previous = now - relativedelta(days=1)
        elif kind == "week":
            now = utils.floor_week(utils.now())
            previous = now - relativedelta(days=7)
        elif kind == "month":
            now = utils.floor_month(utils.now())
            previous = now - relativedelta(months=1)
        else:
            now = utils.floor_year(utils.now())
            previous = now - relativedelta(years=1)

        if streak_end == now.timestamp() or streak_end == previous.timestamp():
            current_streak_range = get_streak_string(current_streak[1], current_streak[2], kind)
            description += f"**Current Streak:** {current_streak[0]:,} ({current_streak_range})\n"
        else:
            description += f"**Current Streak:** 0\n"

        description += f"**Total {kind.title()}s:** {over:,}"

    embed = Embed(
        title=f"Longevity Stats - {kind.title()}s ({n:,} Races)",
        description=description,
        color=user["colors"]["embed"],
    )
    utils.add_profile(embed, stats)

    await ctx.send(embed=embed)

async def get_history(username, kind):
    race_list = await races.get_races(username, columns=["timestamp"])
    race_list.sort(key=lambda x: x[0])

    history = []
    for race in race_list:
        timestamp = race[0]

        if len(history) == 0 or timestamp > history[-1][1]:
            if kind == "day":
                start = utils.floor_day(datetime.utcfromtimestamp(timestamp))
                end = start.timestamp() + 86400
            elif kind == "week":
                start = utils.floor_week(datetime.utcfromtimestamp(timestamp))
                end = start.timestamp() + 86400 * 7
            elif kind == "month":
                start = utils.floor_month(datetime.utcfromtimestamp(timestamp))
                end = (start + relativedelta(months=1)).timestamp()
            else:
                start = utils.floor_year(datetime.utcfromtimestamp(timestamp))
                end = (start + relativedelta(years=1)).timestamp()

            history.append([start.timestamp(), end, 1])

        else:
            history[-1][2] += 1

    return history

def get_streak_string(start, end, kind):
    streak_start = datetime.utcfromtimestamp(start)
    streak_end = datetime.utcfromtimestamp(end)
    streak_1 = streak_start == streak_end

    if kind == "day":
        streak_range = utils.get_display_date_range(streak_start, streak_end)

    elif kind == "week":
        streak_range = f"Week of {streak_start.strftime('%#m/%#d/%Y')}"
        if not streak_1:
            streak_range += f" - Week of {streak_end.strftime('%#m/%#d/%Y')}"

    elif kind == "month":
        streak_range = f"{streak_start.strftime('%B %Y')}"
        if not streak_1:
            streak_range += f" - {streak_end.strftime('%B %Y')}"

    else:
        streak_range = f"{streak_start.strftime('%Y')}"
        if not streak_1:
            streak_range += f" - {streak_end.strftime('%Y')}"

    return streak_range


async def setup(bot):
    await bot.add_cog(LongevityStats(bot))